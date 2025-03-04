import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from tortoise.exceptions import DoesNotExist

from carfigures.core.models import GuildConfig
from carfigures.packages.carfigures.spawn import SpawnManager

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.carfigures")


class CarFiguresSpawner(commands.Cog):
    def __init__(self, bot: "CarFiguresBot"):
        self.spawn_manager = SpawnManager()
        self.bot = bot

    async def load_cache(self):
        amount = 0
        async for config in GuildConfig.all():
            if not config.enabled:
                continue
            if not config.spawnChannel:
                continue
            self.spawn_manager.cache[config.guild_id] = config.spawnChannel
            amount += 1
        log.info(f"Loaded {amount} guilds in cache")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        if guild.id not in self.spawn_manager.cache:
            return
        if guild.id in self.bot.blacklisted_servers:
            return
        await self.spawn_manager.handle_message(message)

    @commands.Cog.listener()
    async def on_carfigures_settings_change(
        self,
        guild: discord.Guild,
        channel: Optional[discord.TextChannel] = None,
        enabled: Optional[bool] = None,
    ):
        if guild.id not in self.spawn_manager.cache:
            if enabled is False:
                return  # do nothing
            if channel:
                self.spawn_manager.cache[guild.id] = channel.id
            else:
                try:
                    config = await GuildConfig.get(guild_id=guild.id)
                except DoesNotExist:
                    return
                else:
                    self.spawn_manager.cache[guild.id] = config.spawnChannel
        else:
            if enabled is False:
                del self.spawn_manager.cache[guild.id]
            elif channel:
                self.spawn_manager.cache[guild.id] = channel.id
