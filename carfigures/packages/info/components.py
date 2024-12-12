import random

import discord
from discord import app_commands
from carfigures.core.models import Car, cars as carfigures


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
    cars: list[Car] = random.choices([x for x in carfigures.values() if x.enabled], k=min(10, len(carfigures)))
    emotes: list[discord.Emoji] = []
    for car in cars:
        if emoji := self.bot.get_emoji(car.emoji):
            emotes.append(emoji)
    return emotes
