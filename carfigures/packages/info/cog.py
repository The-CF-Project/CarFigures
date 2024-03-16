import logging
import random
import sys
import psutil
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from carfigures import __version__ as bot_version
from carfigures.core.models import Car
from carfigures.core.models import cars as carfigures
from carfigures.core.utils.tortoise import row_count_estimate
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.info")

def machine_info() -> str:
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
    if "mention" in app_command.extras:
        return app_command.extras["mention"]
    else:
        if isinstance(app_command, app_commands.ContextMenu):
            return f"`{app_command.name}`"
        else:
            return f"`/{app_command.name}`"


class Info(commands.GroupCog):
    """
    Simple info commands.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    async def _get_10_cars_emojis(self) -> list[discord.Emoji]:
        cars: list[Car] = random.choices(
            [x for x in carfigures.values() if x.enabled], k=min(10, len(carfigures))
        )
        emotes: list[discord.Emoji] = []

        for car in cars:
            if emoji := self.bot.get_emoji(car.emoji_id):
                emotes.append(emoji)

        return emotes

    @app_commands.command()
    async def status(self, interaction: discord.Interaction):
        """
        Show information about this bot.
        """
        embed = discord.Embed(
            title=f"{settings.bot_name} Bot Info:", color=discord.Colour.blurple()
        )

        try:
            cars = await self._get_10_cars_emojis()
        except Exception:
            log.error("Failed to fetch 10 cars emotes", exc_info=True)
            cars = []

        cars_count = len([x for x in carfigures.values() if x.enabled])
        players_count = await row_count_estimate("player")
        cars_instances_count = await row_count_estimate("carinstance")
        cpu_usage, memory_usage, memory_total, memory_percentage, disk_usage, disk_total, disk_percentage = machine_info()

        assert self.bot.user
        assert self.bot.application
        try:
            assert self.bot.application.install_params
        except AssertionError:
            invite_link = discord.utils.oauth_url(
                self.bot.application.id,
                permissions=discord.Permissions(
                    manage_webhooks=True,
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    attach_files=True,
                    use_external_emojis=True,
                    add_reactions=True,
                ),
                scopes=("bot", "applications.commands"),
            )
        else:
            invite_link = discord.utils.oauth_url(
                self.bot.application.id,
                permissions=self.bot.application.install_params.permissions,
                scopes=self.bot.application.install_params.scopes,
            )
        embed.description = (
            # f"{' '.join(str(x) for x in cars)}\n"
            # f"{settings.about_description}\n"
            f"**Bot Info:**\n"
            f"**Entity Count: ** {cars_count:,} • {cars_instances_count:,} **Caught**\n"
            f"**Player Count: ** {players_count:,}\n"
            f"**Server Count: ** {len(self.bot.guilds):,}\n"
            f"**Version: [{bot_version}]({settings.repository_link}/releases)**\n\n"
            f"**Machine Info:**\n"
            f"**CPU:** {cpu_usage}%\n"
            f"**Memory:** {memory_usage}/{memory_total}MB • {memory_percentage}%\n"
            f"**Disk:** {disk_usage}/{disk_total}GB • {disk_percentage}%\n\n"
            f"**Developers**\n"
            f"El Laggron • Array_YE\n\n"
            f"[Discord server]({settings.discord_invite}) • [Invite me]({invite_link}) • "
            f"[Source code and issues]({settings.repository_link})\n"
            f"[Terms of Service]({settings.terms_of_service}) • "
            f"[Privacy policy]({settings.privacy_policy}) • "
            f"[Top.gg Link]({settings.top_gg})"
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        v = sys.version_info
        embed.set_footer(
            text=f"Python {v.major}.{v.minor}.{v.micro} • discord.py {discord.__version__} • CarFigures Version 1.0"
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def commands(self, interaction: discord.Interaction):
        """
        Show information about the commands inside this bot.
        """
        assert self.bot.user
        embed = discord.Embed(
            title=f"{settings.bot_name} Discord bot - help menu", color=discord.Colour.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        for cog in self.bot.cogs.values():
            if cog.qualified_name == "Admin":
                continue
            content = ""
            for app_command in cog.walk_app_commands():
                content += f"{mention_app_command(app_command)}: {app_command.description}\n"
            if not content:
                continue
            embed.add_field(name=cog.qualified_name, value=content, inline=False)

        await interaction.response.send_message(embed=embed)
