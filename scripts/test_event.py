import pygame
import time

pygame.init()
screen = pygame.display.set_mode((200,200))
print('pygame init ok')
for i in range(10):
    try:
        ev = pygame.event.get()
        print('got', len(ev))
    except Exception as e:
        import traceback
        traceback.print_exc()
    time.sleep(0.5)
pygame.quit()
print('done')
