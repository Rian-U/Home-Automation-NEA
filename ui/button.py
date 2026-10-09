import pygame

class Button:
    def __init__(self, x, y, w, h, text, callback, font=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.color = pygame.Color('gray15')
        self.font = font or pygame.font.SysFont(None, 36)
        self.txt_surface = self.font.render(text, True, (255,255,255))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        screen.blit(self.txt_surface, (self.rect.x+10, self.rect.y+10))