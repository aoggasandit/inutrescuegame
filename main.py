"""Rescue Run: a small, asset-free pygame game for teaching and testing.

Controls: move with WASD/arrow keys, aim with the mouse, hold left-click to
fire, press E near the civilian to rescue them, and press R to restart.
"""

from __future__ import annotations

import sys

import pygame


# --- Setup and game tuning -------------------------------------------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60
PLAYER_SPEED = 250.0
BULLET_SPEED = 620.0
SHOT_DELAY = 0.22

NAVY = (14, 23, 39)
FLOOR = (28, 43, 57)
GRID = (37, 54, 67)
WHITE = (239, 245, 247)
MUTED = (158, 178, 191)
CYAN = (66, 215, 222)
GREEN = (81, 220, 145)
RED = (247, 94, 104)
YELLOW = (255, 205, 92)
WALL = (68, 87, 101)


class Bullet:
    """A short-lived projectile that travels in a straight line."""

    def __init__(self, position: tuple[float, float], direction: pygame.Vector2):
        self.position = pygame.Vector2(position)
        self.velocity = direction * BULLET_SPEED
        self.life = 1.3
        self.radius = 5

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        self.life -= dt

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, YELLOW, self.position, self.radius)
        pygame.draw.circle(surface, WHITE, self.position, 2)


class Robot:
    """A simple training robot that follows the player and can be disabled."""

    def __init__(self, x: int, y: int, number: int):
        self.rect = pygame.Rect(x, y, 38, 38)
        self.number = number
        self.speed = 75.0 + number * 5
        self.active = True

    def update(self, dt: float, target: pygame.Rect, walls: list[pygame.Rect]) -> None:
        if not self.active:
            return

        direction = pygame.Vector2(target.center) - pygame.Vector2(self.rect.center)
        if direction.length_squared() > 1:
            direction = direction.normalize()
            move = direction * self.speed * dt
            self._move_axis(move.x, walls, horizontal=True)
            self._move_axis(move.y, walls, horizontal=False)

    def _move_axis(self, amount: float, walls: list[pygame.Rect], horizontal: bool) -> None:
        if horizontal:
            self.rect.x += round(amount)
        else:
            self.rect.y += round(amount)
        for wall in walls:
            if self.rect.colliderect(wall):
                if horizontal:
                    self.rect.right = wall.left if amount > 0 else wall.right
                else:
                    self.rect.bottom = wall.top if amount > 0 else wall.bottom

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.active:
            pygame.draw.circle(surface, (83, 103, 111), self.rect.center, 18, 2)
            pygame.draw.line(surface, MUTED, self.rect.topleft, self.rect.bottomright, 3)
            pygame.draw.line(surface, MUTED, self.rect.topright, self.rect.bottomleft, 3)
            return

        pygame.draw.rect(surface, RED, self.rect, border_radius=10)
        pygame.draw.rect(surface, (255, 151, 151), self.rect, 2, border_radius=10)
        pygame.draw.circle(surface, NAVY, (self.rect.centerx - 7, self.rect.centery), 3)
        pygame.draw.circle(surface, NAVY, (self.rect.centerx + 7, self.rect.centery), 3)
        label = font.render(str(self.number), True, WHITE)
        surface.blit(label, label.get_rect(center=(self.rect.centerx, self.rect.bottom + 11)))


