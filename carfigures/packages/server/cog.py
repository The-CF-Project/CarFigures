from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands

from carfigures.core.models import GuildConfig
from carfigures.packages.server.components import AcceptTOSView, _get_10_cars_emojis
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

activation_embed = discord.Embed(
    colour=settings.default_embed_color,
    title=f"{settings.bot_name} activation",
    description=f"To enable {settings.bot_name} in your server, you must "
    f"read and accept the [Terms of Service]({settings.terms_of_service}).\n\n"
    "As a summary, these are the rules of the bot:\n"
    f"- No farming (spamming or creating servers for {settings.collectible_name})\n"
    "- Do not attempt to abuse the bot's internals\n"
    "**Not respecting these rules will lead to a blacklist**",
)


@app_commands.guild_only()
class Server(commands.GroupCog, group_name=settings.group_cog_names["server"]):
    """
    View and manage your carfigures collection.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command()
    async def channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        """
        Set or change the channel where carfigures will spawn.
        """
        guild = cast(discord.Guild, interaction.guild)  # guild-only command
        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this."
            )
            return
        if not channel.permissions_for(guild.me).read_messages:
            await interaction.response.send_message(
                f"I need the permission to read messages in {channel.mention}."
            )
            return
        if not channel.permissions_for(guild.me).send_messages:
            await interaction.response.send_message(
                f"I need the permission to send messages in {channel.mention}."
            )
            return
        if not channel.permissions_for(guild.me).embed_links:
            await interaction.response.send_message(
                f"I need the permission to send embed links in {channel.mention}."
            )
            return
        await interaction.response.send_message(
            embed=activation_embed, view=AcceptTOSView(interaction, channel)
        )

    @app_commands.command()
    async def disable(
        self,
        interaction: discord.Interaction
    ):
        """
        Disable or enable carfigures spawning.
        """
        guild = cast(discord.Guild, interaction.guild)  # guild-only command
        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this."
            )
            return
        config, created = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if config.enabled:
            config.enabled = False  # type: ignore
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=False)
            await interaction.response.send_message(
                f"{settings.bot_name} is now disabled in this server. Commands will still be "
                f"available, but the spawn of new {settings.collectible_name}s is suspended.\n"
                "To re-enable the spawn, use the same command."
            )
        else:
            config.enabled = True  # type: ignore
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=True)
            if config.spawn_channel and (channel := guild.get_channel(config.spawn_channel)):
                await interaction.response.send_message(
                    f"{settings.bot_name} is now enabled in this server, "
                    f"{settings.collectible_name}s will start spawning soon in {channel.mention}."
                )
            else:
                await interaction.response.send_message(
                    f"{settings.bot_name} is now enabled in this server, however there is no "
                    "spawning channel set. Please configure one with `/server channel`."
                )

    @app_commands.command()
    async def spawnalert(
            self,
            interaction: discord.Interaction,
            role: discord.Role
    ):
        """
        Enable, Disable or Set Role spawn alert for your server
        """

        guild = cast(discord.Guild, interaction.guild)
        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this."
            )
            return
        if not settings.spawnalert:
            await interaction.response.send_message(
                "The Bot Owner has disabled this feature from the bot"
            )
            return
        config, created = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if role:
            if config.spawn_ping == role.id:
                config.spawn_ping = None  # type: ignore
                await config.save()
                self.bot.dispatch("carfigures_settings_change", guild, role=None)
                await interaction.response.send_message(
                    f"{settings.bot_name} will no longer alert {role.mention} when {settings.collectible_name}s spawn."
                )
            else:
                config.spawn_ping = role.id  # type: ignore
                await config.save()
                self.bot.dispatch("carfigures_settings_change", guild, role=role)
                await interaction.response.send_message(
                    f"{settings.bot_name} will now alert {role.mention} when {settings.collectible_name}s spawn."
                )
                return
        else:
            await interaction.response.send_message(
                "Please select a proper role."
            )

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def profile(
        self,
        interaction: discord.Interaction
    ):
        """
        Display information about the server.
        """

        cars = await _get_10_cars_emojis(self)
        guild = interaction.guild
        config, created = await GuildConfig.get_or_create(guild_id=guild.id)
        embed = discord.Embed(
            title=f"❖ {guild.name} Server Info",
            color=settings.default_embed_color,
        )
        embed.description = (
            f"{' '.join(str(x) for x in cars)}\n"
            f"**◲ Server Settings**\n"
            f"\u200b **⋄ Spawn Channel:** {config.spawn_channel or 'Not set'}\n"
            f"\u200b **⋄ Spawn Alert Role:** {config.spawn_ping or 'Not set'}\n\n"
            f"**Ⅲ Server Info**\n"
            f"\u200b **⋄ Server ID:** {guild.id}\n"
            f"\u200b **⋄ Server Owner:** {guild.owner}\n"
            f"\u200b **⋄ Server Description:** {guild.description if guild.description else 'None'}\n\n"
            f"\u200b **⋄ Member Count:** {guild.member_count}\n"
            f"\u200b **⋄ Created Since:** {guild.created_at.strftime('%d/%m/%y')}\n\n"
            )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(embed=embed)

