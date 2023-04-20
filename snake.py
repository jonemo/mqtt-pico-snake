from collections import namedtuple
from micropython import const
from random import randint
import uasyncio as asyncio
import gc

# RGB565 breaks my brain.
# https://embeddednotepad.com/page/rgb565-color-picker

wall_color = const(0xF81F)
snake_color = const(0x001f)  # lcd.green
food_color = const(0x07E0)  # lcd.red
title_color = const(0xFFF0)
# score_color = (255, 255, 255)
score_color = const(0xFFFF)
background_color = const(0x0000)
# 
game_stats_bg_color = const(0xffff) # const(0xf81f) <-- this looks lime green, why!?
game_stats_text_color = const(0x1111)


KEY_NONE = const(0)
KEY_UP = const(1)
KEY_DOWN = const(2)
KEY_LEFT = const(3)
KEY_RIGHT = const(4)

GAMESTATE_READY_TO_START = const(1)
GAMESTATE_PLAYING = const(3)
GAMESTATE_SHOW_SCORE = const(4)


Direction = namedtuple("Direction", ("xdir", "ydir"))
Position = namedtuple("Position", ("x", "y"))


class SnakeNode:
    def __init__(self, position=None, direction=None, next=None):
        self.pos = position  # x/y position of the node on the grid
        self.dir = direction  # direction this node is traveling in
        self.next = next  # pointer to the next snake node, going from head to tail


