import pygame
import sys
import traceback
import random
from datetime import datetime
import os
from collections import deque

from database.user_db import init_db, register_user, check_user
from ui.input_box import InputBox
from ui.button import Button
from screens.menu_page import MenuPage
from screens.settings_page import SettingsPage
from screens.maps import Map, MAPS, ROOMS, ROOM_SLOTS
from screens.room_page import RoomPage
from ui.item_bar import ItemBar
from database.items_db import init_items_db, add_item_type_if_not_exists, get_items_by_category
# Embedded small utilities (bubble sort, binary search, and simple sequential text table)

def bubble_sort(arr):
    """Return a new list that is a bubble-sorted copy of `arr` (stable, O(n^2))."""
    a = list(arr)
    n = len(a)
    if n <= 1:
        return a
    for i in range(n):
        swapped = False
        for j in range(0, n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


def binary_search(sorted_list, target):
    """Classic binary search on a sorted list. Returns index of `target` or -1."""
    lo = 0
    hi = len(sorted_list) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        v = sorted_list[mid]
        if v == target:
            return mid
        elif v < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


class TextTable:
    """Minimal sequential text-table stored as CSV-like file.

    - append_row(dict) writes rows sequentially
    - iter_rows() yields rows (dict)
    - find_first(key, value) does linear scan
    """
    def __init__(self, path, fieldnames):
        self.path = path
        self.fieldnames = list(fieldnames)
        if not os.path.exists(self.path):
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(','.join(self.fieldnames) + '\n')

    def append_row(self, row):
        values = [str(row.get(fn, '')) for fn in self.fieldnames]
        line = ','.join(v.replace('\n', ' ') for v in values) + '\n'
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(line)

    def iter_rows(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            header = f.readline()
            for line in f:
                parts = line.rstrip('\n').split(',')
                row = {self.fieldnames[i]: (parts[i] if i < len(parts) else '') for i in range(len(self.fieldnames))}
                yield row

    def find_first(self, key, value):
        for row in self.iter_rows():
            if row.get(key) == value:
                return row
        return None

pygame.init()
# Defensive: some SDL/pygame builds raise a KeyError during first event.poll/get
# when joystick or other input subsystems are initialized. Quit joystick subsystem
# early to avoid that C-level issue (harmless if no joysticks are present).
try:
    pygame.joystick.quit()
except Exception:
    pass


def safe_get_events():
    """Return a list of events in a way that avoids pygame.event.get() crashes.

    Strategy:
    - Prefer `pygame.event.get()` (fast).
    - If it raises, call `pygame.event.pump()` then gather events via `poll()`
      until a NOEVENT (type==0) is returned. This avoids the C-level conversion
      path that appears to raise KeyError on some Windows/SDL combos.
    """
    try:
        return pygame.event.get()
    except Exception:
        try:
            pygame.event.pump()
        except Exception:
            pass
        out = []
        try:
            while True:
                ev = pygame.event.poll()
                # NOEVENT has numeric type 0; stop when no events available
                if getattr(ev, 'type', 0) == 0:
                    break
                out.append(ev)
        except Exception:
            # worst-case: give up and return empty list
            return []
        return out
# Developer helpers (non-intrusive). Set to True to run simple demos.
DEBUG_DEV = False

def _dev_demo_write_table():
    """Example demo that writes a small sequential text table and runs algorithms.
    Not executed unless `DEBUG_DEV` is True.
    """
    table = TextTable('dev_daily_summary.txt', ['day', 'item', 'energy_kwh', 'cost'])
    # append a sample row for demonstration (no effect on simulation state)
    table.append_row({'day': '0', 'item': 'LED bulbs', 'energy_kwh': '0.123', 'cost': '0.02'})
    # read rows sequentially
    rows = list(table.iter_rows())
    # show bubble-sort and binary-search usage on numeric energy values
    energies = [float(r['energy_kwh'] or 0.0) for r in rows if r.get('energy_kwh')]
    sorted_energies = bubble_sort(energies)
    # binary search for zero (example)
    idx = binary_search(sorted_energies, 0.0)
    print('[DEV] wrote dev_daily_summary.txt; rows:', len(rows), 'sorted_energies:', sorted_energies, 'zero_idx:', idx)


# --- Additional small data-structure demos ---
class Stack:
    """Simple LIFO stack (list-backed)."""
    def __init__(self):
        self._data = []
    def push(self, v):
        self._data.append(v)
    def pop(self):
        return self._data.pop() if self._data else None
    def peek(self):
        return self._data[-1] if self._data else None
    def is_empty(self):
        return len(self._data) == 0


class Queue:
    """Simple FIFO queue using collections.deque."""
    def __init__(self):
        self._dq = deque()
    def enqueue(self, v):
        self._dq.append(v)
    def dequeue(self):
        return self._dq.popleft() if self._dq else None
    def is_empty(self):
        return len(self._dq) == 0


class Graph:
    """Adjacency-list graph with simple BFS/DFS helpers."""
    def __init__(self):
        self.adj = {}  # dict: node -> list[node]
    def add_edge(self, a, b, bidir=True):
        self.adj.setdefault(a, []).append(b)
        if bidir:
            self.adj.setdefault(b, []).append(a)
    def bfs(self, start):
        visited = set()
        order = []
        q = deque([start])
        visited.add(start)
        while q:
            v = q.popleft()
            order.append(v)
            for nb in self.adj.get(v, []):
                if nb not in visited:
                    visited.add(nb)
                    q.append(nb)
        return order
    def dfs(self, start):
        visited = set()
        order = []
        def _dfs(v):
            visited.add(v)
            order.append(v)
            for nb in self.adj.get(v, []):
                if nb not in visited:
                    _dfs(nb)
        _dfs(start)
        return order


class TreeNode:
    """Simple binary-search-tree node for demonstration (no balancing)."""
    def __init__(self, key, left=None, right=None):
        self.key = key
        self.left = left
        self.right = right
    def insert(self, key):
        if key <= self.key:
            if self.left:
                self.left.insert(key)
            else:
                self.left = TreeNode(key)
        else:
            if self.right:
                self.right.insert(key)
            else:
                self.right = TreeNode(key)
    def inorder(self):
        if self.left:
            for k in self.left.inorder():
                yield k
        yield self.key
        if self.right:
            for k in self.right.inorder():
                yield k


def _dev_demo_data_structures():
    # Stack/Queue
    s = Stack(); s.push(1); s.push(2); s.push(3)
    print('[DEV][Stack] pop sequence:', [s.pop(), s.pop(), s.pop()])
    q = Queue(); q.enqueue('a'); q.enqueue('b'); q.enqueue('c')
    print('[DEV][Queue] dequeue sequence:', [q.dequeue(), q.dequeue(), q.dequeue()])

    # Graph
    g = Graph()
    g.add_edge('A','B'); g.add_edge('A','C'); g.add_edge('B','D'); g.add_edge('C','E')
    print('[DEV][Graph] BFS from A:', g.bfs('A'))
    print('[DEV][Graph] DFS from A:', g.dfs('A'))

    # Tree (BST)
    root = TreeNode(5)
    for v in [3,7,2,4,6,8]:
        root.insert(v)
    print('[DEV][Tree] inorder traversal:', list(root.inorder()))


# --- Advanced / additional algorithms ---
def merge_sort(arr):
    """Efficient O(n log n) merge sort returning a new sorted list."""
    a = list(arr)
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])
    right = merge_sort(a[mid:])
    res = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            res.append(left[i]); i += 1
        else:
            res.append(right[j]); j += 1
    if i < len(left):
        res.extend(left[i:])
    if j < len(right):
        res.extend(right[j:])
    return res


