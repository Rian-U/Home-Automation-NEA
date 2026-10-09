from ui.button import Button
import pygame, os

class RoomPage:
    def __init__(self, screen, font, small_font, map_name, room_name, slots_config, on_back, room_image_path=None):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.map_name = map_name
        self.room_name = room_name
        self.on_back = on_back
        self.room_image_path = room_image_path

        self.slots = []
        for s in slots_config:
            # include per-slot on/off state
            self.slots.append({
                "name": s.get("name", ""),
                "category": s.get("category", ""),
                "item": None,
                "on": False
            })

        w, h = screen.get_size()
        self.title_y = 24
        self.top_padding = 12
        # increase slot size and move slots lower so categories / item bar don't overlap room content
        self.slot_size = 120
        self.slot_gap = 24
        self.slot_top = 200  

        # Back button placed below the item bar (moved lower to avoid overlap)
        self.back_button = Button(16, 140, 90, 36, "Back", self._on_back, font=self.font)

        # remove button (created when needed)
        self.remove_button = None
        self.remove_slot_idx = None
        self.selected_slot_idx = None

        if not self.room_image_path:
            candidate1 = os.path.join("assets", "rooms", f"{self.map_name}_{self.room_name}.png")
            candidate2 = os.path.join("assets", "rooms", f"{self.room_name}.png")
            if os.path.exists(candidate1):
                self.room_image_path = candidate1
            elif os.path.exists(candidate2):
                self.room_image_path = candidate2
            else:
                self.room_image_path = None
        self._load_background()

    def _load_background(self):
        self.bg_surf = None
        if self.room_image_path:
            try:
                surf = pygame.image.load(self.room_image_path).convert_alpha()
                self.bg_surf = pygame.transform.smoothscale(surf, self.screen.get_size())
            except Exception:
                self.bg_surf = None

    def _on_back(self):
        if callable(self.on_back):
            self.on_back()

    def get_slot_at_pos(self, pos):
        """Return (idx, slot_dict, rect) if pos is over a slot, else (None, None, None)."""
        for idx in range(len(self.slots)):
            rect = self._slot_rect(idx)
            if rect.collidepoint(pos):
                return idx, self.slots[idx], rect
        return None, None, None

    def place_item(self, slot_idx, item):
        """Place or replace item in slot_idx. Set default ON for newly placed items."""
        if 0 <= slot_idx < len(self.slots):
            self.slots[slot_idx]["item"] = item
            self.slots[slot_idx]["on"] = True
            # hide any remove UI for this slot after placement
            if self.remove_slot_idx == slot_idx:
                self.remove_button = None
                self.remove_slot_idx = None

    def remove_item(self, slot_idx):
        if 0 <= slot_idx < len(self.slots):
            self.slots[slot_idx]["item"] = None
            self.slots[slot_idx]["on"] = False
        self.remove_button = None
        self.remove_slot_idx = None

    def show_remove_for_slot(self, slot_idx):
        """Create a Remove Item button near the slot (drawn on top by main)."""
        rect = self._slot_rect(slot_idx)
        btn_w, btn_h = 120, 36
        # place remove button below the toggle (toggle occupies some vertical space)
        btn_x = rect.x + (rect.w - btn_w)//2
        btn_y = rect.y + rect.h + 8 + 28 + 6  # slot bottom + gap + toggle height + gap
        self.remove_button = Button(btn_x, btn_y, btn_w, btn_h, "Remove Item", lambda idx=slot_idx: self.remove_item(idx), font=self.small_font)
        self.remove_slot_idx = slot_idx

    def handle_event(self, event):
        # back button
        self.back_button.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # check toggles and slots
            for idx in range(len(self.slots)):
                rect = self._slot_rect(idx)
                # toggle rect (below slot, above remove)
                toggle_rect = pygame.Rect(rect.x + (rect.w - 68)//2, rect.y + rect.h + 8, 68, 28)
                if toggle_rect.collidepoint(event.pos):
                    # toggle on/off for this slot
                    self.slots[idx]["on"] = not self.slots[idx].get("on", False)
                    print(f"[ROOM] Toggled slot {idx} ('{self.slots[idx]['name']}') -> {self.slots[idx]['on']}")
                    # clear selection for other slots
                    self.selected_slot_idx = None
                    return

                if rect.collidepoint(event.pos):
                    slot = self.slots[idx]
                    # set selected slot for stats display
                    self.selected_slot_idx = idx
                    if slot["item"]:
                        # show remove button for this slot
                        self.show_remove_for_slot(idx)
                        print(f"[ROOM] slot '{slot['name']}' clicked (has item) - showing Remove button")
                    else:
                        # clicking empty slot does nothing here — drop handled in main
                        print(f"[ROOM] slot '{slot['name']}' clicked (empty) - ready for drop")
                    return
            # clicked in room but not on any slot -> clear selection
            self.selected_slot_idx = None

    def handle_remove_event(self, event):
        """Forward events to the remove button (if visible)."""
        if getattr(self, "remove_button", None):
            try:
                self.remove_button.handle_event(event)
            except Exception:
                # avoid crashing if the button implementation changes
                pass

    def draw(self):
        # full-screen room view
        if self.bg_surf:
            self.screen.blit(self.bg_surf, (0, 0))
        else:
            self.screen.fill((28, 28, 30))
            pygame.draw.rect(self.screen, (36, 36, 40), (0, 0, 84, self.screen.get_width()))

        title_surf = self.font.render(self.room_name, True, (245,245,245))
        self.screen.blit(title_surf, (self.screen.get_width()//2 - title_surf.get_width()//2, self.title_y))

        count = len(self.slots)
        total_width = count * self.slot_size + (count - 1) * self.slot_gap
        start_x = max(20, self.screen.get_width()//2 - total_width//2)
        for idx, slot in enumerate(self.slots):
            rect = pygame.Rect(start_x + idx * (self.slot_size + self.slot_gap), self.slot_top, self.slot_size, self.slot_size)
            pygame.draw.rect(self.screen, (70,70,70), rect)
            pygame.draw.rect(self.screen, (140,140,140), rect, 2)

            # render category and name with larger default sizes for readability
            cat_surf = self._render_text_fit(slot["category"], rect.w - 12, bold=True, start_sizes=(32,30,28))
            self.screen.blit(cat_surf, (rect.x + 6, rect.y + 6))
            name_surf = self._render_text_fit(slot["name"], rect.w - 12, start_sizes=(28,26,24))
            self.screen.blit(name_surf, (rect.x + 6, rect.y + 6 + cat_surf.get_height() + 4))

            # item placeholder area (empty until drop)
            ph_rect = pygame.Rect(rect.x + 8, rect.y + rect.h//2 - 12, rect.w - 16, 24)
            pygame.draw.rect(self.screen, (50,50,50), ph_rect)
            pygame.draw.rect(self.screen, (100,100,100), ph_rect, 1)

            # draw toggle button (below the slot)
            toggle_rect = pygame.Rect(rect.x + (rect.w - 68)//2, rect.y + rect.h + 8, 68, 28)
            if slot.get("on", False):
                color = (0, 200, 0)
                label = "On"
            else:
                color = (200, 0, 0)
                label = "Off"
            pygame.draw.rect(self.screen, color, toggle_rect, border_radius=4)
            pygame.draw.rect(self.screen, (30,30,30), toggle_rect, 2, border_radius=4)
            txt = self.small_font.render(label, True, (255,255,255))
            self.screen.blit(txt, (toggle_rect.centerx - txt.get_width()//2, toggle_rect.centery - txt.get_height()//2))

            # if item present draw minimal preview (icon or name)
            if slot["item"]:
                item = slot["item"]
                icon_path = item.get("icon_path")
                if icon_path and os.path.exists(icon_path):
                    try:
                        icon = pygame.image.load(icon_path).convert_alpha()
                        icon = pygame.transform.smoothscale(icon, (rect.w-24, rect.h//2 - 8))
                        self.screen.blit(icon, (rect.x + (rect.w - icon.get_width())//2, rect.y + rect.h//2 - icon.get_height()//2))
                    except Exception:
                        self._draw_item_text(item, rect)
                else:
                    self._draw_item_text(item, rect)

            # overlay for room stats handled by main draw overlay (drawn on top)
            pass

        # draw back button
        self.back_button.draw(self.screen)

    def draw_remove_button(self, surface):
        """Draw remove button on top of everything (call this after item_bar.draw in main)."""
        if self.remove_button:
            self.remove_button.draw(surface)

    def _draw_item_text(self, item, rect):
        txt = self._render_text_fit(item.get("name",""), rect.w-12)
        self.screen.blit(txt, (rect.x + (rect.w - txt.get_width())//2, rect.y + rect.h//2 - txt.get_height()//2))

    def _slot_rect(self, idx):
        total_width = len(self.slots) * self.slot_size + (len(self.slots)-1) * self.slot_gap
        start_x = max(20, self.screen.get_width()//2 - total_width//2)
        x = start_x + idx * (self.slot_size + self.slot_gap)
        return pygame.Rect(x, self.slot_top, self.slot_size, self.slot_size)

    def _render_text_fit(self, text, max_w, bold=False, start_sizes=None):
        """Return a Surface with text rendered small enough to fit inside max_w.
           Tries decreasing font sizes then truncates with ellipsis if needed.
           start_sizes: optional iterable of sizes to try first.
        """
        if start_sizes:
            sizes = tuple(start_sizes) + (26, 24, 22, 20, 18, 16, 14, 12, 10, 8)
        else:
            sizes = (28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8)

        for size in sizes:
            f = pygame.font.SysFont(None, size, bold=bold)
            w, h = f.size(text)
            if w <= max_w:
                return f.render(text, True, (230,230,230))

        # truncate with ellipsis as last resort
        f = pygame.font.SysFont(None, 8, bold=bold)
        txt = text
        while txt and f.size(txt + '…')[0] > max_w:
            txt = txt[:-1]
        return f.render((txt + '…') if txt else '…', True, (230,230,230))

    def get_selected_slot_info(self):
        """Return (rect, item) for selected_slot_idx if any, else (None, None)."""
        if self.selected_slot_idx is None:
            return None, None
        idx = self.selected_slot_idx
        rect = self._slot_rect(idx)
        item = self.slots[idx].get('item')
        return rect, item

# if any default slot category strings exist replace them, e.g.:
    {"name": "Slot 1", "category": "ElectricsAndThermo"},
