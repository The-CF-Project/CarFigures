import logging
import sys

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from carfigures import bot_version
from carfigures.settings import settings, commandings, information, appearance
from carfigures.core.models import Library, TopicType, cars
from carfigures.core.utils.transformers import EventTransform
from carfigures.core.utils.paginator import FieldPageSource, Pages
from carfigures.core.utils.tortoise import row_count_estimate
from carfigures.packages.info.components import (
    machine_info,
    mention_app_command,
    LibrarySelector,
)


if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.info")


class Info(commands.GroupCog, group_name=commandings.info_group):
    """
    info commands.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command()
    async def status(self, interaction: discord.Interaction):
        """
        Show information about this bot.
        """
        embed = discord.Embed(
            title=f"❑ {settings.bot_name} Bot Status",
            color=settings.default_embed_color,
        )

        cars_count = len([x for x in cars.values() if x.enabled])
        players_count = await row_count_estimate("player")
        cars_instances_count = await row_count_estimate("carinstance")
        developers = "\n".join(
            [f"\u200b **⋄** {developer}" for developer in information.developers]
        )
        first_contributors = "\n".join(
            [
                f"\u200b **⋄** {contributor}"
                for contributor in information.contributors[:4]
            ]
        )
        remaining_contributors = "\n".join(
            [
                f"\u200b **⋄** {contributor}"
                for contributor in information.contributors[4:]
            ]
        )
        (
            cpu_usage,
            memory_usage,
            memory_total,
            memory_percentage,
            disk_usage,
            disk_total,
            disk_percentage,
        ) = machine_info()

        assert self.bot.user
        assert self.bot.application
        if self.bot.application.install_params is None:
            invite_link = discord.utils.oauth_url(
                self.bot.application.id,
                permissions=discord.Permissions(
                    manage_webhooks=True,
                    manage_expressions=True,
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    use_external_emojis=True,
                ),
                scopes=("bot", "applications.commands"),
            )
        else:
            invite_link = discord.utils.oauth_url(
                self.bot.application.id,
                permissions=self.bot.application.install_params.permissions,
                scopes=self.bot.application.install_params.scopes,
            )

        embed.add_field(
            name="∆ Bot Info\n",
            value=f"\u200b **⋄ {appearance.collectible_plural.title()}s Count: ** {cars_count:,} • {cars_instances_count:,} **Caught**\n"
            f"\u200b **⋄ Player Count: ** {players_count:,}\n"
            f"\u200b **⋄ Server Count: ** {len(self.bot.guilds):,}\n"
            f"\u200b **⋄  Operating Version: [{bot_version}]({information.repository_link})**\n\n",
            inline=False,
        )
        embed.add_field(
            name="∇ Machine Info\n",
            value=f"\u200b **⋄ CPU:** {cpu_usage}%\n"
            f"\u200b **⋄ Memory:** {memory_usage}/{memory_total}MB • {memory_percentage}%\n"
            f"\u200b **⋄ Disk:** {disk_usage}/{disk_total}GB • {disk_percentage}%\n\n",
            inline=False,
        )
        embed.add_field(name="⋈ Developers", value=developers, inline=True)
        embed.add_field(name="⋊ Contributors", value=first_contributors, inline=True)
        if remaining_contributors:
            embed.add_field(name="\u200b", value=remaining_contributors, inline=True)

        embed.add_field(
            name="⋇ Links",
            value=f"[Discord server]({information.discord_invite}) • [Invite me]({invite_link}) • "
            f"[Source code and issues]({information.repository_link})\n"
            f"[Terms of Service]({information.terms_of_service}) • "
            f"[Privacy policy]({information.privacy_policy}) • "
            f"[Top.gg Link]({information.top_gg})",
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        v = sys.version_info
        embed.set_footer(
            text=f"Python {v.major}.{v.minor}.{v.micro} • discord.py {discord.__version__}"
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def commands(self, interaction: discord.Interaction["CarFiguresBot"]):
        """
        Show information about the commands inside this bot, categorized by page.
        """

        assert self.bot.users
        groups_and_commands = {}  # Dictionary to store commands by category

        # Group commands by cog (category)
        for cog in self.bot.cogs.values():
            for app_command in cog.walk_app_commands():
                # Use cog name as category (unchangeable by users)
                group = cog.qualified_name
                groups_and_commands.setdefault(group, []).append(app_command)

        # Create the paginated source directly using categories dictionary
        entries = []
        for group_name, group_commands in groups_and_commands.items():
            sorted_commands = sorted(
                group_commands, key=lambda command: command.name
            )  # Sort commands alphabetically
            command_descriptions = {
                command.name: command.description for command in sorted_commands
            }  # Create temporary dictionary
            command_list = ""
            for command in sorted_commands:
                # Combine formatted command names with newlines
                command_list = "\n".join(
                    [
                        f"\u200b ⋄ {mention_app_command(command)}: {command_descriptions[command.name]}"
                    ]
                )

            # Create an entry tuple (category name as title, list of commands)
            entry = (f"**Group: {group_name}**", f"{command_list}")
            entries.append(entry)

        source = FieldPageSource(entries=entries, per_page=2)
        source.embed.title = f"{settings.bot_name} Commands list"
        source.embed.colour = settings.default_embed_color
        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command()
    @app_commands.choices(
        docstype=[
            app_commands.Choice(name="Player Documentation", value=TopicType.PLAYER),
            app_commands.Choice(
                name="Developer Documentation", value=TopicType.DEVERLOPER
            ),
        ]
    )
    async def library(self, interaction: discord.Interaction, docstype: TopicType):
        """
        CarFigure's Official Documentation

        Parameters
        ----------
        docstype: TopicType
            The Type of Documentation
        """
        # Filter the Library entries based on the selected docstype
        topics = await Library.filter(type=docstype)

        if not topics:
            await interaction.response.send_message(
                "No topics available for this type."
            )
            return

        embed = discord.Embed(
            title="Select a Topic",
            description="Please select a topic from the dropdown menu below.",
            color=settings.default_embed_color,
        )
        view = LibrarySelector(topics)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command()
    async def credits(self, interaction: discord.Interaction):
        """
        The bot credits
        """
        embed = discord.Embed(
            title=f"{settings.bot_name} Credits", color=settings.default_embed_color
        )
        developers = "\n".join(
            [f"\u200b **⋄** {developer}" for developer in information.developers]
        )
        first_contributors = "\n".join(
            [
                f"\u200b **⋄** {contributor}"
                for contributor in information.contributors[:4]
            ]
        )
        remaining_contributors = "\n".join(
            [
                f"\u200b **⋄** {contributor}"
                for contributor in information.contributors[4:]
            ]
        )

        embed.add_field(name="⋈ Developers", value=developers, inline=True)
        embed.add_field(name="∀ Artists", value="Seggs", inline=True)
        embed.add_field(name="⋊ Contributors", value=first_contributors, inline=False)
        if remaining_contributors:
            embed.add_field(name="\u200b", value=remaining_contributors, inline=True)

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def events(self, interaction: discord.Interaction, event: EventTransform):
        """
        List the events inside the bot

        Parameters
        ----------
        event: Event
            The event u want to check info about!
        """
        await interaction.response.defer(thinking=True)
        content, file = await event.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()