class Matrix:
    """Minimal matrix operations (no numpy): supports add, mul, transpose.
    Represented as list-of-lists (rows).
    """
    def __init__(self, rows):
        self.rows = [list(r) for r in rows]
        self.h = len(self.rows)
        self.w = len(self.rows[0]) if self.h else 0
    def transpose(self):
        return Matrix([[self.rows[r][c] for r in range(self.h)] for c in range(self.w)])
    def __mul__(self, other):
        # matrix multiply (self * other)
        if self.w != other.h:
            raise ValueError('Incompatible shapes for multiplication')
        out = [[0] * other.w for _ in range(self.h)]
        for i in range(self.h):
            for k in range(self.w):
                aik = self.rows[i][k]
                for j in range(other.w):
                    out[i][j] += aik * other.rows[k][j]
        return Matrix(out)
    def __add__(self, other):
        if self.h != other.h or self.w != other.w:
            raise ValueError('Shapes must match for addition')
        return Matrix([[self.rows[i][j] + other.rows[i][j] for j in range(self.w)] for i in range(self.h)])
    def __repr__(self):
        return f"Matrix({self.rows})"


def schedule_minimize_lateness(tasks):
    """Simple scheduling: tasks is list of dicts {'name', 'duration', 'due'}.
    Uses Earliest Due Date (EDD) ordering to minimize maximum lateness.
    Returns (schedule_order, max_lateness, details_list)
    """
    # sort by due date
    ordered = sorted(tasks, key=lambda t: t.get('due', 0))
    time = 0
    details = []
    max_lat = 0
    for t in ordered:
        start = time
        finish = start + float(t.get('duration', 0))
        lateness = max(0.0, finish - float(t.get('due', 0)))
        details.append({'name': t.get('name'), 'start': start, 'finish': finish, 'due': t.get('due', 0), 'lateness': lateness})
        if lateness > max_lat:
            max_lat = lateness
        time = finish
    return [t['name'] for t in ordered], max_lat, details


def _dev_demo_algorithms():
    # merge sort demo
    arr = [5,3,8,1,2,9,4]
    print('[DEV][MergeSort] input:', arr, 'sorted:', merge_sort(arr))

    # small matrix demo
    A = Matrix([[1,2],[3,4]])
    B = Matrix([[2,0],[1,2]])
    C = A * B
    print('[DEV][Matrix] A*B =', C)

    # scheduling demo (minimize max lateness)
    tasks = [
        {'name':'T1','duration':3,'due':4},
        {'name':'T2','duration':2,'due':3},
        {'name':'T3','duration':1,'due':6},
    ]
    order, max_lat, details = schedule_minimize_lateness(tasks)
    print('[DEV][Schedule] order:', order, 'max_lateness:', max_lat)


init_db()
init_items_db()
if DEBUG_DEV:
    try:
        _dev_demo_write_table()
        _dev_demo_data_structures()
        _dev_demo_algorithms()
    except Exception:
        print('[DEV] dev demo raised:')
        traceback.print_exc()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Home Automation Simulation')
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 36)
# smaller font for item bar categories / items
ITEM_SMALL_FONT = pygame.font.SysFont(None, 20)
SMALL_FONT = pygame.font.SysFont(None, 28)

show_fps = False
fullscreen = False
current_map = None
selected_item_category = None
selected_item = None

# Drag-and-drop state (initialize so module-level code can reference them)
dragging_item = None
dragging_surf = None
dragging_offset = (0, 0)

# current room page and name
current_room_page = None
current_room_name = None

# placements: placements[map_name][room_name] = [ item_dict_or_None, ... ] (slot-aligned)
placements = {}
# per-slot on/off state mirror: placements_on[map][room] = [ bool_or_False, ... ]
placements_on = {}

# ensure map drawn below the item bar
MAP_Y_OFFSET = 120  # moved lower so item bar/categories don't overlap map

# Add day_started flag so day only begins when user presses Start
day_started = False

# Smart items that support remote toggle from the map
SMART_REMOTE = {
    "LED bulbs",
    "Smart Thermostat",
    "Smart plug",
    "Smart Washing-Machine",
    "Smart oven",
    "Smart Air-Purifier",
    "Smart Blinds",
}

# current room page and name
current_room_page = None
current_room_name = None

# placements: placements[map_name][room_name] = [ item_dict_or_None, ... ] (slot-aligned)
placements = {}
# per-slot on/off state mirror: placements_on[map][room] = [ bool_or_False, ... ]
placements_on = {}

# ensure map drawn below the item bar
MAP_Y_OFFSET = 120  # moved lower so item bar/categories don't overlap map

# add new state for room view and day summary
LOGIN, REGISTER, MENU, SETTINGS, SIMULATION, MAP_SELECT, ROOM_VIEW, DAY_SUMMARY = (
    'login', 'register', 'menu', 'settings', 'simulation', 'map_select', 'room_view', 'day_summary'
)
screen_state = LOGIN
selected_map_name = None

# Data-structure instances used at runtime
undo_stack = Stack()
event_queue = Queue()
map_graphs = {}  # map_name -> Graph
map_matrices = {}  # map_name -> adjacency Matrix

# Add day_started flag so day only begins when user presses Start
day_started = False

# Smart items that support remote toggle from the map
SMART_REMOTE = {
    "LED bulbs",
    "Smart Thermostat",
    "Smart plug",
    "Smart Washing-Machine",
    "Smart oven",
    "Smart Air-Purifier",
    "Smart Blinds",
}