class Snake:
    def __init__(self, grid_width, grid_height, tile_size, lcd):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.tile_size = tile_size
        self.lcd = lcd

        center_of_grid = Position(x=self.grid_width//2, y=self.grid_height//2)
        self.direction = Direction(xdir=0, ydir=0)
        self.head = SnakeNode(position=center_of_grid, direction=self.direction)

    def push(self, new_head):
        """Append a new head at the front of the snake"""
        new_head.next, self.head = self.head, new_head

    def pop(self):
        current_node = self.head
        previous_node = None

        # loop through entire list of SnakeNodes
        while current_node.next != None:
            previous_node = current_node
            current_node = current_node.next

        # loop ends: final node in current_node, penultimate node in previous_node
        # if there is a previous_node (i.e. this is not the head node)
        if previous_node != None:
            previous_node.next = None # clear pointer to final node
            del current_node  # maybe this works as a hint to the garbage collector?

    def contains(self, position: Position):
        current_node = self.head

        while current_node != None:
            if current_node.pos == position:
                return True

            current_node = current_node.next

        return False

    def move(self):
        # unpack direction and position of head node
        x_dir, y_dir = self.direction
        head_x, head_y = self.head.pos

        # update position according to direction
        head_x += x_dir
        head_y += y_dir

        # keep position within grid boundaries
        head_x %= self.grid_width
        head_y %= self.grid_height

        # create and return new head node
        new_head_position = Position(x=head_x, y=head_y)
        new_node = SnakeNode(new_head_position, self.direction)

        return new_node

    def show(self):
        current_node = self.head

        while current_node != None:
            if current_node != self.head:

                x1, y1 = current_node.pos
                x2, y2 = previous_node.pos

                invisible = (abs(x1-x2)>1) or (abs(y1-y2)>1)

                if not invisible:
                    x1 *= self.tile_size
                    y1 *= self.tile_size

                    x2 *= self.tile_size
                    y2 *= self.tile_size

                    x1 += self.tile_size//2
                    y1 += self.tile_size//2

                    x2 += self.tile_size//2
                    y2 += self.tile_size//2

                    self.line(x1, y1, x2, y2)

            else:
                # draw circle for snake head
                grid_x, grid_y = current_node.pos
                canvas_x = (self.tile_size * grid_x)
                canvas_y = (self.tile_size * grid_y)
                center_x = canvas_x+(self.tile_size//2)
                center_y = canvas_y+(self.tile_size//2)
                radius = (self.tile_size-4)//2

                self.lcd.ellipse(center_x, center_y, radius, radius, snake_color, True)

            previous_node = current_node
            current_node = current_node.next

    def moving(self):
        return self.direction != (0, 0)

    def update_direction(self, key_pressed):
        x_dir, y_dir = self.direction

        if key_pressed == KEY_LEFT:
            if self.direction.xdir == 0:
                x_dir = -1
            y_dir = 0
        elif key_pressed == KEY_RIGHT:
            if self.direction.xdir == 0:
                x_dir = 1
            y_dir = 0
        elif key_pressed == KEY_DOWN:
            x_dir = 0
            if self.direction.ydir == 0:
                y_dir = 1
        elif key_pressed == KEY_UP:
            x_dir = 0
            if self.direction.ydir == 0:
                y_dir = -1

        self.direction = Direction(xdir=x_dir, ydir=y_dir)

    def line(self, x1, y1, x2, y2):
        start_x = min(x1, x2)
        start_y = min(y1, y2)

        line_thickness = 4
        offset = line_thickness//2

        start_x -= offset
        start_y -= offset

        # for horizontal lines
        if x1 == x2:
            line_width = offset * 2
            line_height = offset + abs(y1-y2) + offset

        # for vertical lines
        elif y1 == y2:
            line_width = offset + abs(x1-x2) + offset
            line_height = offset * 2

        self.lcd.rect(start_x, start_y, line_width, line_height, snake_color, True)

    def gamestate_string(self):
        current_node = self.head
        string_parts = []
        while current_node != None:
            string_parts.append(f"{current_node.pos.x},{current_node.pos.y}")
            current_node = current_node.next
        return ";".join(string_parts)


class Food:
    def __init__(self, snake, grid_width, grid_height, tile_size, lcd):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.tile_size = tile_size
        self.lcd = lcd
        self.reset_position(snake)

    def reset_position(self, snake):
        """sets new position for Food"""
        new_pos = Position(
            x=randint(0, self.grid_width-1), 
            y=randint(0, self.grid_height-1),
        )

        # re-calculate if random position inside snake
        while snake.contains(new_pos):
            new_pos = Position(
                x=randint(0, self.grid_width-1), 
                y=randint(0, self.grid_height-1),
            )

        self.pos = new_pos

    def show(self):
        # calculate center of tile on canvas
        tile_x = (self.tile_size * self.pos.x) + self.tile_size//2
        tile_y = (self.tile_size * self.pos.y) + self.tile_size//2
        radius = (self.tile_size-2)//2
        self.lcd.ellipse(tile_x, tile_y, radius, radius, food_color, True)



class Game:
    def __init__(self, grid_width, grid_height, tile_size, lcd, pubsubber):
        """
        Holds game state and manages all the game mechanics, drawing and 
        publishing of scores.

        :param grid_width:

        :param grid_height:

        :param tile_size:

        :param lcd: Instance of the LCD_1inch14-flavored framebuf provides by
            the LCD screen manufacturer.

        :param pubsubber: Instance of SnakePubsubber which holds scores of the
            other players and has a report_score() method for sending our 
            score to them.
        """
        self.lcd = lcd
        self.pubsubber = pubsubber

        self.grid_width = grid_width 
        self.grid_height = grid_height
        self.tile_size = tile_size

        self.lcd.registerKeyUpCallback(self.keyUpPressed)
        self.lcd.registerKeyDownCallback(self.keyDownPressed)
        self.lcd.registerKeyLeftCallback(self.keyLeftPressed)
        self.lcd.registerKeyRightCallback(self.keyRightPressed)

        self.key_press_to_process = KEY_NONE
        self.frameCount = 0
        self.score = 0
        self.previous_score = 0  # needed to display score after crash and before reset
        self.target_score = 5
        self.base_refresh = 0.01
        self.slow, self.fast = 12, 2
        self.countdown = 20
        self.cooldown = self.countdown

        self.state = GAMESTATE_READY_TO_START
        self.init_level()

    # initialize current level
    def init_level(self):
        self.snake = Snake(
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            tile_size=self.tile_size,
            lcd=self.lcd,
        )
        self.food = Food(
            snake=self.snake, 
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            tile_size=self.tile_size,
            lcd=self.lcd,
        )
        self.key_press_to_process = KEY_NONE
        self.set_score(0)
        self.report_gamestate()
        gc.collect()

    def set_score(self, new_score):
        self.score = new_score
        self.pubsubber.report_score(new_score)

    def report_gamestate(self):
        snake_state_str = self.snake.gamestate_string()
        self.pubsubber.report_gamestate(
            f"{self.food.pos.x},{self.food.pos.y};{snake_state_str}"
        )

    async def tick(self):
        self.frame_skip = int(self.map_to_range(self.score, 0, 50, self.slow, self.fast))

        if self.frameCount % self.frame_skip == 0:
            self.draw_background()
            self.draw_game_stats()

            if self.state == GAMESTATE_READY_TO_START:
                self.draw_game_objects()
                self.show_how_to_start_hint()
                if self.key_press_to_process != KEY_NONE:
                    self.state = GAMESTATE_PLAYING

            elif self.state == GAMESTATE_PLAYING:
                self.draw_game_objects()
                    
                if self.key_press_to_process != KEY_NONE:
                    self.snake.update_direction(self.key_press_to_process)
                    self.key_press_to_process = KEY_NONE

                new_head = self.snake.move()

                # snake hit food
                if new_head.pos == self.food.pos:
                    self.set_score(self.score + 1)
                    self.snake.push(new_head)
                    self.food.reset_position(self.snake)
                # snake hit wall or itself
                elif self.snake.moving() and self.snake.contains(new_head.pos):
                    self.previous_score = self.score
                    self.set_score(0)
                    self.cooldown = self.countdown
                    self.state = GAMESTATE_SHOW_SCORE
                # snake moving regularly
                else:
                    self.snake.push(new_head)
                    self.snake.pop()
                    self.report_gamestate()

            elif self.state == GAMESTATE_SHOW_SCORE:
                self.cooldown -= 1
                self.show_game_text()

                if self.cooldown < 0:
                    self.cooldown = self.countdown
                    self.init_level()
                    self.state = GAMESTATE_READY_TO_START

            self.lcd.show()

        self.frameCount += 1
        gc.collect()
        await asyncio.sleep(self.base_refresh)

    # the key*Pressed functions are registered as interrupt handlers
    def keyUpPressed(self):
        self.key_press_to_process = KEY_UP

    def keyDownPressed(self):
        self.key_press_to_process = KEY_DOWN

    def keyLeftPressed(self):
        self.key_press_to_process = KEY_LEFT

    def keyRightPressed(self):
        self.key_press_to_process = KEY_RIGHT

    def draw_background(self):
        self.lcd.fill(background_color)

    def draw_game_objects(self):
        self.food.show()
        self.snake.show()

    def draw_game_stats(self):
        y_pos = 125
        box_y = y_pos - 2
        box_width = self.lcd.width
        box_height = self.lcd.height - box_y
        players = [
            ("A", 0xf800), 
            ("B", 0xf800), 
            ("C", 0xf800), 
            ("D", 0x07E0), 
            ("E", 0x07E0), 
            ("F", 0x07E0),
        ]

        # background colors
        self.lcd.rect(0, box_y, box_width, box_height, game_stats_bg_color, True)

        for i, (player, color) in enumerate(players):
            x_pos = 4 + i * 39
            # dividing lines
            if i>0:
                bar_color = 0x0000 if i == 3 else color
                self.lcd.rect(x_pos - 3, box_y, 1, box_height, bar_color, True)
            # self highlight
            if player == self.pubsubber.player_name_self:
                self.lcd.rect(x_pos - 1, box_y + 1, 36, box_height - 2, 0x07FF, True)
            # text
            score = self.pubsubber.scores[player]
            self.lcd.text(':', x_pos + 8, y_pos, color)
            self.lcd.text(player, x_pos + 3, y_pos, color)
            self.lcd.text(f"{score:2}", x_pos + 16, y_pos, color)

        # self.lcd.text("Score", 90, y_pos, title_color)
        # self.lcd.text(str(self.score), 146, y_pos, title_color)

    def show_title_screen(self):
        self.lcd.text("PiCo", 100, 50, title_color)
        self.lcd.text("Snake", 100, 62, title_color)

    def show_game_text(self):
        if self.state == GAMESTATE_SHOW_SCORE:
            self.draw_game_objects()
            self.lcd.text("SCORE", 90, 60, score_color)
            self.lcd.text(str(self.previous_score), 150, 60, score_color)

    def show_how_to_start_hint(self):
        self.lcd.text("<-- Use joystick", 18, 30, 0xFFFF)
        self.lcd.text("to start game", 60, 40, 0xFFFF)

    def map_to_range(self, val, min_1, max_1, min_2, max_2):
        """simple range mapping method"""
        if val <= min_1:
            return min_2
        elif val >= max_1:
            return max_2
        else:
            diff_1 = max_1 - min_1
            ratio_1 = (val-min_1)/diff_1

            diff_2 = max_2 - min_2
            ratio_2 = (ratio_1*diff_2) + min_2

            return ratio_2