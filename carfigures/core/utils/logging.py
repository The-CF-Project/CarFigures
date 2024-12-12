import logging

import discord

from carfigures.core.bot import CarFiguresBot
from carfigures.settings import settings

log = logging.getLogger("carfigures.packages.admin.cog")


async def log_action(message: str, bot: CarFiguresBot, console_log: bool = False):
    if settings.logChannel:
        channel = bot.get_channel(settings.logChannel)
        if not channel:
            log.warning(f"Channel {settings.logChannel} not found")
            return
        if not isinstance(channel, discord.TextChannel):
            log.warning(f"Channel {channel.name} is not a text channel")  # type: ignore
            return
        await channel.send(message)
    if console_log:
        log.info(message)