# Time / energy system
# current day runs for 30 seconds
day_duration_seconds = 30
day_elapsed_seconds = 0.0
minutes_per_second = 1440.0 / float(day_duration_seconds)  # computed as 1440 / day_duration_seconds

simulation_running = False  # simulation runs only after user presses Start Day
# meter per-day is represented by daily_energy_kwh (reset each day)
daily_energy_kwh = 0.0
daily_cost = 0.0

# per-item usage collected during the current simulated day
daily_item_usage = {}   # { item_name: {"energy": kWh, "cost": £, "category": "..."} }

daily_history = []  # list of {"energy":..., "cost":..., "date":...}
day_number = 0  # number of completed days

# UI Continue button on day summary (created later)
continue_button = None

# internal timing for main loop
last_time = pygame.time.get_ticks() / 1000.0

def start_new_day():
    global day_duration_seconds, day_elapsed_seconds, minutes_per_second, simulation_running
    global daily_item_usage, daily_energy_kwh, daily_cost
    # fixed duration: 30 seconds per simulated day
    day_duration_seconds = 30
    day_elapsed_seconds = 0.0
    minutes_per_second = 1440.0 / float(day_duration_seconds)  # full day = 1440 minutes
    simulation_running = True
    # reset per-day accumulators and per-item breakdown
    daily_item_usage = {}
    daily_energy_kwh = 0.0
    daily_cost = 0.0
    print(f"[TIME] Starting new simulated day ({day_duration_seconds}s → {minutes_per_second:.2f} min/sec)")

def end_current_day():
    global simulation_running, continue_button, screen_state
    simulation_running = False
    # place Continue button at bottom-right to avoid overlapping summary content
    btn_w, btn_h = 220, 48
    btn_x = WIDTH - btn_w - 24
    btn_y = HEIGHT - btn_h - 24
    continue_button = Button(btn_x, btn_y, btn_w, btn_h, "Continue", on_continue, font=FONT)
    screen_state = DAY_SUMMARY

    # Build a small BST of per-item energies for this day and print sorted results
    try:
        if daily_item_usage:
            items = [(info.get('energy', 0.0), name) for name, info in daily_item_usage.items()]
            it = iter(items)
            first = next(it, None)
            if first is not None:
                root = TreeNode(first)
                for e, n in it:
                    root.insert((e, n))
                sorted_items = list(root.inorder())  # ascending by energy
                sorted_items_desc = list(reversed(sorted_items))
                print('[TIME][DaySummary] top per-item energy (kWh, name):', sorted_items_desc[:8])
            # Suggest appliance scheduling to reduce peak (simple EDD demo)
            try:
                appliance_tasks = []
                for name, info in daily_item_usage.items():
                    if info.get('category') == 'Appliances' and info.get('energy', 0.0) > 0.0:
                        # duration in arbitrary units proportional to energy (demo only)
                        dur = max(1.0, float(info.get('energy', 0.0)) * 100.0)
                        # due time: prefer earlier for high-energy devices (demo heuristic)
                        due = max(1.0, 100.0 - dur)
                        appliance_tasks.append({'name': name, 'duration': dur, 'due': due})
                if appliance_tasks:
                    order, max_lat, details = schedule_minimize_lateness(appliance_tasks)
                    print('[TIME][ScheduleSuggestion] appliance order:', order, 'max_lateness:', max_lat)
            except Exception:
                traceback.print_exc()
    except Exception:
        traceback.print_exc()

    print("[TIME] Day finished — showing day summary")

def on_continue():
    global day_number, daily_history, daily_energy_kwh, daily_cost, meter_energy_kwh, screen_state, day_started
    # save today's totals into history
    day_number += 1
    daily_history.append({
        "day_index": day_number,
        "energy": daily_energy_kwh,
        "cost": daily_cost,
        "date": datetime.utcnow().isoformat()
    })
    # reset daily counters and start next day
    daily_energy_kwh = 0.0
    daily_cost = 0.0
    start_new_day()
    # ensure the simulation actually runs
    day_started = True
    # return to simulation
    screen_state = SIMULATION
    print(f"[TIME] Continue pressed — starting day {day_number+1}")

# --- moved here so it's defined before the main loop ---
def suggest_improvements(item_name, category, energy_per_min):
    """Return a short suggestion string for the given item."""
    # basic heuristics:
    epm = 0.0
    try:
        epm = float(energy_per_min)
    except Exception:
        pass

    name = (item_name or "").lower()
    if "incandescent" in name:
        return "Consider switching to LED bulbs to save energy."
    if "oven" in name:
        return "Use efficient cooking modes or reduce oven time where possible."
    if "washing" in name:
        return "Run full loads and use eco cycle to reduce energy."
    if "air-purifier" in name or "air purifier" in name:
        return "Run intermittently or on lower speed when possible."
    if "smart" in name:
        return "Can be controlled remotely; consider scheduling/off when unused."
    if "manual" in name:
        return "Consider smart alternatives to enable remote control and scheduling."
    # high-power general suggestion
    if epm > (0.02):  # threshold kWh / min (approx 1.2 kW average)
        return "High consumption — reduce runtime or replace with an efficient model."
    # default
    return "Turn off when not in use and consider energy-efficient alternatives."

def add_default_items():
    # energy_per_min is kWh per minute = power_kW / 60
    # realistic example power values:
    # LED bulb ~10W (0.01 kW) -> per min = 0.01/60 = 0.000167 kWh/min
    # Incandescent ~60W -> 0.06/60 = 0.001 kWh/min
    # Halogen ~50W -> 0.05/60 = 0.000833 kWh/min
    # Thermostat / small sensors ~1W -> 0.001/60 ~ 0.000017 kWh/min (we keep small but nonzero)
    # Smart plug idle ~2W -> 0.002/60 = 0.000033 kWh/min (very small)
    # Washing machine (active) ~0.5 kW -> 0.5/60 = 0.00833 kWh/min
    # Oven ~2.5 kW -> 2.5/60 = 0.04167 kWh/min
    # Air purifier ~50W -> 0.05/60 = 0.000833 kWh/min
    lighting = [
        ("LED bulbs", "ElectricsAndThermo", 0.01/60),
        ("Incandescent bulbs", "ElectricsAndThermo", 0.06/60),
        ("Halogen", "ElectricsAndThermo", 0.05/60),
        ("Manual Thermostat", "ElectricsAndThermo", 0.001/60),
        ("Smart Thermostat", "ElectricsAndThermo", 0.002/60),
        ("Smart plug", "ElectricsAndThermo", 0.002/60),
        ("UK plug (Type G)", "ElectricsAndThermo", 0.0),
    ]
    appliances = [
        ("Manual Washing-Machine", "Appliances", 0.5/60),
        ("Smart Washing-Machine", "Appliances", 0.5/60),
        ("Conventional oven", "Appliances", 2.5/60),
        ("Smart oven", "Appliances", 2.0/60),
    ]
    misc = [
        ("Air purifier", "Miscellaneous", 0.05/60),
        ("Smart Air-Purifier", "Miscellaneous", 0.035/60),
        ("Blinds", "Miscellaneous", 0.0),
        ("Smart Blinds", "Miscellaneous", 0.001/60),
    ]

    for name, cat, epm in lighting + appliances + misc:
        add_item_type_if_not_exists(name, cat, energy_per_min=epm, cost_per_kwh=0.20, icon_path=None)

