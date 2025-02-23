import logging
import sys
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from carfigures import botVersion
from carfigures.core.models import cars as carfigures
from carfigures.core.utils.transformers import EventEnabledTransform
from carfigures.packages.info.components import mention_app_command, row_count_estimate
from carfigures.settings import appearance, information, settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.info")


class Info(commands.GroupCog):
    """
    Simple info commands.
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

        cars_count = len([car for car in carfigures.values() if car.enabled])
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
            value=f"\u200b **⋄ {appearance.collectible_plural.title()}s Count: ** {cars_count:,} • "
            f"{cars_instances_count:,} **Caught**\n"
            f"\u200b **⋄ Player Count: ** {players_count:,}\n"
            f"\u200b **⋄ Server Count: ** {len(self.bot.guilds):,}\n"
            f"\u200b **⋄  Operating Version: [{botVersion}]({information.repository_link})**\n\n",
            inline=False,
        )
        # ⋋
        embed.add_field(name="⋈ Developers", value=developers, inline=True)
        embed.add_field(name="⋊ Contributors", value=first_contributors, inline=True)
        if remaining_contributors:
            embed.add_field(name="\u200b", value=remaining_contributors, inline=True)

        embed.add_field(
            name="⋇ Links",
            value=f"[Discord server]({information.server_invite}) • [Invite me]({invite_link}) • "
            f"[Source code and issues]({information.repository_link})\n"
            f"[Terms of Service]({information.terms_of_service}) • "
            f"[Privacy policy]({information.privacy_policy}) • ",
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        v = sys.version_info
        embed.set_footer(
            text=f"Python {v.major}.{v.minor}.{v.micro} • discord.py {discord.__version__}"
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def commands(self, interaction: discord.Interaction):
        """
        Show information about the commands inside this bot.
        """

        assert self.bot.users
        category_to_commands = {}  # Dictionary to store commands by category

        # Group commands by cog (category)
        for cog in self.bot.cogs.values():
            for app_command in cog.walk_app_commands():
                # Use cog name as category (unchangeable by users)
                category = cog.qualified_name
                if category == "SuperUser" or category == "Info":
                    continue
                if category == "Cars":
                    category = appearance.cars.title()
                category_to_commands.setdefault(category, []).append(app_command)

        # Create dropdown options for categories
        options = [
            discord.SelectOption(
                label=category,
                description=f"View commands for {category}",
                value=category,
            )
            for category in category_to_commands
        ]

        select = discord.ui.Select(
            placeholder="Choose a category...",
            min_values=1,
            max_values=1,
            options=options,
        )

        embed = discord.Embed(
            title="Select a category",
            description="Choose a category to see its commands.",
            color=settings.default_embed_color,
        )
        view = discord.ui.View()

        async def callback(interaction: discord.Interaction):
            selected_category = select.values[0]
            commands_in_category = category_to_commands[selected_category]
            commands_list = "\n".join(
                [f"⋄ {mention_app_command(cmd)}: {cmd.description}" for cmd in commands_in_category]
            )

            embed = discord.Embed(
                title=f"{settings.bot_name} Commands | {selected_category}",
                description=commands_list or "No commands available.",
                color=settings.default_embed_color,
            )
            await interaction.response.edit_message(embed=embed, view=view)

        # Create an embed explaining the purpose of the dropdown
        embed = discord.Embed(
            title=f"{settings.bot_name} Commands",
            description="Select a category from the dropdown to view its commands.",
            color=settings.default_embed_color,
        )
        select.callback = callback  # type: ignore
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view)

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
        content, file = await event.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()
