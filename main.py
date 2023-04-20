import uasyncio as asyncio
import gc
from sys import version as sys_version
# import json

from lcd1in14 import LCD_1inch14
from mqtt_as import MQTTClient, config
from secrets import WLAN_SSID, WLAN_PASSWORD
from snake import Game
from splashscreen import splashscreen

# initialize the LCD screen
LCD = LCD_1inch14()

TOPIC_PREFIX = "pico-snake-mqtt"

# Who am I!? Saving ourselves an import by getting the default
# client ID from mqtt_as which happens to be hexlify(unique_id())
SNAKERPICOS = {
    b'e6614864d357a437': "A",
    # b'e6614864d3228237': "B",  # (defective Pi)
    b'e6616408432e7b2e': "B",
    b'e6614103e766c524': "C",
    b'e6616407e351682c': "D",
    b'e6616407e3749931': "E",
    b'e6616407e3405f2c': "F",
}

PLAYER2TEAM = {
    "A": "blue",
    "B": "blue",
    "C": "blue",
    "D": "red",
    "E": "red",
    "F": "red",
}

class SnakePubsubber:
    def __init__(self, mqtt_client, topic_prefix, player_name_self):
        self.mqtt_client = mqtt_client
        self.topic_prefix = topic_prefix
        self.player_name_self = player_name_self

        self.scores = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "E": 0,
            "F": 0,
        }

    async def subber(self):
        if not self.mqtt_client.isconnected():
            return
        
        await self.mqtt_client.subscribe(topic=f"{self.topic_prefix}/+/score")

        async for topic, msg, _ in self.mqtt_client.queue:
            topic_parts = topic.decode().split("/")
            if (
                len(topic_parts) == 3
                and topic_parts[0] == self.topic_prefix
                and topic_parts[1] != self.player_name_self
                and topic_parts[2] == "score"
            ):
                try:
                    # msg_parsed = json.loads(msg.decode())
                    score = int(msg.decode())
                except Exception as ex:
                    print(f"Failed to decode arriving message: {msg}")
                    continue
                self.scores[topic_parts[1]] = score

    async def publish_score_task(self, score):
        # drop messages while offline instead of enqueueing them and 
        # gobbling up memory with it
        if not self.mqtt_client.isconnected():
            return
        
        await self.mqtt_client.publish(
            topic=f"{self.topic_prefix}/{self.player_name_self}/score", 
            msg=f"{score}", 
            retain=True,
            qos=0,
        )

    async def publish_gamestate_task(self, payload):
        # drop messages while offline instead of enqueueing them and 
        # gobbling up memory with it
        if not self.mqtt_client.isconnected():
            return
        
        await self.mqtt_client.publish(
            topic=f"{self.topic_prefix}/{self.player_name_self}/game", 
            msg=payload, 
            retain=True,
            qos=0,
        )

    def report_score(self, score):
        self.scores[self.player_name_self] = score
        asyncio.create_task(self.publish_score_task(score))

    def report_gamestate(self, state_str):
        asyncio.create_task(self.publish_gamestate_task(state_str))


async def snake(pubsubber):
    """run game loop"""
    # grid size 20 x 11 tiles with tile_size=12 => 240*132 px
    game = Game(grid_width=20, grid_height=10, tile_size=12, lcd=LCD, pubsubber=pubsubber)
    while True:
        await game.tick()


async def main():
    print(f"MicroPython version: {sys_version}")
    hex_uniq_id = config["client_id"]
    print(f"Unique ID: {hex_uniq_id}")
    player_name = SNAKERPICOS.get(hex_uniq_id, hex_uniq_id[-4:])
    print(f"Player Name: {player_name}")
    player_team = PLAYER2TEAM.get(player_name, "orange")

    if player_team == "red":
        splashscreen_letters_color = 0x27e1
    elif player_team == "blue":
        splashscreen_letters_color = 0xf712
    else:
        splashscreen_letters_color = 0x2417

    splashscreen(lcd=LCD, letter_color=splashscreen_letters_color)
    splashscreen_text_offset_x = 12

    LCD.text(f"Player {player_name}", splashscreen_text_offset_x, 90, 0xFFFF)
    LCD.text(f"Team {player_team.upper()}", splashscreen_text_offset_x, 102, 0xFFFF)
    LCD.text(f"Connecting...", splashscreen_text_offset_x, 114, 0xFFFF)
    LCD.show()

    config.update({
        "ssid": WLAN_SSID,
        "wifi_pw": WLAN_PASSWORD,
        "server": '192.168.3.1',
        "will": (
            f"{TOPIC_PREFIX}/{player_name}/score",  # topic
            "0",  # value 
            True,  # retain 
            0,  # qos
        ),
        "keepalive": 5,
        "queue_len": 1,  # Use event interface with default queue
    })

    mqtt_client = MQTTClient(config)
    try:
        await mqtt_client.connect()
        LCD.text(f"Connecting...", splashscreen_text_offset_x, 114, 0x0000) # erasing previous text
        LCD.text(f"MQTT connected", splashscreen_text_offset_x, 114, 0xFFFF)
        LCD.show()
    except OSError:
        print('MQTT connection failed.')
        LCD.text(f"Connecting...", splashscreen_text_offset_x, 114, 0x0000) # erasing previous text
        LCD.text("No MQTT conn :-(", splashscreen_text_offset_x, 114, 0xFFFF)
        LCD.show()

    try:
        ip = mqtt_client._sta_if.ifconfig()[0]
        print(f"IP: {ip}")
        LCD.text(f"{ip}", splashscreen_text_offset_x, 126, 0xFFFF)
        LCD.show()
    except Exception as ex:
        print(f"Could not determine IP: {ex}")
        LCD.text(f"No IP Addr :-(", splashscreen_text_offset_x, 126, 0xFFFF)
        LCD.show()

    pubsubber = SnakePubsubber(
        mqtt_client=mqtt_client, 
        topic_prefix=TOPIC_PREFIX, 
        player_name_self=player_name,
    )

    gc.collect()

    # countdown timer
    LCD.text("3", 190, 50, 0xFFFF)
    LCD.show()
    await asyncio.sleep(1)
    LCD.text("3", 190, 50, 0x0000)
    LCD.text("2", 190, 50, 0xFFFF)
    LCD.show()
    await asyncio.sleep(1)
    LCD.text("2", 190, 50, 0x0000)
    LCD.text("1", 190, 50, 0xFFFF)
    LCD.show()
    await asyncio.sleep(1)

    tasks = [
        asyncio.create_task(snake(pubsubber)),
        asyncio.create_task(pubsubber.subber()),
    ]
    await asyncio.gather(*tasks)

asyncio.run(main())