add_default_items()

def on_category_change(category):
    global selected_item_category
    selected_item_category = category
    items = get_items_by_category(category)
    print(f"[DEBUG] Category changed -> {category}, loaded {len(items)} items")
    item_bar.set_items(items)

def on_item_selected(item):
    global selected_item
    if item:
        selected_item = item
        print("Item selected:", item["name"])
        globals()["selected_item"] = item

def go_to_settings():
    global screen_state
    screen_state = SETTINGS

def go_to_menu():
    global screen_state
    screen_state = MENU

def back_to_menu():
    global screen_state
    screen_state = MENU

def set_show_fps(value):
    global show_fps
    show_fps = value

def set_fullscreen(value):
    global fullscreen, screen
    fullscreen = value
    if fullscreen:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

def logout():
    switch_to_login()

def quit_program():
    pygame.quit()
    sys.exit()

menu_page = MenuPage(
    screen, FONT, SMALL_FONT,
    on_start=lambda: go_to_map_select(),
    on_settings=go_to_settings,
    on_logout=logout,
    on_quit=quit_program,
)

settings_page = SettingsPage(
    screen, FONT, SMALL_FONT,
    show_fps, fullscreen,
    on_back=back_to_menu,
    on_toggle_fps=set_show_fps,
    on_toggle_fullscreen=set_fullscreen
)

item_bar = ItemBar(
    screen, FONT, ITEM_SMALL_FONT,
    categories=["ElectricsAndThermo", "Appliances", "Miscellaneous"],
    height=96,
    on_category_change=on_category_change,
    on_item_click=on_item_selected
)

# Populate initial category items immediately
try:
    on_category_change(item_bar.get_selected_category())
except Exception:
    print('[ERROR] Exception during initial category load:')
    traceback.print_exc()

print('[INFO] Initialization complete — entering main loop soon')

# continue_button created dynamically when a day ends (see end_current_day)

# Helper: ensure placements dict has structure for a map & room and return list of items (None for empty)
def ensure_room_placements(map_name, room_name, slots_cfg):
    """Ensure placements and placements_on exist for the room and match slots_cfg length."""
    if map_name not in placements:
        placements[map_name] = {}
    if room_name not in placements[map_name]:
        placements[map_name][room_name] = [None] * len(slots_cfg)
    if map_name not in placements_on:
        placements_on[map_name] = {}
    if room_name not in placements_on[map_name]:
        placements_on[map_name][room_name] = [False] * len(slots_cfg)
    # If slots_cfg length changed, resize lists (safe)
    cur = placements[map_name][room_name]
    if len(cur) != len(slots_cfg):
        placements[map_name][room_name] = (cur + [None] * len(slots_cfg))[:len(slots_cfg)]
    cur_on = placements_on[map_name][room_name]
    if len(cur_on) != len(slots_cfg):
        placements_on[map_name][room_name] = (cur_on + [False] * len(slots_cfg))[:len(slots_cfg)]
    return placements[map_name][room_name]

def compute_remote_buttons(map_obj, map_name):
    """Compute labeled toggle buttons for smart items placed in rooms.
       Returns list of dicts: {rect,label,map,room,slot,on}"""
    buttons = []
    if not map_obj or map_name not in placements:
        return buttons
    for room_name, room_rect in map_obj.rooms.items():
        room_list = placements.get(map_name, {}).get(room_name, [])
        room_on = placements_on.get(map_name, {}).get(room_name, [])
        # collect smart item slots (preserve order)
        smart_slots = [i for i, itm in enumerate(room_list) if itm and itm.get("name") in SMART_REMOTE]
        for idx_stack, slot_index in enumerate(smart_slots):
            itm = room_list[slot_index]
            label = itm.get("name", "")
            # render width using SMALL_FONT (approx)
            txt_surf = SMALL_FONT.render(label, True, (255,255,255))
            btn_w = min(240, max(60, txt_surf.get_width() + 16))
            btn_h = max(22, txt_surf.get_height() + 8)
            # position above room_rect, stacked upward so they do not overlap the room area
            x = room_rect.centerx - btn_w // 2
            y = room_rect.top - btn_h - 8 - idx_stack * (btn_h + 6)
            btn_rect = pygame.Rect(int(x), int(y), int(btn_w), int(btn_h))
            on_state = False
            if slot_index < len(room_on):
                on_state = bool(room_on[slot_index])
            buttons.append({
                "rect": btn_rect,
                "label": label,
                "map": map_name,
                "room": room_name,
                "slot": slot_index,
                "on": on_state
            })
    return buttons


def build_map_graph(map_obj, map_name, adjacency_margin=8):
    """Build a Graph for the given map using room rect adjacency.
    Two rooms are connected if their rects touch or are within `adjacency_margin` pixels.
    """
    g = Graph()
    names = list(map_obj.rooms.keys())
    rects = {n: map_obj.rooms[n] for n in names}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = rects[names[i]]
            b = rects[names[j]]
            # consider adjacent if rects touch or are within margin
            if a.colliderect(b) or a.inflate(adjacency_margin, adjacency_margin).colliderect(b):
                g.add_edge(names[i], names[j], bidir=True)
    map_graphs[map_name] = g
    # also build an adjacency matrix (Matrix) for numerical/algorithmic uses
    idx = {n: i for i, n in enumerate(names)}
    mat = [[0]*len(names) for _ in names]
    for u, nbrs in g.adj.items():
        for v in nbrs:
            mat[idx[u]][idx[v]] = 1
    try:
        map_matrices[map_name] = Matrix(mat)
    except Exception:
        map_matrices[map_name] = None
    return g