class RescueRun:
    """Owns the game state, update loop, and drawing helpers."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Rescue Run | pygame mini-game")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 20)
        self.large_font = pygame.font.Font(None, 58)
        self.reset()

    def reset(self) -> None:
        """Start a fresh round; keeping this in one method makes reset reliable."""
        self.player = pygame.Rect(90, 535, 34, 42)
        self.player_health = 100
        self.player_speed = PLAYER_SPEED
        self.bullets: list[Bullet] = []
        self.robots = [Robot(420, 190, 1), Robot(610, 390, 2), Robot(790, 190, 3)]
        self.walls = [
            pygame.Rect(220, 130, 42, 190),
            pygame.Rect(365, 355, 220, 38),
            pygame.Rect(680, 115, 42, 190),
            pygame.Rect(700, 465, 160, 38),
        ]
        self.civilian = pygame.Vector2(850, 145)
        self.extraction = pygame.Rect(865, 560, 90, 74)
        self.rescued = False
        self.state = "playing"
        self.shot_timer = 0.0
        self.damage_timer = 0.0
        self.message = "Disable all 3 training bots, then rescue the civilian."
        self.message_timer = 4.0

    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            running = self.handle_events()
            if self.state == "playing":
                self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r:
                    self.reset()
                if event.key == pygame.K_e and self.state == "playing":
                    self.try_rescue()
        return True

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        movement = pygame.Vector2(
            float(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - float(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            float(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - float(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if movement.length_squared() > 0:
            movement = movement.normalize() * self.player_speed * dt
            self.move_player(movement)

        self.shot_timer = max(0.0, self.shot_timer - dt)
        self.damage_timer = max(0.0, self.damage_timer - dt)
        if pygame.mouse.get_pressed()[0] and self.shot_timer == 0:
            self.shoot()

        for robot in self.robots:
            robot.update(dt, self.player, self.walls)
            if robot.active and self.player.colliderect(robot.rect) and self.damage_timer == 0:
                self.player_health -= 15
                self.damage_timer = 0.65
                self.show_message("Ouch! Keep moving to avoid the training bots.", 1.3)

        for bullet in self.bullets:
            bullet.update(dt)
            if any(bullet.position.distance_to(robot.rect.center) < 24 for robot in self.robots if robot.active):
                for robot in self.robots:
                    if robot.active and bullet.position.distance_to(robot.rect.center) < 24:
                        robot.active = False
                        break
                bullet.life = 0
            if any(wall.collidepoint(bullet.position) for wall in self.walls):
                bullet.life = 0
        self.bullets = [
            bullet for bullet in self.bullets
            if bullet.life > 0
            and -20 < bullet.position.x < SCREEN_WIDTH + 20
            and -20 < bullet.position.y < SCREEN_HEIGHT + 20
        ]

        if self.player_health <= 0:
            self.state = "lost"
        elif self.rescued and self.player.colliderect(self.extraction):
            self.state = "won"

        if self.message_timer > 0:
            self.message_timer -= dt

    def move_player(self, movement: pygame.Vector2) -> None:
        """Move on each axis separately so walls block the player cleanly."""
        self.player.x += round(movement.x)
        for wall in self.walls:
            if self.player.colliderect(wall):
                self.player.right = wall.left if movement.x > 0 else wall.right

        self.player.y += round(movement.y)
        for wall in self.walls:
            if self.player.colliderect(wall):
                self.player.bottom = wall.top if movement.y > 0 else wall.bottom

        self.player.clamp_ip(pygame.Rect(12, 78, SCREEN_WIDTH - 24, SCREEN_HEIGHT - 90))

    def shoot(self) -> None:
        mouse = pygame.Vector2(pygame.mouse.get_pos())
        direction = mouse - pygame.Vector2(self.player.center)
        if direction.length_squared() == 0:
            return
        direction = direction.normalize()
        muzzle = pygame.Vector2(self.player.center) + direction * 24
        self.bullets.append(Bullet(muzzle, direction))
        self.shot_timer = SHOT_DELAY

    def try_rescue(self) -> None:
        bots_remaining = sum(robot.active for robot in self.robots)
        distance = pygame.Vector2(self.player.center).distance_to(self.civilian)
        if bots_remaining:
            self.show_message(f"Disable the remaining {bots_remaining} bot(s) first.", 2.0)
        elif distance > 65:
            self.show_message("Move closer to the civilian, then press E.", 2.0)
        else:
            self.rescued = True
            self.show_message("Civilian rescued! Reach the green extraction zone.", 3.0)

    def show_message(self, text: str, duration: float) -> None:
        self.message = text
        self.message_timer = duration

    def draw(self) -> None:
        self.screen.fill(FLOOR)
        self.draw_grid()
        self.draw_world()
        self.draw_hud()
        self.draw_end_overlay()
        pygame.display.flip()

    def draw_grid(self) -> None:
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, GRID, (x, 72), (x, SCREEN_HEIGHT), 1)
        for y in range(80, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, GRID, (0, y), (SCREEN_WIDTH, y), 1)

    def draw_world(self) -> None:
        # Extraction is visible from the start so the objective is easy to learn.
        pygame.draw.rect(self.screen, (27, 74, 61), self.extraction, border_radius=12)
        pygame.draw.rect(self.screen, GREEN, self.extraction, 2, border_radius=12)
        exit_text = self.small_font.render("EXTRACT", True, GREEN)
        self.screen.blit(exit_text, exit_text.get_rect(center=self.extraction.center))

        for wall in self.walls:
            pygame.draw.rect(self.screen, WALL, wall, border_radius=7)
            pygame.draw.rect(self.screen, (105, 128, 139), wall, 2, border_radius=7)

        if not self.rescued:
            self.draw_person(self.civilian, YELLOW, "CIVILIAN")
        else:
            # The rescued civilian walks beside the player as a clear escort cue.
            escort_position = pygame.Vector2(self.player.center) + pygame.Vector2(-30, 22)
            self.draw_person(escort_position, YELLOW, "")

        for robot in self.robots:
            robot.draw(self.screen, self.small_font)

        self.draw_player()
        for bullet in self.bullets:
            bullet.draw(self.screen)

    def draw_player(self) -> None:
        mouse = pygame.Vector2(pygame.mouse.get_pos())
        direction = mouse - pygame.Vector2(self.player.center)
        if direction.length_squared() > 0:
            direction = direction.normalize()
            end = pygame.Vector2(self.player.center) + direction * 29
            pygame.draw.line(self.screen, (205, 229, 233), self.player.center, end, 6)
        tint = (104, 196, 207) if self.damage_timer <= 0 or int(self.damage_timer * 12) % 2 else WHITE
        pygame.draw.rect(self.screen, CYAN, self.player, border_radius=10)
        pygame.draw.circle(self.screen, tint, (self.player.centerx, self.player.y + 9), 8)
        pygame.draw.rect(self.screen, (17, 91, 106), self.player, 2, border_radius=10)

    def draw_person(self, position: pygame.Vector2, color: tuple[int, int, int], label: str) -> None:
        center = (round(position.x), round(position.y))
        pygame.draw.circle(self.screen, color, (center[0], center[1] - 8), 9)
        pygame.draw.line(self.screen, color, (center[0], center[1]), (center[0], center[1] + 16), 5)
        pygame.draw.line(self.screen, color, (center[0], center[1] + 5), (center[0] - 9, center[1] + 13), 4)
        pygame.draw.line(self.screen, color, (center[0], center[1] + 5), (center[0] + 9, center[1] + 13), 4)
        if label:
            name = self.small_font.render(label, True, color)
            self.screen.blit(name, name.get_rect(center=(center[0], center[1] + 31)))

    def draw_hud(self) -> None:
        pygame.draw.rect(self.screen, NAVY, (0, 0, SCREEN_WIDTH, 72))
        pygame.draw.line(self.screen, (56, 78, 92), (0, 71), (SCREEN_WIDTH, 71), 2)

        title = self.font.render("RESCUE RUN", True, WHITE)
        self.screen.blit(title, (22, 15))
        active_bots = sum(robot.active for robot in self.robots)
        objective = f"BOTS  {len(self.robots) - active_bots}/{len(self.robots)}     "
        objective += "CIVILIAN  RESCUED" if self.rescued else "CIVILIAN  WAITING"
        self.screen.blit(self.small_font.render(objective, True, MUTED), (22, 43))

        # Draw health as both text and a bar for readable feedback.
        health_x = 525
        self.screen.blit(self.small_font.render("HEALTH", True, MUTED), (health_x, 13))
        pygame.draw.rect(self.screen, (56, 70, 82), (health_x, 38, 150, 14), border_radius=7)
        health_color = GREEN if self.player_health > 50 else YELLOW if self.player_health > 25 else RED
        pygame.draw.rect(
            self.screen,
            health_color,
            (health_x, 38, max(0, round(150 * self.player_health / 100)), 14),
            border_radius=7,
        )
        self.screen.blit(self.small_font.render(f"{max(0, self.player_health)}%", True, WHITE), (685, 35))
        controls = "WASD / arrows: move   •   Mouse: aim   •   Hold click: fire   •   E: rescue   •   R: restart"
        control_surface = self.small_font.render(controls, True, MUTED)
        self.screen.blit(control_surface, (SCREEN_WIDTH - control_surface.get_width() - 18, 17))

        if self.message_timer > 0:
            text = self.font.render(self.message, True, WHITE)
            box = text.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)).inflate(28, 18)
            pygame.draw.rect(self.screen, NAVY, box, border_radius=9)
            pygame.draw.rect(self.screen, (70, 99, 111), box, 1, border_radius=9)
            self.screen.blit(text, text.get_rect(center=box.center))

    def draw_end_overlay(self) -> None:
        if self.state == "playing":
            return
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((5, 10, 18, 185))
        self.screen.blit(shade, (0, 0))
        heading = "RESCUE COMPLETE!" if self.state == "won" else "MISSION FAILED"
        color = GREEN if self.state == "won" else RED
        title = self.large_font.render(heading, True, color)
        prompt = self.font.render("Press R to play again  •  Esc to quit", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 25)))
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))


def main() -> None:
    """Create the game and hand control to its main loop."""
    RescueRun().run()


if __name__ == "__main__":
    main()
