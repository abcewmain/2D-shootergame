import math
import random
import time
import tkinter as tk
from dataclasses import dataclass


WIDTH = 960
HEIGHT = 640
ARENA = (32, 92, 928, 608)
PLAYER_SPEED = 225
BOT_SPEED = 112
BOT_COUNT = 5
WIN_SCORE = 15
ROUND_TIME = 180

COLORS = {
    "background": "#111923",
    "grid": "#1a2834",
    "panel": "#182630",
    "panel_edge": "#30434b",
    "text": "#e9eedb",
    "muted": "#8fa4a1",
    "player": "#67e8d1",
    "bot": "#ff9f70",
    "bullet_player": "#d4fff1",
    "bullet_bot": "#ffc087",
    "cover": "#293b43",
    "cover_edge": "#466068",
    "accent": "#e9ce78",
    "zone": "#6ce4b5",
    "danger": "#ff6d73",
}

OBSTACLES = (
    (218, 180, 328, 206),
    (632, 180, 742, 206),
    (218, 435, 328, 461),
    (632, 435, 742, 461),
    (458, 153, 502, 234),
    (458, 389, 502, 470),
    (390, 288, 438, 315),
    (522, 325, 570, 352),
)

SPAWNS = (
    (90, 130),
    (870, 130),
    (90, 570),
    (870, 570),
    (480, 120),
    (480, 580),
    (130, 350),
    (830, 350),
)

OBJECTIVE = (480, 314)


@dataclass
class Fighter:
    x: float
    y: float
    health: float
    cooldown: float = 0.0
    hit_flash: float = 0.0


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    owner: str
    life: float = 1.5


def circle_touches_rectangle(x, y, radius, rectangle):
    left, top, right, bottom = rectangle
    closest_x = min(max(x, left), right)
    closest_y = min(max(y, top), bottom)
    dx = x - closest_x
    dy = y - closest_y
    return dx * dx + dy * dy < radius * radius


def can_stand(x, y, radius):
    left, top, right, bottom = ARENA
    if x - radius < left or x + radius > right:
        return False
    if y - radius < top or y + radius > bottom:
        return False
    return not any(
        circle_touches_rectangle(x, y, radius, obstacle)
        for obstacle in OBSTACLES
    )


def move_fighter(fighter, dx, dy, radius):
    next_x = fighter.x + dx
    if can_stand(next_x, fighter.y, radius):
        fighter.x = next_x
    next_y = fighter.y + dy
    if can_stand(fighter.x, next_y, radius):
        fighter.y = next_y


