import os
import pygame
from ui.button import Button


class ItemBar:
    def __init__(self, screen, font, small_font, categories, height=96,
                 on_category_change=None, on_item_click=None,
                 placeholder_size=72, placeholder_gap=10):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.categories = categories or []
        self.on_category_change = on_category_change
        self.on_item_click = on_item_click

        self.height = height
        self.rect = pygame.Rect(0, 0, screen.get_width(), self.height)

        self.placeholder_size = placeholder_size
        self.placeholder_gap = placeholder_gap

        self.item_font = pygame.font.SysFont(None, 28)

        self.selected_category = self.categories[0] if self.categories else None
        self.selected_item = None
        self.selected_item_rect = None

        self.category_buttons = []
        self.item_placeholders = []  # list of (rect, item)
        self.icon_cache = {}

        self._layout_categories(self.rect.w)

    def _layout_categories(self, width):
        padding = 10
        n = max(1, len(self.categories))
        btn_w = max(80, (width - padding * (n + 1)) // n)
        btn_h = 36
        x = padding

        self.category_buttons = []
        for cat in self.categories:
            def make_cb(c=cat):
                def cb():
                    self.selected_category = c
                    if self.on_category_change:
                        self.on_category_change(c)
                return cb

            btn = Button(x, 6, btn_w, btn_h, cat, make_cb(), font=self.small_font)
            self.category_buttons.append(btn)
            x += btn_w + padding

    def set_items(self, items):
        # populate placeholders from left to right under the categories
        self.item_placeholders = []
        if not items:
            return
        y = 6 + 36 + 8
        x = 10
        w = self.placeholder_size
        h = self.placeholder_size
        sw = self.rect.w
        for itm in items:
            if x + w > sw - 10:
                # move to next row (if bar taller this could be allowed)
                break
            r = pygame.Rect(x, y, w, h)
            self.item_placeholders.append((r, itm))
            x += w + self.placeholder_gap

    def handle_event(self, event):
        # let buttons handle their own clicks
        for btn in self.category_buttons:
            btn.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = False
            for rect, item in self.item_placeholders:
                if rect.collidepoint(event.pos):
                    hit = True
                    self.selected_item = item
                    self.selected_item_rect = rect
                    if item and self.on_item_click:
                        self.on_item_click(item)
                    break
            if not hit:
                self.selected_item = None
                self.selected_item_rect = None

    def _render_text_fit(self, text, max_width, font=None):
        font = font or self.item_font
        surf = font.render(text, True, (255, 255, 255))
        if surf.get_width() <= max_width:
            return surf
        # naive shrink loop
        size = font.get_height()
        while surf.get_width() > max_width and size > 8:
            size -= 2
            f = pygame.font.SysFont(None, size)
            surf = f.render(text, True, (255, 255, 255))
        return surf

    def _render_two_line(self, a, b, max_w, max_h):
        f1 = self._render_text_fit(a, max_w, font=self.item_font)
        f2 = self._render_text_fit(b, max_w, font=self.item_font)
        surf = pygame.Surface((max_w, f1.get_height() + f2.get_height()), pygame.SRCALPHA)
        surf.blit(f1, (0, 0))
        surf.blit(f2, (0, f1.get_height()))
        return surf

    def _blit_text_centered(self, surf, rect):
        x = rect.centerx - surf.get_width() // 2
        y = rect.centery - surf.get_height() // 2
        self.screen.blit(surf, (x, y))

    def draw(self):
        pygame.draw.rect(self.screen, (40, 40, 40), self.rect)

        # draw category buttons
        for btn in self.category_buttons:
            btn.draw(self.screen)
            if btn.text == self.selected_category:
                pygame.draw.rect(self.screen, (200, 200, 60), pygame.Rect(btn.rect.x, btn.rect.bottom - 3, btn.rect.w, 3))

        # draw placeholders
        for rect, item in self.item_placeholders:
            pygame.draw.rect(self.screen, (60, 60, 60), rect)
            pygame.draw.rect(self.screen, (120, 120, 120), rect, 2)
            if item:
                icon_path = item.get("icon_path")
                if icon_path:
                    if icon_path not in self.icon_cache:
                        try:
                            if os.path.exists(icon_path):
                                surf = pygame.image.load(icon_path).convert_alpha()
                                surf = pygame.transform.smoothscale(surf, (rect.w - 8, rect.h - 8))
                                self.icon_cache[icon_path] = surf
                            else:
                                self.icon_cache[icon_path] = None
                        except Exception:
                            self.icon_cache[icon_path] = None
                    surf = self.icon_cache.get(icon_path)
                    if surf:
                        self.screen.blit(surf, (rect.x + (rect.w - surf.get_width()) // 2, rect.y + (rect.h - surf.get_height()) // 2))
                    else:
                        name = item.get("name", "")
                        if len(name.split()) == 2:
                            w1, w2 = name.split()
                            txt = self._render_two_line(w1, w2, rect.w - 8, rect.h - 8)
                            self._blit_text_centered(txt, rect)
                        else:
                            txt = self._render_text_fit(name, rect.w - 8, font=self.small_font)
                            self._blit_text_centered(txt, rect)
                else:
                    # no icon path provided - render name directly
                    name = item.get("name", "")
                    if len(name.split()) == 2:
                        w1, w2 = name.split()
                        txt = self._render_two_line(w1, w2, rect.w - 8, rect.h - 8)
                        self._blit_text_centered(txt, rect)
                    else:
                        txt = self._render_text_fit(name, rect.w - 8, font=self.small_font)
                        self._blit_text_centered(txt, rect)

    def draw_overlay(self, surface):
        if not (self.selected_item and self.selected_item_rect):
            return
        it = self.selected_item
        try:
            epm = float(it.get('energy_per_min', 0.0))
            costk = float(it.get('cost_per_kwh', 0.0))
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
        remote = 'Yes' if (it.get('name') in SMART_REMOTE_LOCAL) else 'No'
        lines = [f"Energy/min: {epm:.6f} kWh", f"Cost/kWh: £{costk:.2f}", f"Remote: {remote}"]
        w = max(self.selected_item_rect.w, 160)
        h = (self.small_font.get_height() + 4) * len(lines) + 8
        px = self.selected_item_rect.x
        py = self.selected_item_rect.y + self.selected_item_rect.h + 6
        sw = surface.get_width()
        if px + w > sw - 8:
            px = max(8, sw - w - 8)
        panel = pygame.Rect(px, py, w, h)
        pygame.draw.rect(surface, (24, 24, 24), panel)
        pygame.draw.rect(surface, (100, 100, 100), panel, 1)
        ly = panel.y + 6
        for line in lines:
            surf = self.small_font.render(line, True, (230, 230, 230))
            surface.blit(surf, (panel.x + 8, ly))
            ly += self.small_font.get_height() + 4

    def get_selected_category(self):
        return self.selected_category

    def get_selected_item(self):
        return self.selected_item

    def resize(self, width):
        self.rect.w = width
        self._layout_categories(width)
        if self.item_placeholders:
            items = [itm for (_, itm) in self.item_placeholders]
            self.set_items(items)

    def get_item_at_pos(self, pos):
        """Return (item, rect) if the given screen `pos` is over an item placeholder."""
        for rect, item in self.item_placeholders:
            if rect.collidepoint(pos):
                return item, rect
        return None, None

    def create_item_surface(self, item, size):
        """Create a drawable surface representing `item` for dragging preview.

        Returns a Surface sized (size,size).
        """
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # draw a simple background box
        pygame.draw.rect(surf, (60, 60, 60), (0, 0, size, size))
        pygame.draw.rect(surf, (120, 120, 120), (0, 0, size, size), 2)
        # render icon if present
        icon_path = item.get('icon_path') if isinstance(item, dict) else None
        if icon_path:
            try:
                if icon_path not in self.icon_cache:
                    if os.path.exists(icon_path):
                        i = pygame.image.load(icon_path).convert_alpha()
                        i = pygame.transform.smoothscale(i, (size - 8, size - 8))
                        self.icon_cache[icon_path] = i
                    else:
                        self.icon_cache[icon_path] = None
                ico = self.icon_cache.get(icon_path)
                if ico:
                    surf.blit(ico, ((size - ico.get_width()) // 2, (size - ico.get_height()) // 2))
                    return surf
            except Exception:
                pass
        # fallback: render item name
        name = item.get('name') if isinstance(item, dict) else str(item)
        txt = self._render_text_fit(name, size - 8, font=self.item_font)
        surf.blit(txt, ((size - txt.get_width()) // 2, (size - txt.get_height()) // 2))
        return surf