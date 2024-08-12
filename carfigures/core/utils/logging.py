import logging

import discord

from carfigures.core.bot import CarFiguresBot
from carfigures.settings import superuser

log = logging.getLogger("carfigures.packages.admin.cog")


async def log_action(message: str, bot: CarFiguresBot, console_log: bool = False):
    if superuser.log_channel:
        channel = bot.get_channel(superuser.log_channel)
        if not channel:
            log.warning(f"Channel {superuser.log_channel} not found")
            return
        if not isinstance(channel, discord.TextChannel):
            log.warning(f"Channel {channel.name} is not a text channel")  # type: ignore
            return
        await channel.send(message)
    if console_log:
        log.info(message)