class Breachline:
    def __init__(self, root):
        self.root = root
        root.title("BREACHLINE  /  Field Test")
        root.configure(bg=COLORS["background"])
        root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg=COLORS["background"],
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack()

        self.keys = set()
        self.mouse_x = WIDTH / 2
        self.mouse_y = HEIGHT / 2
        self.mouse_down = False
        self.last_frame = time.perf_counter()
        self.mode = "UPLINK"
        self.reset_match()

        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        self.canvas.bind("<Motion>", self.mouse_move)
        self.canvas.bind("<ButtonPress-1>", self.mouse_press)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_release)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        self.tick()

    def reset_match(self):
        self.player = Fighter(120, 350, 100)
        self.bots = []
        self.bullets = []
        self.player_score = 0
        self.bot_score = 0
        self.uplink_progress = 0
        self.match_time = ROUND_TIME
        self.game_over = False
        self.message = ""
        self.player_fire_cooldown = 0
        self.spawn_bots()

    def spawn_bots(self):
        self.bots.clear()
        for _ in range(BOT_COUNT):
            x, y = random.choice(SPAWNS[1:])
            self.bots.append(Fighter(x, y, 65, random.uniform(0.1, 0.8)))

    def key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key == "escape":
            self.root.destroy()
        elif key == "r":
            self.reset_match()
        elif key == "tab":
            self.mode = "DEATHMATCH" if self.mode == "UPLINK" else "UPLINK"
            self.reset_match()

    def key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def mouse_press(self, _event):
        self.mouse_down = True

    def mouse_release(self, _event):
        self.mouse_down = False

    def tick(self):
        now = time.perf_counter()
        dt = min(now - self.last_frame, 0.04)
        self.last_frame = now

        if not self.game_over:
            self.update(dt)
        self.draw()
        self.root.after(16, self.tick)

    def update(self, dt):
        self.match_time = max(0, self.match_time - dt)
        self.player_fire_cooldown = max(0, self.player_fire_cooldown - dt)
        self.player.hit_flash = max(0, self.player.hit_flash - dt)

        self.move_player(dt)
        if self.mouse_down and self.player_fire_cooldown <= 0:
            self.fire(self.player, self.mouse_x, self.mouse_y, "player")
            self.player_fire_cooldown = 0.19

        for bot in self.bots:
            self.update_bot(bot, dt)
        self.update_bullets(dt)
        self.update_uplink(dt)
        self.check_match_end()

    def move_player(self, dt):
        dx = int("d" in self.keys or "right" in self.keys) - int(
            "a" in self.keys or "left" in self.keys
        )
        dy = int("s" in self.keys or "down" in self.keys) - int(
            "w" in self.keys or "up" in self.keys
        )
        if dx == 0 and dy == 0:
            return
        length = math.hypot(dx, dy)
        speed = PLAYER_SPEED * (1.45 if "shift_l" in self.keys else 1)
        move_fighter(
            self.player,
            dx / length * speed * dt,
            dy / length * speed * dt,
            12,
        )

    def update_bot(self, bot, dt):
        bot.cooldown = max(0, bot.cooldown - dt)
        bot.hit_flash = max(0, bot.hit_flash - dt)

        dx = self.player.x - bot.x
        dy = self.player.y - bot.y
        distance = max(1, math.hypot(dx, dy))
        if distance > 185:
            move_fighter(bot, dx / distance * BOT_SPEED * dt, dy / distance * BOT_SPEED * dt, 11)
        elif distance < 115:
            move_fighter(bot, -dx / distance * BOT_SPEED * dt, -dy / distance * BOT_SPEED * dt, 11)

        if distance < 470 and bot.cooldown <= 0:
            self.fire(bot, self.player.x, self.player.y, "bot")
            bot.cooldown = random.uniform(0.85, 1.25)

    def fire(self, fighter, target_x, target_y, owner):
        dx = target_x - fighter.x
        dy = target_y - fighter.y
        distance = max(1, math.hypot(dx, dy))
        if owner == "bot":
            dx += random.uniform(-distance * 0.055, distance * 0.055)
            dy += random.uniform(-distance * 0.055, distance * 0.055)
            distance = max(1, math.hypot(dx, dy))
        speed = 610 if owner == "player" else 400
        self.bullets.append(
            Bullet(
                fighter.x + dx / distance * 16,
                fighter.y + dy / distance * 16,
                dx / distance * speed,
                dy / distance * speed,
                owner,
            )
        )

    def update_bullets(self, dt):
        remaining = []
        for bullet in self.bullets:
            bullet.x += bullet.vx * dt
            bullet.y += bullet.vy * dt
            bullet.life -= dt
            if bullet.life <= 0 or not can_stand(bullet.x, bullet.y, 2):
                continue

            if bullet.owner == "player":
                target = next(
                    (
                        bot
                        for bot in self.bots
                        if math.hypot(bot.x - bullet.x, bot.y - bullet.y) < 15
                    ),
                    None,
                )
                if target is not None:
                    target.health -= 34
                    target.hit_flash = 0.12
                    if target.health <= 0:
                        self.player_score += 1
                        self.bots.remove(target)
                        self.bullets = remaining
                        self.spawn_one_bot()
                    continue
            elif math.hypot(self.player.x - bullet.x, self.player.y - bullet.y) < 16:
                self.player.health -= 12
                self.player.hit_flash = 0.16
                if self.player.health <= 0:
                    self.bot_score += 1
                    self.player.health = 100
                    self.player.x, self.player.y = 120, 350
                continue
            remaining.append(bullet)
        self.bullets = remaining

    def spawn_one_bot(self):
        x, y = random.choice(SPAWNS[1:])
        self.bots.append(Fighter(x, y, 65, random.uniform(0.3, 0.9)))

    def update_uplink(self, dt):
        if self.mode != "UPLINK":
            return
        ox, oy = OBJECTIVE
        player_on_point = math.hypot(self.player.x - ox, self.player.y - oy) < 55
        bot_on_point = any(math.hypot(bot.x - ox, bot.y - oy) < 55 for bot in self.bots)
        if player_on_point and not bot_on_point:
            self.uplink_progress = min(100, self.uplink_progress + 28 * dt)
            if self.uplink_progress >= 100:
                self.player_score += 1
                self.uplink_progress = 0
        elif bot_on_point and not player_on_point:
            self.uplink_progress = max(0, self.uplink_progress - 22 * dt)
        elif not player_on_point:
            self.uplink_progress = max(0, self.uplink_progress - 10 * dt)

    def check_match_end(self):
        if self.player_score >= WIN_SCORE:
            self.game_over = True
            self.message = "FIELD CONTROL  /  YOU WIN"
        elif self.bot_score >= WIN_SCORE:
            self.game_over = True
            self.message = "SQUAD OVERWHELMED"
        elif self.match_time <= 0:
            self.game_over = True
            self.message = "MATCH COMPLETE"

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        self.draw_arena()
        self.draw_objective()
        self.draw_bullets()
        self.draw_fighter(self.player, "player")
        for bot in self.bots:
            self.draw_fighter(bot, "bot")
        self.draw_hud()
        if self.game_over:
            self.draw_end_screen()

    def draw_arena(self):
        canvas = self.canvas
        for x in range(40, WIDTH, 32):
            canvas.create_line(x, 92, x, HEIGHT, fill=COLORS["grid"])
        for y in range(100, HEIGHT, 32):
            canvas.create_line(32, y, 928, y, fill=COLORS["grid"])
        canvas.create_rectangle(
            ARENA[0],
            ARENA[1],
            ARENA[2],
            ARENA[3],
            outline=COLORS["cover_edge"],
            width=2,
        )
        for left, top, right, bottom in OBSTACLES:
            canvas.create_rectangle(
                left + 4,
                top + 5,
                right + 4,
                bottom + 5,
                fill="#0c1218",
                outline="",
            )
            canvas.create_rectangle(
                left,
                top,
                right,
                bottom,
                fill=COLORS["cover"],
                outline=COLORS["cover_edge"],
                width=2,
            )
            canvas.create_line(
                left + 8,
                top + 7,
                right - 8,
                top + 7,
                fill="#60767a",
                width=2,
            )

    def draw_objective(self):
        if self.mode != "UPLINK":
            return
        x, y = OBJECTIVE
        canvas = self.canvas
        canvas.create_oval(
            x - 48,
            y - 48,
            x + 48,
            y + 48,
            outline="#3b8c76",
            width=2,
            dash=(5, 5),
        )
        canvas.create_oval(
            x - 20,
            y - 20,
            x + 20,
            y + 20,
            fill="#203d3c",
            outline=COLORS["zone"],
            width=2,
        )
        canvas.create_text(
            x,
            y,
            text="U",
            fill=COLORS["zone"],
            font=("Consolas", 14, "bold"),
        )
        canvas.create_text(
            x,
            y + 62,
            text="UPLINK",
            fill=COLORS["zone"],
            font=("Consolas", 8, "bold"),
        )
        canvas.create_rectangle(426, 391, 534, 397, fill="#23363a", outline="")
        canvas.create_rectangle(
            426,
            391,
            426 + 108 * self.uplink_progress / 100,
            397,
            fill=COLORS["zone"],
            outline="",
        )

    def draw_fighter(self, fighter, team):
        canvas = self.canvas
        color = COLORS["player"] if team == "player" else COLORS["bot"]
        if fighter.hit_flash > 0:
            color = "#ffffff"
        radius = 13 if team == "player" else 12
        canvas.create_oval(
            fighter.x - radius + 3,
            fighter.y - radius + 4,
            fighter.x + radius + 3,
            fighter.y + radius + 4,
            fill="#0b1015",
            outline="",
        )
        canvas.create_oval(
            fighter.x - radius,
            fighter.y - radius,
            fighter.x + radius,
            fighter.y + radius,
            fill=color,
            outline="#f2f1d8",
            width=1,
        )
        if team == "player":
            dx = self.mouse_x - fighter.x
            dy = self.mouse_y - fighter.y
        else:
            dx = self.player.x - fighter.x
            dy = self.player.y - fighter.y
        length = max(1, math.hypot(dx, dy))
        canvas.create_line(
            fighter.x,
            fighter.y,
            fighter.x + dx / length * 21,
            fighter.y + dy / length * 21,
            fill=COLORS["text"],
            width=3,
        )
        if team == "bot":
            canvas.create_rectangle(
                fighter.x - 12,
                fighter.y - 20,
                fighter.x + 12,
                fighter.y - 17,
                fill="#3c2426",
                outline="",
            )
            canvas.create_rectangle(
                fighter.x - 12,
                fighter.y - 20,
                fighter.x - 12 + 24 * max(0, fighter.health) / 65,
                fighter.y - 17,
                fill=COLORS["danger"],
                outline="",
            )

    def draw_bullets(self):
        for bullet in self.bullets:
            color = COLORS["bullet_player"] if bullet.owner == "player" else COLORS["bullet_bot"]
            self.canvas.create_oval(
                bullet.x - 3,
                bullet.y - 3,
                bullet.x + 3,
                bullet.y + 3,
                fill=color,
                outline="",
            )

    def draw_hud(self):
        canvas = self.canvas
        canvas.create_rectangle(0, 0, WIDTH, 80, fill=COLORS["panel"], outline="")
        canvas.create_line(0, 79, WIDTH, 79, fill=COLORS["panel_edge"], width=2)
        canvas.create_text(
            30,
            23,
            text="BREACHLINE",
            anchor="w",
            fill=COLORS["text"],
            font=("Consolas", 19, "bold"),
        )
        canvas.create_text(
            31,
            53,
            text="FIELD TEST  /  SECTOR 04",
            anchor="w",
            fill=COLORS["muted"],
            font=("Consolas", 9),
        )
        canvas.create_text(
            349,
            22,
            text=self.mode,
            fill=COLORS["accent"],
            font=("Consolas", 11, "bold"),
        )
        canvas.create_text(
            349,
            50,
            text="YOU  {:02d}     /     HOSTILES  {:02d}".format(
                self.player_score, self.bot_score
            ),
            fill=COLORS["text"],
            font=("Consolas", 11, "bold"),
        )
        canvas.create_text(
            662,
            22,
            text="VITALS",
            fill=COLORS["muted"],
            font=("Consolas", 9),
        )
        canvas.create_rectangle(662, 37, 786, 49, fill="#3c2426", outline="")
        canvas.create_rectangle(
            662,
            37,
            662 + 124 * max(0, self.player.health) / 100,
            49,
            fill=COLORS["player"] if self.player.health > 30 else COLORS["danger"],
            outline="",
        )
        canvas.create_text(
            811,
            43,
            text=f"{max(0, int(self.match_time // 60)):02d}:{int(self.match_time % 60):02d}",
            fill=COLORS["text"],
            font=("Consolas", 16, "bold"),
        )
        canvas.create_text(
            913,
            43,
            text=f"/ {WIN_SCORE}",
            anchor="e",
            fill=COLORS["muted"],
            font=("Consolas", 9),
        )
        canvas.create_rectangle(0, HEIGHT - 25, WIDTH, HEIGHT, fill=COLORS["panel"], outline="")
        canvas.create_text(
            20,
            HEIGHT - 12,
            text="WASD MOVE     SHIFT SPRINT     MOUSE AIM     CLICK FIRE     TAB MODE     R RESTART     ESC QUIT",
            anchor="w",
            fill=COLORS["muted"],
            font=("Consolas", 9),
        )

    def draw_end_screen(self):
        canvas = self.canvas
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#0b1118", stipple="gray50", outline="")
        canvas.create_text(
            WIDTH / 2,
            HEIGHT / 2 - 25,
            text=self.message,
            fill=COLORS["text"],
            font=("Consolas", 24, "bold"),
        )
        canvas.create_text(
            WIDTH / 2,
            HEIGHT / 2 + 22,
            text="PRESS R TO DEPLOY AGAIN",
            fill=COLORS["accent"],
            font=("Consolas", 12, "bold"),
        )


def main():
    root = tk.Tk()
    Breachline(root)
    root.mainloop()


if __name__ == "__main__":
    main()
