import pygame

MAPS = {
    "Map 1": "assets/map1_bg.png",
    "Map 2": "assets/map2_bg.png",
    "Map 3": "assets/map3_bg.jpg"
}

ROOMS = {
    "Map 1": {
        "bedroom": pygame.Rect(175, 175, 175, 110),
        "bathroom": pygame.Rect(150, 350, 100, 110),
        "office": pygame.Rect(340, 200, 140, 100),
        "living_room": pygame.Rect(480, 350, 150, 110),
        "kitchen": pygame.Rect(375, 350, 100, 110),
        "bedroom2": pygame.Rect(480, 190, 200, 110),
    },
    "Map 2": {
        "bedroom": pygame.Rect(100, 90, 180, 100),
        "bathroom": pygame.Rect(290, 80, 180, 100),
        "office": pygame.Rect(490, 90, 180, 100),
        "bedroom2": pygame.Rect(100, 270, 180, 100),
        "living_room": pygame.Rect(490, 250, 180, 100),
        "kitchen": pygame.Rect(320, 340, 180, 100),
    },
    "Map 3": {
        "bedroom": pygame.Rect(80, 80, 160, 90),
        "bathroom": pygame.Rect(260, 80, 160, 90),
        "office": pygame.Rect(440, 80, 160, 90),
        "living_room": pygame.Rect(80, 190, 160, 90),
        "dining": pygame.Rect(260, 190, 160, 90),
        "kitchen": pygame.Rect(440, 190, 160, 90),
    }
}

# per-room slot configuration (normalized category names)
# Rules applied:
# - Bedrooms: ElectricsAndThermo (lighting), ElectricsAndThermo (plug), Miscellaneous
# - Offices: ElectricsAndThermo (lighting), ElectricsAndThermo (plug), ElectricsAndThermo (desklight), Miscellaneous
# - Living rooms: ElectricsAndThermo (lighting), ElectricsAndThermo (plug), ElectricsAndThermo (thermostat), Miscellaneous
# - Bathrooms: ElectricsAndThermo (lighting), Miscellaneous, Appliances
# - Dining: ElectricsAndThermo (lighting), Miscellaneous
# - Kitchens: ElectricsAndThermo (lighting), ElectricsAndThermo (plug), Appliances, Miscellaneous
ROOM_SLOTS = {
    "Map 1": {
        "bedroom": [
            {"name": "Ceiling Light", "category": "ElectricsAndThermo"},
            {"name": "Side Plug", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "bedroom2": [
            {"name": "Ceiling Light", "category": "ElectricsAndThermo"},
            {"name": "Side Plug", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "bathroom": [
            {"name": "Vanity Light", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
            {"name": "Appliance Slot", "category": "Appliances"},
        ],
        "office": [
            {"name": "Desk Light", "category": "ElectricsAndThermo"},
            {"name": "Desk Plug", "category": "ElectricsAndThermo"},
            {"name": "Desk Lamp", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "living_room": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": "TV Plug", "category": "ElectricsAndThermo"},
            {"name": "Thermostat", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "kitchen": [
            {"name": "Ceiling Light", "category": "ElectricsAndThermo"},
            {"name": "Counter Plug", "category": "ElectricsAndThermo"},
            {"name": "Appliance Slot", "category": "Appliances"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
    },
    "Map 2": {
        "bedroom": [
            {"name": "Ceiling Light", "category": "ElectricsAndThermo"},
            {"name": "Side Plug", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "bathroom": [
            {"name": "Vanity Light", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
            {"name": "Appliance Slot", "category": "Appliances"},
        ],
        "office": [
            {"name": "Desk Light", "category": "ElectricsAndThermo"},
            {"name": "Desk Plug", "category": "ElectricsAndThermo"},
            {"name": "Desk Lamp", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "living_room": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": " TV Plug", "category": "ElectricsAndThermo"},
            {"name": "Thermostat", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "dining": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "kitchen": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": "Counter Plug", "category": "ElectricsAndThermo"},
            {"name": "Appliance Slot", "category": "Appliances"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
    },
    "Map 3": {
        "bedroom": [
            {"name": "Ceiling Light", "category": "ElectricsAndThermo"},
            {"name": "Side Plug", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "bathroom": [
            {"name": "Vanity Light", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
            {"name": "Appliance Slot", "category": "Appliances"},
        ],
        "office": [
            {"name": "Desk Light", "category": "ElectricsAndThermo"},
            {"name": "Desk Plug", "category": "ElectricsAndThermo"},
            {"name": "Desk Lamp", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "living_room": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": "TV Plug", "category": "ElectricsAndThermo"},
            {"name": "Thermostat", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "dining": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
        "kitchen": [
            {"name": "Main Light", "category": "ElectricsAndThermo"},
            {"name": "Counter Plug", "category": "ElectricsAndThermo"},
            {"name": "Appliance Slot", "category": "Appliances"},
            {"name": "Misc Slot", "category": "Miscellaneous"},
        ],
    }
}

class Map:
    def __init__(self, screen, bg_path, rooms, y_offset=100):
        self.screen = screen
        self.y_offset = y_offset

        loaded = pygame.image.load(bg_path).convert()
        self.bg = pygame.transform.scale(loaded, (screen.get_width(), screen.get_height() - self.y_offset))
        self.bg_rect = self.bg.get_rect(topleft=(0, self.y_offset))

        self.rooms = {name: rect.copy().move(0, self.y_offset) for name, rect in rooms.items()}

        self.selected_room = None
        self.hovered_room = None
        self.room_items = {name: None for name in self.rooms}

    def draw(self):
        self.screen.blit(self.bg, self.bg_rect.topleft)
        for name, rect in self.rooms.items():
            if name == self.selected_room:
                pygame.draw.rect(self.screen, (0, 200, 0), rect, 3)
            elif name == self.hovered_room:
                pygame.draw.rect(self.screen, (200, 100, 0), rect, 3)
            item = self.room_items.get(name)
            if item:
                pygame.draw.circle(self.screen, (0, 0, 255), rect.center, min(rect.w, rect.h)//6)
            # render room name centered inside the rect
            try:
                display_name = name.replace('_', ' ').title()
                # choose font size proportional to rect height
                base_size = max(12, min(24, rect.h // 5))
                font = pygame.font.SysFont(None, base_size)
                txt_surf = font.render(display_name, True, (255, 255, 255))
                # shrink until it fits within rect (with padding)
                pad = 8
                while txt_surf.get_width() > rect.w - pad and base_size > 10:
                    base_size -= 1
                    font = pygame.font.SysFont(None, base_size)
                    txt_surf = font.render(display_name, True, (255, 255, 255))

                # draw semi-transparent background behind label for readability
                bg_w = txt_surf.get_width() + 8
                bg_h = txt_surf.get_height() + 6
                label_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
                label_surf.fill((20, 20, 20, 180))
                # blit background then text centered
                lx = rect.centerx - bg_w // 2
                ly = rect.centery - bg_h // 2
                self.screen.blit(label_surf, (lx, ly))
                self.screen.blit(txt_surf, (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))
            except Exception:
                # be silent on render errors
                pass

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered_room = None
            for name, rect in self.rooms.items():
                if rect.collidepoint(event.pos):
                    self.hovered_room = name
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.selected_room = None
            for name, rect in self.rooms.items():
                if rect.collidepoint(event.pos):
                    self.selected_room = name
                    print(f"Selected room: {name}")
                    break

    def place_item_in_room(self, room_name, item):
        if room_name in self.room_items:
            self.room_items[room_name] = item

    def get_selected_room(self):
        return self.selected_room
