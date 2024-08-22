import discord
import logging

from typing import TYPE_CHECKING, cast

from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from carfigures.core.models import (
    GuildConfig,
    DonationPolicy,
    PrivacyPolicy,
    Player as PlayerModel,
    CarInstance,
    cars,
    DONATION_POLICY_MAP,
    PRIVATE_POLICY_MAP,
)
from carfigures.core.utils.buttons import ConfirmChoiceView
from carfigures.packages.my.components import (
    _get_10_cars_emojis,
    AcceptTOSView,
    activation_embed,
)


from carfigures.settings import settings, appearance, commandings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.my")


class My(commands.GroupCog, group_name=commandings.my_group):
    """
    idk for now
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot
        self.server.parent = self.__cog_app_commands_group__
        self.own.parent = self.__cog_app_commands_group__

    server = app_commands.Group(name="server", description="Server management")
    own = app_commands.Group(name="own", description="My management")
    friends = app_commands.Group(name="friends", description="Friends management")

    @own.command()
    @app_commands.choices(
        policy=[
            app_commands.Choice(name="Public Inventory", value=PrivacyPolicy.PUBLIC),
            app_commands.Choice(
                name="Friends Only Inventory", value=PrivacyPolicy.FRIENDS
            ),
            app_commands.Choice(name="Private Inventory", value=PrivacyPolicy.PRIVATE),
        ]
    )
    async def privacy(self, interaction: discord.Interaction, policy: PrivacyPolicy):
        """
        Set your privacy policy.
        """

        user, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        user.privacy_policy = policy
        await user.save()
        await interaction.response.send_message(
            f"Your privacy policy has been set to **{policy.name}**.", ephemeral=True
        )

    @app_commands.choices(
        policy=[
            app_commands.Choice(
                name="Accept all donations", value=DonationPolicy.ALWAYS_ACCEPT
            ),
            app_commands.Choice(
                name="Request your approval first",
                value=DonationPolicy.REQUEST_APPROVAL,
            ),
            app_commands.Choice(
                name="Deny all donations", value=DonationPolicy.ALWAYS_DENY
            ),
        ]
    )
    @own.command()
    async def policy(
        self, interaction: discord.Interaction, policy: app_commands.Choice[int]
    ):
        """
        Change how you want to receive donations.

        Parameters
        ----------
        policy: DonationPolicy
            The new policy for accepting donations
        """
        user, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        user.donation_policy = DonationPolicy(policy.value)
        if policy.value == DonationPolicy.ALWAYS_ACCEPT:
            await interaction.response.send_message(
                f"Setting updated, you will now receive all donated {appearance.collectible_plural} "
                "immediately.",
                ephemeral=True,
            )
        elif policy.value == DonationPolicy.REQUEST_APPROVAL:
            await interaction.response.send_message(
                "Setting updated, you will now have to approve donation requests manually.",
                ephemeral=True,
            )
        elif policy.value == DonationPolicy.ALWAYS_DENY:
            await interaction.response.send_message(
                "Setting updated, it is now impossible to use "
                f"`/{commandings.cars_group} {commandings.gift_name}` with "
                "you. It is still possible to perform donations using the trade system.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("Invalid input!", ephemeral=True)
            return
        await user.save()  # do not save if the input is invalid

    @own.command()
    async def profile(self, interaction: discord.Interaction):
        """
        Show your profile.
        """

        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        await player.fetch_related("cars")

        emojis = ""
        if not settings.minimal_profile:
            cars = await _get_10_cars_emojis(self)
            emojis = " ".join(str(x) for x in cars)

        # Creating the Embed and Storting the variables in it
        embed = discord.Embed(
            title=f" ❖ {interaction.user.display_name}'s Profile",
            color=settings.default_embed_color,
        )

        embed.description = (
            f"{emojis}\n"
            f"**Ⅲ Player Settings**\n"
            f"\u200b **⋄ Privacy Policy:** {PRIVATE_POLICY_MAP[player.privacy_policy]}\n"
            f"\u200b **⋄ Donation Policy:** {DONATION_POLICY_MAP[player.donation_policy]}\n\n"
            f"**Ⅲ Player Info\n**"
            f"\u200b **⋄ {appearance.collectible_plural.title()} Collected:** {await player.cars.filter().count()}\n"
            f"\u200b **⋄ Rebirths Done:** {player.rebirths}\n"
            f"\u200b **⋄ Bolts Acquired:** {player.bolts}\n"
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @own.command()
    async def rebirth(self, interaction: discord.Interaction):
        """
        Delete all your cars if you have full completion, to get advantages back
        """

        bot_carfigures = {
            id: carfigure.pk for id, carfigure in cars.items() if carfigure.enabled
        }
        filters = {"player__discord_id": interaction.user.id, "car__enabled": True}

        if not bot_carfigures:
            await interaction.response.send_message(
                f"There are no {appearance.collectible_plural} registered on this bot yet.",
                ephemeral=True,
            )
            return

        owned_carfigures = set(
            carfigures[0]
            for carfigures in await CarInstance.filter(**filters)
            .distinct()  # Do not query everything
            .values_list("car_id")
        )

        if missing := set(
            cars for cars in bot_carfigures.items() if cars not in owned_carfigures
        ):
            await interaction.response.send_message(
                "You haven't reached 100% of the bot collection yet."
                f"there is still {len(missing)}",
                ephemeral=True,
            )
            return

        view = ConfirmChoiceView(interaction)
        await interaction.response.send_message(
            f"Are you sure you want to delete all your {appearance.collectible_plural} for advantages?",
            view=view,
        )

        await view.wait()
        if view.value is None or not view.value:
            return
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        player.rebirths += 1
        await player.save()
        await CarInstance.filter(player=player).delete()

        ordinal_rebirth = (
            "1st"
            if player.rebirths == 1
            else "2nd"
            if player.rebirths == 2
            else "3rd"
            if player.rebirths == 3
            else f"{player.rebirths}th"
        )

        await interaction.followup.send(
            f"Congratulations! this is your {ordinal_rebirth} Rebirth, hopefully u get even more!"
        )

    @server.command()
    async def spawnchannel(
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
                "You need the permission to manage the server to use this.",
                ephemeral=True,
            )
            return
        if not channel.permissions_for(guild.me).read_messages:
            await interaction.response.send_message(
                f"I need the permission to read messages in {channel.mention}.",
                ephemeral=True,
            )
            return
        if not channel.permissions_for(guild.me).send_messages:
            await interaction.response.send_message(
                f"I need the permission to send messages in {channel.mention}.",
                ephemeral=True,
            )
            return
        if not channel.permissions_for(guild.me).embed_links:
            await interaction.response.send_message(
                f"I need the permission to send embed links in {channel.mention}.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=activation_embed, view=AcceptTOSView(interaction, channel)
        )

    @server.command()
    async def spawnstate(self, interaction: discord.Interaction):
        """
        Disable or enable carfigures spawning.
        """
        guild = cast(discord.Guild, interaction.guild)  # guild-only command
        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this.",
                ephemeral=True,
            )
            return
        config, _ = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if config.enabled:
            config.enabled = False  # type: ignore
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=False)
            await interaction.response.send_message(
                f"{settings.bot_name} is now disabled in this server. Commands will still be "
                f"available, but the spawn of new {appearance.collectible_plural} is suspended.\n"
                "To re-enable the spawn, use the same command."
            )
        else:
            config.enabled = True  # type: ignore
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=True)
            if config.spawn_channel and (
                channel := guild.get_channel(config.spawn_channel)
            ):
                await interaction.response.send_message(
                    f"{settings.bot_name} is now enabled in this server, "
                    f"{appearance.collectible_plural} will start spawning soon in {channel.mention}."
                )
            else:
                await interaction.response.send_message(
                    f"{settings.bot_name} is now enabled in this server, however there is no "
                    "spawning channel set. Please configure one with `/server channel`."
                )

    @server.command()
    async def spawnrole(self, interaction: discord.Interaction, role: discord.Role):
        """
        Enable, disable or set role spawn alert for your server
        """

        guild = cast(discord.Guild, interaction.guild)
        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this.",
                ephemeral=True,
            )
            return
        if not settings.spawnalert:
            await interaction.response.send_message(
                "The bot owner has disabled this feature from the bot.", ephemeral=True
            )
            return
        config, _ = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if role:
            if config.spawn_ping == role.id:
                config.spawn_ping = None  # type: ignore
                await config.save()
                self.bot.dispatch("carfigures_settings_change", guild, role=None)
                await interaction.response.send_message(
                    f"{settings.bot_name} will no longer alert {role.mention} when {appearance.collectible_plural} spawn."
                )
            else:
                config.spawn_ping = role.id  # type: ignore
                await config.save()
                self.bot.dispatch("carfigures_settings_change", guild, role=role)
                await interaction.response.send_message(
                    f"{settings.bot_name} will now alert {role.mention} when {appearance.collectible_plural} spawn."
                )
                return

    @server.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def info(self, interaction: discord.Interaction):
        """
        Display information about the server.
        """

        guild = cast(discord.Guild, interaction.guild)
        config, _ = await GuildConfig.get_or_create(guild_id=guild.id)
        spawn_channel = guild.get_channel(config.spawn_channel)
        spawn_role = guild.get_role(config.spawn_ping)
        emojis = ""
        if not settings.minimal_profile:
            cars = await _get_10_cars_emojis(self)
            emojis = " ".join(str(x) for x in cars)
            spawn_channel = f"<#{config.spawn_channel}>"
            spawn_role = f"<@&{config.spawn_ping}>"

        embed = discord.Embed(
            title=f"❖ {guild.name} Server Info",
            color=settings.default_embed_color,
        )
        embed.description = (
            f"{emojis}\n"
            f"**Ⅲ Server Settings**\n"
            f"\u200b **⋄ Spawn State:** {'Enabled' if config.enabled else 'Disabled'}\n"
            f"\u200b **⋄ Spawn Channel:** {spawn_channel or 'Not set'}\n"
            f"\u200b **⋄ Spawn Alert Role:** {spawn_role or 'Not set'}\n\n"
            f"**Ⅲ Server Info**\n"
            f"\u200b **⋄ Server ID:** {guild.id}\n"
            f"\u200b **⋄ Server Owner:** <@{guild.owner_id}>\n"
            f"\u200b **⋄ Member Count:** {guild.member_count}\n"
            f"\u200b **⋄ Created Since:** {format_dt(guild.created_at, style='R')}\n\n"
            f"\u200b **⋄ Cars Caught Here:** {await CarInstance.filter(server_id=guild.id).count()}"
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await interaction.response.send_message(embed=embed)
