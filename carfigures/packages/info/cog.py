import logging
import sys

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from carfigures.core.models import cars as carfigures
from carfigures.core.utils.transformers import EventEnabledTransform
from carfigures.core.utils.paginator import FieldPageSource, Pages
from carfigures.core.utils.tortoise import row_count_estimate

from carfigures.settings import settings, information, appearance

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.info")


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


class Info(commands.GroupCog):
    """
    Simple info commands.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        """
        Show the bot latency.
        """
        await interaction.response.send_message(
            f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True
        )

    @app_commands.command()
    async def status(self, interaction: discord.Interaction):
        """
        Show information about this bot.
        """
        embed = discord.Embed(
            title=f"❑ {settings.botName} Bot Status",
            color=settings.defaultEmbedColor,
        )

        cars_count = len([x for x in carfigures.values() if x.enabled])
        players_count = await row_count_estimate("player")
        cars_instances_count = await row_count_estimate("carinstance")
        developers = "\n".join([f"\u200b **⋄** {dev}" for dev in information.developers])
        first_contributors = "\n".join(
            [f"\u200b **⋄** {contrib}" for contrib in information.contributors[:4]]
        )

        remaining_contributors = "\n".join(
            [f"\u200b **⋄** {contrib}" for contrib in information.contributors[4:]]
        )

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
            value=f"\u200b **⋄ {appearance.collectiblePlural.title()}s Count: ** {cars_count:,} • "
            f"{cars_instances_count:,} **Caught**\n"
            f"\u200b **⋄ Player Count: ** {players_count:,}\n"
            f"\u200b **⋄ Server Count: ** {len(self.bot.guilds):,}\n"
            f"\u200b **⋄  Operating Version: [v2.1.4]({information.repositoryLink})**\n\n",
            inline=False,
        )
        # ⋋
        embed.add_field(name="⋈ Developers", value=developers, inline=True)
        embed.add_field(name="⋊ Contributors", value=first_contributors, inline=True)
        if remaining_contributors:
            embed.add_field(name="\u200b", value=remaining_contributors, inline=True)

        embed.add_field(
            name="⋇ Links",
            value=f"[Discord server]({information.serverInvite}) • [Invite me]({invite_link}) • "
            f"[Source code and issues]({information.repositoryLink})\n"
            f"[Terms of Service]({information.termsOfService}) • "
            f"[Privacy policy]({information.privacyPolicy}) • ",
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        v = sys.version_info
        embed.set_footer(
            text=f"Python {v.major}.{v.minor}.{v.micro} • discord.py {discord.__version__}"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    async def commands(self, interaction: discord.Interaction):
        """
        Show information about the commands inside this bot, categorized by page.
        """

        assert self.bot.users
        categoryToCommands = {}  # Dictionary to store commands by category

        # Group commands by cog (category)
        for cog in self.bot.cogs.values():
            for appCommand in cog.walk_app_commands():
                # Use cog name as category (unchangeable by users)
                category = cog.qualified_name
                if category == "SuperUser":
                    continue
                categoryToCommands.setdefault(category, []).append(appCommand)

        # Create the paginated source directly using categories dictionary
        entries = []
        for categoryName, cogCommands in categoryToCommands.items():
            sortedCommands = sorted(
                cogCommands, key=lambda c: c.name
            )  # Sort commands alphabetically
            commandDescriptions = {
                c.name: c.description for c in sortedCommands
            }  # Create temporary dictionary

            # Combine formatted command names with newlines
            commandList = "\n".join(
                [
                    f"\u200b ⋄ {mention_app_command(c)}: {commandDescriptions[c.name]}"
                    for c in sortedCommands
                ]
            )

            # Create an entry tuple (category name as title, list of commands)
            entry = (f"**Category: {categoryName}**", f"{commandList}")
            entries.append(entry)

        source = FieldPageSource(entries=entries, per_page=2)  # Adjust per_page as needed
        source.embed.title = f"{settings.botName} Commands list"
        source.embed.colour = settings.defaultEmbedColor
        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start(ephemeral=True)

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def events(self, interaction: discord.Interaction, event: EventEnabledTransform):
        """
        List the events inside the bot

        Parameters
        ----------
        event: Event
            The event u want to check info about!
        """
        await interaction.response.defer(thinking=True)
        content, file = await event.prepareForMessage(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()
