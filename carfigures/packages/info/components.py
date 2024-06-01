import psutil
import random

import discord
from discord import app_commands
from carfigures.core.models import Car, cars as carfigures


def machine_info() -> str:
    """
    Function to gather information about the machine's CPU, memory, and disk usage.
    """
    cpu_usage = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    memory_usage = round(memory.used / (1024 ** 2), 2)
    memory_total = round(memory.total / (1024 ** 2), 2)
    memory_percentage = memory.percent
    disk = psutil.disk_usage("/")
    disk_usage = round(disk.used / (1024 ** 3), 2)
    disk_total = round(disk.total / (1024 ** 3), 2)
    disk_percentage = disk.percent
    return cpu_usage, memory_usage, memory_total, memory_percentage, disk_usage, disk_total, disk_percentage


def mention_app_command(app_command: app_commands.Command | app_commands.Group) -> str:
    """
    Generate a mention for the provided app command.
    """
    if "mention" in app_command.extras:
        return app_command.extras["mention"]
    else:
        if isinstance(app_command, app_commands.ContextMenu):
            return f"`{app_command.name}`"
        else:
            return f"`/{app_command.name}`"
        

async def _get_10_cars_emojis(self) -> list[discord.Emoji]:
    """
    Return a list of up to 10 Discord emojis representing cars.
    """
    cars: list[Car] = random.choices(
        [x for x in carfigures.values() if x.enabled], k=min(10, len(carfigures))
    )
    emotes: list[discord.Emoji] = []
    for car in cars:
        if emoji := self.bot.get_emoji(car.emoji_id):
            emotes.append(emoji)
    return emotes