def iter_active_placed_items():
    """Yield placed items that are ON (considering placements_on)."""
    for map_name, rooms in placements.items():
        for room_name, items in rooms.items():
            ons = placements_on.get(map_name, {}).get(room_name, [False]*len(items))
            for idx, itm in enumerate(items):
                if itm and idx < len(ons) and ons[idx]:
                    yield itm

# Login / register UI (kept from previous)
username_box = InputBox(300, 200, 200, 40, font=FONT)
password_box = InputBox(300, 260, 200, 40, font=FONT)
input_boxes = [username_box, password_box]
login_error = ''

def switch_to_register():
    global screen_state, username_box, password_box, login_error
    screen_state = REGISTER
    username_box.text = ''
    password_box.text = ''
    username_box.txt_surface = FONT.render('', True, (255,255,255))
    password_box.txt_surface = FONT.render('', True, (255,255,255))
    login_error = ''

def switch_to_login():
    global screen_state, username_box, password_box, login_error
    screen_state = LOGIN
    username_box.text = ''
    password_box.text = ''
    username_box.txt_surface = FONT.render('', True, (255,255,255))
    password_box.txt_surface = FONT.render('', True, (255,255,255))
    login_error = ''

def go_to_map_select():
    global screen_state
    screen_state = MAP_SELECT

def select_map(map_name):
    global selected_map_name, screen_state, current_map, day_started
    selected_map_name = map_name
    current_map = Map(screen, MAPS[map_name], ROOMS[map_name], y_offset=MAP_Y_OFFSET)
    # build adjacency graph for quick room navigation/inspection
    try:
        build_map_graph(current_map, selected_map_name)
        print(f"[GRAPH] built adjacency graph for {selected_map_name}")
        # show reachable rooms via BFS from first room (useful insight)
        try:
            first_room = next(iter(current_map.rooms.keys()))
            bfs_order = map_graphs[selected_map_name].bfs(first_room)
            print(f"[GRAPH] BFS from {first_room}: {bfs_order}")
            # show adjacency matrix shape
            mm = map_matrices.get(selected_map_name)
            if mm:
                print(f"[GRAPH] adjacency matrix for {selected_map_name}: {mm.h}x{mm.w}")
        except Exception:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()
    screen_state = SIMULATION
    item_bar.resize(screen.get_width())
    # do not start the day automatically — let user place items first
    day_started = False
    # ensure placements exist for all rooms listed in ROOM_SLOTS for this map
    for rn, slots in ROOM_SLOTS.get(map_name, {}).items():
        ensure_room_placements(map_name, rn, slots)

def try_login():
    global screen_state, login_error
    if username_box.text and password_box.text:
        if check_user(username_box.text, password_box.text):
            go_to_menu()
        else:
            login_error = 'Incorrect username or password.'
    else:
        login_error = 'Please enter username and password.'

def try_register():
    global screen_state, login_error
    if username_box.text and password_box.text:
        success, msg = register_user(username_box.text, password_box.text)
        if success:
            go_to_menu()
        else:
            login_error = msg
    else:
        login_error = 'Please enter username and password.'

login_button = Button(300, 320, 90, 40, 'Login', try_login, font=FONT)
register_button = Button(410, 320, 90, 40, 'Register', switch_to_register, font=FONT)
register_submit_button = Button(300, 320, 90, 40, 'Register', try_register, font=FONT)
back_button = Button(410, 320, 90, 40, 'Back', switch_to_login, font=FONT)
map_select_buttons = []
def create_map_select_buttons():
    global map_select_buttons
    map_select_buttons = []
    y = 200
    for map_name in MAPS.keys():
        btn = Button(WIDTH//2 - 100, y, 200, 50, map_name, lambda n=map_name: select_map(n), font=FONT)
        map_select_buttons.append(btn)
        y += 70
create_map_select_buttons()

# add helper to go back from room view
def go_back_from_room():
    global screen_state, current_room_page, current_room_name
    current_room_page = None
    current_room_name = None
    screen_state = SIMULATION

# Start-Day button (shown in SIMULATION when day hasn't started)
start_day_button = None
menu_button = None

def make_start_day_button():
    global start_day_button, menu_button
    btn_w, btn_h = 200, 44
    btn_x = WIDTH - btn_w - 16
    btn_y = item_bar.rect.bottom + 12
    start_day_button = Button(btn_x, btn_y, btn_w, btn_h, "Start Day", on_start_day, font=FONT)
    # place Main Menu button to the left of Start Day
    mb_w, mb_h = 140, 36
    mb_x = btn_x - mb_w - 8
    mb_y = btn_y + (btn_h - mb_h)//2
    menu_button = Button(mb_x, mb_y, mb_w, mb_h, "Main Menu", lambda: return_to_menu(), font=SMALL_FONT)

def on_start_day():
    global day_started
    # start new day; this resets timers as usual
    start_new_day()
    day_started = True

def return_to_menu():
    global day_started, simulation_running, screen_state, current_map, current_room_page, current_room_name
    global daily_energy_kwh, daily_cost, day_elapsed_seconds, continue_button
    global placements, placements_on, selected_map_name
    # stop any running day and clear room view
    day_started = False
    simulation_running = False
    current_room_page = None
    current_room_name = None

    # reset today's accumulators so when user returns to simulation they start fresh
    daily_energy_kwh = 0.0
    daily_cost = 0.0
    day_elapsed_seconds = 0.0

    # clear any summary/continue button state
    continue_button = None

    # completely reset placement state so items from previous maps don't persist
    placements = {}
    placements_on = {}

    # clear selected map and map object so next simulation starts fresh
    selected_map_name = None
    current_map = None

    # go back to main menu
    go_to_menu()
# create initial start + menu button objects
make_start_day_button()

# day will start when user presses Start Day (on_start_day)
# (no automatic start here)

# main loop
running = True
while running:
    now = pygame.time.get_ticks() / 1000.0
    dt = now - last_time
    last_time = now

    events = safe_get_events()

    for event in events:
        try:
            # Global undo: Ctrl+Z -> pop last action from undo_stack
            if event.type == pygame.KEYDOWN:
                try:
                    mods = pygame.key.get_mods()
                except Exception:
                    mods = 0
                if event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                    act = undo_stack.pop()
                    if act:
                        try:
                            if act.get('type') == 'place':
                                m = act.get('map')
                                r = act.get('room')
                                i = act.get('idx')
                                prev = act.get('prev')
                                ensure_room_placements(m, r, ROOM_SLOTS.get(m, {}).get(r, []))
                                placements[m][r][i] = prev
                                # sync to current room page if visible
                                if current_room_page and current_room_name == r and selected_map_name == m:
                                    current_room_page.slots[i]['item'] = prev
                                print(f"[UNDO] reverted placement in {r} slot {i}")
                            elif act.get('type') == 'remove':
                                m = act.get('map')
                                r = act.get('room')
                                i = act.get('idx')
                                itm = act.get('item')
                                ensure_room_placements(m, r, ROOM_SLOTS.get(m, {}).get(r, []))
                                placements[m][r][i] = itm
                                placements_on[m][r][i] = bool(act.get('on', True))
                                if current_room_page and current_room_name == r and selected_map_name == m:
                                    current_room_page.slots[i]['item'] = itm
                                    current_room_page.slots[i]['on'] = bool(act.get('on', True))
                                print(f"[UNDO] restored removed item in {r} slot {i}")
                        except Exception:
                            traceback.print_exc()
                    # consumed undo — skip further per-screen handling
                    continue
            if event.type == pygame.QUIT:
                running = False

            if screen_state in [LOGIN, REGISTER]:
                for box in input_boxes:
                    box.handle_event(event)
                if screen_state == LOGIN:
                    login_button.handle_event(event)
                    register_button.handle_event(event)
                else:
                    register_submit_button.handle_event(event)
                    back_button.handle_event(event)

            elif screen_state == MENU:
                menu_page.handle_event(event)

            elif screen_state == SETTINGS:
                settings_page.handle_event(event)

            elif screen_state == MAP_SELECT:
                for btn in map_select_buttons:
                    btn.handle_event(event)

            elif screen_state == SIMULATION:
                # item bar should capture top clicks first
                item_bar.handle_event(event)
                # Start Day button active until day_started becomes True
                if start_day_button and not day_started:
                    start_day_button.handle_event(event)
                # Main Menu button always active in SIMULATION
                if menu_button:
                    menu_button.handle_event(event)

                # handle remote map toggles first (consume clicks so they don't select rooms)
                if current_map and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    remote_buttons = compute_remote_buttons(current_map, selected_map_name)
                    handled = False
                    for b in remote_buttons:
                        if b["rect"].collidepoint(event.pos):
                            # ensure structure exists
                            ensure_room_placements(b["map"], b["room"], ROOM_SLOTS.get(b["map"], {}).get(b["room"], []))
                            placements_on[b["map"]][b["room"]][b["slot"]] = not placements_on[b["map"]][b["room"]][b["slot"]]
                            # sync to RoomPage if currently viewing same room
                            if current_room_page and current_room_name == b["room"]:
                                if 0 <= b["slot"] < len(current_room_page.slots):
                                    current_room_page.slots[b["slot"]]["on"] = placements_on[b["map"]][b["room"]][b["slot"]]
                            print(f"[MAP] remote toggle {b['label']} in {b['room']} -> {placements_on[b['map']][b['room']][b['slot']]}")
                            handled = True
                            break
                    if handled:
                        # consumed the click — don't pass to map selection
                        continue

                if current_map:
                    current_map.handle_event(event)

                    # if the map registered a selected room (user clicked a room), open the room view
                    selected_room = current_map.get_selected_room()
                    if selected_room:
                        slots_cfg = ROOM_SLOTS.get(selected_map_name, {}).get(selected_room, [])
                        if not slots_cfg:
                            slots_cfg = [
                                {"name": "Slot 1", "category": "ElectricsAndThermo"},
                                {"name": "Slot 2", "category": "ElectricsAndThermo"},
                            ]
                        try:
                            # ensure placements exist for this room
                            room_place_list = ensure_room_placements(selected_map_name, selected_room, slots_cfg)

                            # create RoomPage and populate with existing placements
                            current_room_page = RoomPage(
                                screen, FONT, SMALL_FONT, selected_map_name, selected_room, slots_cfg,
                                on_back=go_back_from_room
                            )
                            current_room_name = selected_room
                            # populate RoomPage.slots with previously placed items (if any)
                            for i in range(min(len(room_place_list), len(current_room_page.slots))):
                                current_room_page.slots[i]["item"] = room_place_list[i]
                                # get on/off from placements_on if present
                                current_room_page.slots[i]["on"] = placements_on.get(selected_map_name, {}).get(selected_room, [False]*len(current_room_page.slots))[i]
                            screen_state = ROOM_VIEW
                            current_map.selected_room = None
                        except Exception:
                            print("[ERROR] creating RoomPage for", selected_room)
                            traceback.print_exc()
                            current_room_page = None
                            current_map.selected_room = None

            elif screen_state == ROOM_VIEW:
                # RoomPage handles clicks first
                if current_room_page:
                    current_room_page.handle_event(event)

                # Start drag: only allow starting a drag from the item bar while inside a room
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    itm, itm_rect = item_bar.get_item_at_pos(event.pos)
                    if itm:
                        dragging_item = itm
                        dragging_surf = item_bar.create_item_surface(itm, item_bar.placeholder_size)
                        dragging_offset = (event.pos[0] - itm_rect.x, event.pos[1] - itm_rect.y)
                        # don't let item_bar handle this particular mouse-down
                        continue

                # Drag motion (nothing to change here; drawn in render)
                if event.type == pygame.MOUSEMOTION and dragging_item:
                    pass

                # Drop / end drag
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragging_item:
                    if current_room_page:
                        idx, slot, slot_rect = current_room_page.get_slot_at_pos(event.pos)
                        if idx is not None:
                            # enforce category match
                            if dragging_item.get("category") == slot.get("category"):
                                current_room_page.place_item(idx, dragging_item)
                                # ensure structures exist
                                ensure_room_placements(selected_map_name, current_room_name, ROOM_SLOTS.get(selected_map_name, {}).get(current_room_name, []))
                                # save placed item and default to ON
                                prev_item = placements.get(selected_map_name, {}).get(current_room_name, [None] * (idx + 1))[idx] if selected_map_name in placements and current_room_name in placements.get(selected_map_name, {}) else None
                                placements[selected_map_name][current_room_name][idx] = dragging_item
                                placements_on[selected_map_name][current_room_name][idx] = True
                                # push undo action
                                try:
                                    undo_stack.push({
                                        'type': 'place',
                                        'map': selected_map_name,
                                        'room': current_room_name,
                                        'idx': idx,
                                        'prev': prev_item,
                                        'item': dragging_item,
                                    })
                                    # enqueue for dev logging
                                    event_queue.enqueue({
                                        'time': datetime.utcnow().isoformat(),
                                        'action': 'place',
                                        'map': selected_map_name,
                                        'room': current_room_name,
                                        'idx': idx,
                                        'item': dragging_item,
                                    })
                                except Exception:
                                    traceback.print_exc()
                                print(f"Placed '{dragging_item.get('name')}' into slot '{slot.get('name')}'")
                            else:
                                print(f"Cannot place '{dragging_item.get('name')}' into slot '{slot.get('name')}' (requires {slot.get('category')})")
                    dragging_item = None
                    dragging_surf = None
                    dragging_offset = (0, 0)

                # allow item bar interactions while in room
                item_bar.handle_event(event)

                # forward remove-button events then sync placements for current room
                if current_room_page:
                    # capture previous persistent state so we can detect removals
                    prev_list = None
                    if selected_map_name and current_room_name and selected_map_name in placements and current_room_name in placements[selected_map_name]:
                        prev_list = list(placements[selected_map_name][current_room_name])

                    current_room_page.handle_remove_event(event)

                    # sync persistent placements for this room after possible removal
                    if selected_map_name and current_room_name:
                        # ensure structure exists
                        slots_cfg = ROOM_SLOTS.get(selected_map_name, {}).get(current_room_name, [])
                        ensure_room_placements(selected_map_name, current_room_name, slots_cfg)
                        new_list = [s["item"] for s in current_room_page.slots]
                        # detect removals: prev had item and new is None
                        if prev_list is not None:
                            for i in range(max(len(prev_list), len(new_list))):
                                prev_it = prev_list[i] if i < len(prev_list) else None
                                new_it = new_list[i] if i < len(new_list) else None
                                if prev_it is not None and new_it is None:
                                    # record removal for undo & logging
                                    try:
                                        undo_stack.push({
                                            'type': 'remove',
                                            'map': selected_map_name,
                                            'room': current_room_name,
                                            'idx': i,
                                            'item': prev_it,
                                            'on': placements_on.get(selected_map_name, {}).get(current_room_name, [False]*len(prev_list))[i] if i < len(prev_list) else False,
                                        })
                                        event_queue.enqueue({
                                            'time': datetime.utcnow().isoformat(),
                                            'action': 'remove',
                                            'map': selected_map_name,
                                            'room': current_room_name,
                                            'idx': i,
                                            'item': prev_it,
                                        })
                                    except Exception:
                                        traceback.print_exc()

                        placements[selected_map_name][current_room_name] = new_list
                        placements_on[selected_map_name][current_room_name] = [bool(s.get("on", False)) for s in current_room_page.slots]
            elif screen_state == DAY_SUMMARY:
                # day summary UI: only continue button active
                if continue_button:
                    continue_button.handle_event(event)
        except Exception:
            print('[ERROR] Exception while handling event:')
            traceback.print_exc()

    # --- process queued dev events (lightweight) ---
    if DEBUG_DEV:
        try:
            log_table = TextTable('dev_event_log.txt', ['time', 'action', 'map', 'room', 'slot', 'item'])
            for _ in range(4):
                ev = event_queue.dequeue()
                if not ev:
                    break
                item_name = ''
                it = ev.get('item')
                if isinstance(it, dict):
                    item_name = it.get('name', '')
                else:
                    item_name = str(it)
                log_table.append_row({'time': ev.get('time', ''), 'action': ev.get('action', ''), 'map': ev.get('map', ''), 'room': ev.get('room', ''), 'slot': ev.get('idx', ''), 'item': item_name})
        except Exception:
            traceback.print_exc()

    # --- time / simulation updates ---
    # only advance simulated time after the user pressed Start Day
    if screen_state == SIMULATION and day_started and simulation_running:
        # accumulate simulated minutes for this frame
        if day_duration_seconds and minutes_per_second:
            delta_minutes = dt * minutes_per_second
            # sum energy for all ON placed items across all maps/rooms
            frame_energy = 0.0
            frame_cost = 0.0
            for itm in iter_active_placed_items():
                try:
                    epm = float(itm.get("energy_per_min", 0.0))
                    costk = float(itm.get("cost_per_kwh", 0.0))
                except Exception:
                    epm = 0.0
                    costk = 0.0
                e_kwh = epm * delta_minutes
                c = e_kwh * costk
                frame_energy += e_kwh
                frame_cost += c
                # record per-item usage for the day (keyed by item name)
                name = itm.get("name", "Unknown")
                entry = daily_item_usage.setdefault(name, {"energy": 0.0, "cost": 0.0, "category": itm.get("category", ""), "epm": epm})
                entry["energy"] += e_kwh
                entry["cost"] += c

            # accumulate per-day totals (meter shows per-day)
            daily_energy_kwh += frame_energy
            daily_cost += frame_cost

            day_elapsed_seconds += dt
            # if day finished, pause and show summary
            if day_elapsed_seconds >= day_duration_seconds:
                # prepare day summary values (we keep daily_energy_kwh/daily_cost)
                end_current_day()

    # draw
    screen.fill((30, 30, 30))

    if screen_state == LOGIN:
        title = FONT.render('Login', True, (255,255,255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))
        user_label = SMALL_FONT.render('Username:', True, (200,200,200))
        pass_label = SMALL_FONT.render('Password:', True, (200,200,200))
        screen.blit(user_label, (200, 210))
        screen.blit(pass_label, (200, 270))
        for box in input_boxes:
            box.draw(screen)
        login_button.draw(screen)
        register_button.draw(screen)
        if login_error:
            err = SMALL_FONT.render(login_error, True, (255, 80, 80))
            screen.blit(err, (300, 370))

    elif screen_state == REGISTER:
        title = FONT.render('Register', True, (255,255,255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))
        user_label = SMALL_FONT.render('Username:', True, (200,200,200))
        pass_label = SMALL_FONT.render('Password:', True, (200,200,200))
        screen.blit(user_label, (200, 210))
        screen.blit(pass_label, (200, 270))
        for box in input_boxes:
            box.draw(screen)
        register_submit_button.draw(screen)
        back_button.draw(screen)
        if login_error:
            err = SMALL_FONT.render(login_error, True, (255, 80, 80))
            screen.blit(err, (300, 370))

    elif screen_state == MENU:
        menu_page.draw()

    elif screen_state == SETTINGS:
        settings_page.draw()

    elif screen_state == MAP_SELECT:
        screen.fill((30, 30, 30))
        title = FONT.render("Select a Map", True, (255,255,255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        for btn in map_select_buttons:
            btn.draw(screen)

    elif screen_state == SIMULATION:
        if current_map:
            current_map.draw()
            # draw labeled remote toggles for smart items (above rooms)
            remote_buttons = compute_remote_buttons(current_map, selected_map_name)
            for b in remote_buttons:
                rect = b["rect"]
                color = (0,200,0) if b["on"] else (200,0,0)
                pygame.draw.rect(screen, color, rect, border_radius=6)
                pygame.draw.rect(screen, (30,30,30), rect, 2, border_radius=6)
                txt = SMALL_FONT.render(b["label"], True, (255,255,255))
                screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
        item_bar.draw()
        # draw Main Menu button and Start Day button when visible
        if menu_button:
            menu_button.draw(screen)
        if start_day_button and not day_started:
            start_day_button.draw(screen)
        # show small running timer and meter (meter now shows current day's total)
        timer_text = SMALL_FONT.render(f"Day time: {int(day_elapsed_seconds)}s / {int(day_duration_seconds) if day_duration_seconds else 0}s", True, (200,200,200))
        screen.blit(timer_text, (10, item_bar.rect.bottom + 32))
        meter_text = SMALL_FONT.render(f"Today's meter (kWh): {daily_energy_kwh:.4f}", True, (200,200,100))
        screen.blit(meter_text, (10, item_bar.rect.bottom + 60))

    elif screen_state == ROOM_VIEW:
        # Draw room (full-screen)
        if current_room_page:
            current_room_page.draw()
        # Draw the item bar on top
        item_bar.draw()
        # Draw remove button (if visible) on top of the item bar
        if current_room_page:
            current_room_page.draw_remove_button(screen)
        # Ensure Back button is visible above the item bar
        if current_room_page:
            current_room_page.back_button.draw(screen)
        # Draw dragging preview on top if any
        if dragging_item and dragging_surf:
            mx, my = pygame.mouse.get_pos()
            draw_x = mx - dragging_offset[0]
            draw_y = my - dragging_offset[1]
            screen.blit(dragging_surf, (draw_x, draw_y))

    elif screen_state == DAY_SUMMARY:
        # show day's totals and a Continue button
        title = FONT.render("Day Summary", True, (255,255,255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
        # today's totals
        energy_txt = SMALL_FONT.render(f"Today's energy: {daily_energy_kwh:.4f} kWh", True, (220,220,220))
        cost_txt = SMALL_FONT.render(f"Today's cost: £{daily_cost:.4f}", True, (220,220,220))
        screen.blit(energy_txt, (WIDTH//2 - energy_txt.get_width()//2, 160))
        screen.blit(cost_txt, (WIDTH//2 - cost_txt.get_width()//2, 200))

        # compute temporary history including today's values to check week totals
        temp_hist = daily_history + [{"energy": daily_energy_kwh, "cost": daily_cost}]
        if len(temp_hist) >= 7:
            # sum last 7 days (most recent)
            last7 = temp_hist[-7:]
            week_energy = sum(d["energy"] for d in last7)
            week_cost = sum(d["cost"] for d in last7)
            week_txt = SMALL_FONT.render(f"Last 7 days: {week_energy:.4f} kWh, £{week_cost:.4f}", True, (200,200,150))
            screen.blit(week_txt, (WIDTH//2 - week_txt.get_width()//2, 260))

        # per-item breakdown (sorted by energy desc using merge_sort)
        lines_x = 60
        lines_y = 300
        line_h = SMALL_FONT.get_height() + 6
        # prepare list of (energy, name) so merge_sort orders by energy
        energy_name_pairs = [(info.get('energy', 0.0), name) for name, info in daily_item_usage.items()]
        sorted_pairs = merge_sort(energy_name_pairs)
        # descending
        sorted_pairs_desc = list(reversed(sorted_pairs))
        if sorted_pairs_desc:
            header = ITEM_SMALL_FONT.render("Per-item usage (energy kWh, cost £) and suggestions:", True, (210,210,210))
            screen.blit(header, (lines_x, lines_y - line_h))
            # show up to N items (fit screen), with a short suggestion under each
            max_display = 8
            for i, (energy_val, iname) in enumerate(sorted_pairs_desc[:max_display]):
                y = lines_y + i * (line_h * 2)
                info = daily_item_usage.get(iname, {})
                txt = SMALL_FONT.render(f"{iname}: {info.get('energy',0.0):.4f} kWh, £{info.get('cost',0.0):.4f}", True, (230,230,230))
                screen.blit(txt, (lines_x, y))
                suggestion = suggest_improvements(iname, info.get("category", ""), info.get("epm", 0.0))
                sug_surf = ITEM_SMALL_FONT.render(f"Suggestion: {suggestion}", True, (180,180,180))
                screen.blit(sug_surf, (lines_x + 12, y + line_h))
        else:
            none_txt = ITEM_SMALL_FONT.render("No item consumption recorded this day.", True, (200,200,200))
            screen.blit(none_txt, (lines_x, lines_y))

        # draw Continue button if present
        if continue_button:
            continue_button.draw(screen)

    if show_fps:
        fps_text = SMALL_FONT.render(f"FPS: {int(clock.get_fps())}", True, (0,255,0))
        screen.blit(fps_text, (10, 10))
    # draw overlays last so they appear above all UI
    try:
        item_bar.draw_overlay(screen)
    except Exception:
        traceback.print_exc()
    # room overlay (slot stats) if in room view
    if current_room_page:
        try:
            rect, item = current_room_page.get_selected_slot_info()
            if rect and item:
                try:
                    epm = float(item.get('energy_per_min', 0.0))
                    costk = float(item.get('cost_per_kwh', 0.0))
                except Exception:
                    epm = 0.0; costk = 0.0
                SMART_REMOTE_LOCAL = {
                    "LED bulbs",
                    "Smart Thermostat",
                    "Smart plug",
                    "Smart Washing-Machine",
                    "Smart oven",
                    "Smart Air-Purifier",
                    "Smart Blinds",
                }
                remote = 'Yes' if (item.get('name') in SMART_REMOTE_LOCAL) else 'No'
                lines = [f"Energy/min: {epm:.6f} kWh", f"Cost/kWh: £{costk:.2f}", f"Remote: {remote}"]
                w = max(rect.w, 160)
                h = (SMALL_FONT.get_height() + 4) * len(lines) + 8
                px = rect.x
                py = rect.y + rect.h + 6
                if px + w > WIDTH - 8:
                    px = max(8, WIDTH - w - 8)
                panel = pygame.Rect(px, py, w, h)
                pygame.draw.rect(screen, (24,24,24), panel)
                pygame.draw.rect(screen, (100,100,100), panel, 1)
                ly = panel.y + 6
                for line in lines:
                    surf = SMALL_FONT.render(line, True, (230,230,230))
                    screen.blit(surf, (panel.x + 8, ly))
                    ly += SMALL_FONT.get_height() + 4
        except Exception:
            traceback.print_exc()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()