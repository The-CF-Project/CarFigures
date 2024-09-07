import discord
import logging

from typing import TYPE_CHECKING, cast

from discord import Interaction, app_commands
from discord.ext import commands
from discord.utils import format_dt
from tortoise.expressions import Q
from discord.ui import View, Select

from carfigures.core.models import (
    Friendship as FriendshipModel,
    GuildConfig,
    DonationPolicy,
    Languages,
    FriendshipRequest as FriendshipRequestModel,
    PrivacyPolicy,
    Player as PlayerModel,
    CarInstance,
    cars,
)
from carfigures.core.utils.buttons import ConfirmChoiceView
from carfigures.packages.my.components import (
    FriendSelector,
    _get_10_cars_emojis,
    AcceptTOSView,
    activation_embed,
)


from carfigures.configs import settings, appearance, commandconfig
from carfigures.langs import LANGUAGE_MAP, translate

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.my")


class My(commands.GroupCog, group_name=commandconfig.my_group):
    """
    The My Command Collection
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    server = app_commands.Group(name="server", description="Server management")
    own = app_commands.Group(name="own", description="My management")
    rebirth = app_commands.Group(name="rebirth", description="Rebirth management")
    friends = app_commands.Group(name="friends", description="Friends management")
    goals = app_commands.Group(name="goals", description="Goals management")

    @app_commands.choices(
        policy=[
            app_commands.Choice(name="Public Inventory", value=PrivacyPolicy.PUBLIC),
            app_commands.Choice(name="Friends Only", value=PrivacyPolicy.FRIENDS),
            app_commands.Choice(name="Private Inventory", value=PrivacyPolicy.PRIVATE),
        ]
    )
    @own.command(name="privacy")
    async def playerprivacy(
        self, interaction: discord.Interaction, policy: PrivacyPolicy
    ):
        """
        Set your privacy policy.
        """

        user, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        user.privacy_policy = policy
        await user.save()
        await interaction.response.send_message(
            translate("privacy_updated", user.language, policy=policy.name),
            ephemeral=True,
        )

    @own.command(name="language")
    async def playerlanguage(
        self, interaction: discord.Interaction, language: Languages
    ):
        """
        Set your preferred Language
        """

        user, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        user.language = language
        await user.save()
        await interaction.response.send_message(
            f"you have successfully changed your language to **{language.name}**"
        )

    @app_commands.choices(
        policy=[
            app_commands.Choice(
                name="Accept all donations", value=DonationPolicy.ALWAYS_ACCEPT
            ),
            app_commands.Choice(
                name="Request your approval first",
                value=DonationPolicy.APPROVAL_REQUIRED,
            ),
            app_commands.Choice(
                name="Deny all donations", value=DonationPolicy.ALWAYS_DENY
            ),
        ]
    )
    @own.command(name="policy")
    async def playerpolicy(
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
        await user.save()  # do not save if the input is invalid

        match policy.value:
            case DonationPolicy.ALWAYS_ACCEPT:
                message = translate(
                    "policy_updated_accept",
                    user.language,
                    collectibles=appearance.collectible_plural,
                )
            case DonationPolicy.APPROVAL_REQUIRED:
                message = translate("policy_updated_approval", user.language)
            case DonationPolicy.ALWAYS_DENY:
                message = translate(
                    "policy_updated_deny",
                    user.language,
                    cars_group=commandconfig.cars_group,
                    gift_name=commandconfig.gift_name,
                )
            case _:
                message = translate("invalid_input", user.language)

        await interaction.response.send_message(message, ephemeral=True)

    @own.command(name="profile")
    async def playerprofile(self, interaction: discord.Interaction):
        """
        View your profile.
        """

        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        await player.fetch_related("cars")

        emojis = ""
        if not settings.minimal_profile:
            cars = await _get_10_cars_emojis(self)
            emojis = " ".join(str(x) for x in cars)

        # Creating the Embed and Storting the variables in it
        embed = discord.Embed(
            title=translate(
                "profile_title", player.language, username=interaction.user.display_name
            ),
            color=settings.default_embed_color,
        )

        embed.description = (
            f"{emojis}\n"
            f"**Ⅲ {translate('player_settings', player.language)}**\n"
            f"\u200b **⋄ {translate('privacy_policy', player.language)}:** "
            f"{translate(player.privacy_policy.name.lower(), player.language)}\n"
            f"\u200b **⋄ {translate('donation_policy', player.language)}:** "
            f"{translate(player.donation_policy.name.lower(), player.language)}\n"
            f"\u200b **⋄ {translate('language_selected', player.language)}:** {LANGUAGE_MAP[player.language]}\n\n"
            f"**Ⅲ {translate('player_info', player.language)}**\n"
            f"\u200b **⋄ {translate('cars_collected', player.language)}:** {await player.cars.filter().count()}\n"
            f"\u200b **⋄ {translate('rebirths_done', player.language)}:** {player.rebirths}\n"
            f"\u200b **⋄ {translate('bolts_acquired', player.language)}:** {player.bolts}\n"
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @rebirth.command(name="start")
    async def rebirthstart(self, interaction: discord.Interaction):
        """
        Delete all your cars if you have full completion, to get advantages back
        """

        player = await PlayerModel.get(discord_id=interaction.user.id)
        bot_carfigures = {
            id: carfigure.pk for id, carfigure in cars.items() if carfigure.enabled
        }
        filters = {
            "player__discord_id": interaction.user.id,
            "car__enabled": True,
            "favorite": False,
            "exclusive": None,
            "event": None,
        }

        if not bot_carfigures:
            await interaction.response.send_message(
                translate(
                    "no_cars_registered",
                    player.language,
                    collectibles=appearance.collectible_plural,
                ),
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
                translate(
                    "incomplete_collection", player.language, missing=len(missing)
                ),
                ephemeral=True,
            )
            return

        view = ConfirmChoiceView(interaction)
        await interaction.response.send_message(
            translate(
                "confirm_rebirth",
                player.language,
                collectibles=appearance.collectible_plural,
            ),
            view=view,
        )

        await view.wait()
        if view.value is None or not view.value:
            return
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        player.rebirths += 1
        await player.save()
        await CarInstance.filter(player=player).delete()

        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )
        await interaction.followup.send(
            translate(
                "rebirth_completed", player.language, ordinal=ordinal(player.rebirths)
            )
        )

    @friends.command(name="profiles")
    async def friendsprofiles(self, interaction: discord.Interaction):
        """
        List all your friends' profiles
        """
        player = await PlayerModel.get(discord_id=interaction.user.id)
        friends = await player.get_friends()
        embed = discord.Embed(
            title="Select your friend!",
            description="Please select a friend to view their profile.",
            color=settings.default_embed_color,
        )
        view = FriendSelector(friends, player, "profiles")
        await interaction.response.send_message(embed=embed, view=view)

    @friends.command(name="goals")
    async def friendsgoals(self, interaction: discord.Interaction):
        """
        List all your friends' goals
        """
        player = await PlayerModel.get(discord_id=interaction.user.id)
        friends = await player.get_friends()
        embed = discord.Embed(
            title="Select your friend!",
            description="Please select a friend to view their goals.",
            color=settings.default_embed_color,
        )
        view = FriendSelector(friends, player, "goals")
        await interaction.response.send_message(embed=embed, view=view)

    @friends.command(name="add")
    async def friendsadd(self, interaction: Interaction, user: discord.User):
        """
        Send a friend request to another user.
        """
        sender, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        receiver, _ = await PlayerModel.get_or_create(discord_id=user.id)

        if sender == receiver:
            await interaction.response.send_message(
                translate("cannot_friend_self", sender.language), ephemeral=True
            )
            return

        existing_request = (
            await FriendshipRequestModel.filter(
                (
                    Q(sender__discord_id=sender.discord_id)
                    & Q(receiver__discord_id=receiver.discord_id)
                )
                | (
                    Q(sender__discord_id=receiver.discord_id)
                    & Q(receiver__discord_id=sender.discord_id)
                )
            )
            .first()
            .prefetch_related("sender", "receiver")
        )

        if existing_request:
            await interaction.response.send_message(
                translate(
                    "friend_request_already_sent",
                    sender.language,
                    user=user.display_name,
                ),
                ephemeral=True,
            )
            return
        existing_friendship = await FriendshipModel.filter(
            Q(
                player1__discord_id=sender.discord_id,
                player2__discord_id=receiver.discord_id,
            )
            | Q(
                player1__discord_id=receiver.discord_id,
                player2__discord_id=sender.discord_id,
            )
        ).first()

        if existing_friendship:
            await interaction.response.send_message(
                translate("already_friends", sender.language, user=user.display_name),
                ephemeral=True,
            )
            return

        await FriendshipRequestModel.create(sender=sender, receiver=receiver)
        await interaction.response.send_message(
            translate("friend_request_sent", sender.language, user=user.display_name),
            ephemeral=True,
        )

    @friends.command(name="requests")
    async def friendsrequests(self, interaction: Interaction):
        """
        View and manage your friend requests.
        """
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        requests = await FriendshipRequestModel.filter(
            receiver=player
        ).prefetch_related("sender")

        if not requests:
            await interaction.response.send_message(
                translate("no_friend_requests", player.language), ephemeral=True
            )
            return

        embed = discord.Embed(
            title=translate(
                "friend_requests_title",
                player.language,
                user=interaction.user.display_name,
            ),
            color=settings.default_embed_color,
        )

        options = []
        for request in requests:
            sender = request.sender
            options.append(
                discord.SelectOption(
                    label=f"{sender.discord_id}",
                    description=translate(
                        "friend_request_from", player.language, user=sender.discord_id
                    ),
                    value=str(request.id),
                )
            )

        select = Select(
            placeholder=translate("select_friend_request", player.language),
            options=options,
        )

        async def select_callback(interaction: discord.Interaction):
            request_id = int(select.values[0])
            request = await FriendshipRequestModel.get(id=request_id).prefetch_related(
                "sender"
            )
            view = ConfirmChoiceView(interaction)
            await interaction.response.send_message(
                translate(
                    "confirm_friend_request",
                    player.language,
                    user=request.sender.discord_id,
                ),
                view=view,
                ephemeral=True,
            )

            await view.wait()
            if view.value:
                await FriendshipModel.create(player1=player, player2=request.sender)
                await request.delete()
                await interaction.followup.send(
                    translate(
                        "friend_request_accepted",
                        player.language,
                        user=request.sender.discord_id,
                    ),
                    ephemeral=True,
                )
            else:
                await request.delete()
                await interaction.followup.send(
                    translate(
                        "friend_request_declined",
                        player.language,
                        user=request.sender.discord_id,
                    ),
                    ephemeral=True,
                )

        select.callback = select_callback  # type: ignore
        view = View()
        view.add_item(select)

        embed.description = translate("friend_requests_description", player.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                translate("no_permission", player.language), ephemeral=True
            )
            return
        if not channel.permissions_for(guild.me).read_messages:
            await interaction.response.send_message(
                translate(
                    "bot_needs_permission",
                    player.language,
                    permission="read messages",
                    channel=channel.mention,
                ),
                ephemeral=True,
            )
            return
        if not channel.permissions_for(guild.me).send_messages:
            await interaction.response.send_message(
                translate(
                    "bot_needs_permission",
                    player.language,
                    permission="send messages",
                    channel=channel.mention,
                ),
                ephemeral=True,
            )
            return
        if not channel.permissions_for(guild.me).embed_links:
            await interaction.response.send_message(
                translate(
                    "bot_needs_permission",
                    player.language,
                    permission="embed links",
                    channel=channel.mention,
                ),
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
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)

        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                translate("no_permission", player.language), ephemeral=True
            )
            return
        config, _ = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if config.enabled:
            config.enabled = False
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=False)
            await interaction.response.send_message(
                translate(
                    "spawn_disabled",
                    player.language,
                    bot_name=settings.bot_name,
                    collectibles=appearance.collectible_plural,
                )
            )
        else:
            config.enabled = True
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=True)
            if config.spawn_channel and (
                channel := guild.get_channel(config.spawn_channel)
            ):
                await interaction.response.send_message(
                    translate(
                        "spawn_enabled",
                        player.language,
                        bot_name=settings.bot_name,
                        collectibles=appearance.collectible_plural,
                        channel=channel.mention,
                    )
                )
            else:
                await interaction.response.send_message(
                    translate(
                        "spawn_enabled_no_channel",
                        player.language,
                        bot_name=settings.bot_name,
                    )
                )

    @server.command()
    async def spawnrole(self, interaction: discord.Interaction, role: discord.Role):
        """
        Enable, disable or set role spawn alert for your server
        """

        guild = cast(discord.Guild, interaction.guild)
        user = cast(discord.Member, interaction.user)
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                translate("no_permission", player.language), ephemeral=True
            )
            return
        if not settings.spawnalert:
            await interaction.response.send_message(
                translate("spawn_alert_disabled", player.language), ephemeral=True
            )
            return
        config, _ = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if role:
            if config.spawn_ping == role.id:
                config.spawn_ping = None  # type: ignore
                await config.save()
                self.bot.dispatch("carfigures_settings_change", guild, role=None)
                await interaction.response.send_message(
                    translate(
                        "spawn_alert_removed",
                        player.language,
                        bot_name=settings.bot_name,
                        role=role.mention,
                        collectibles=appearance.collectible_plural,
                    )
                )
            else:
                config.spawn_ping = role.id
                await config.save()
                self.bot.dispatch("carfigures_settings_change", guild, role=role)
                await interaction.response.send_message(
                    translate(
                        "spawn_alert_set",
                        player.language,
                        bot_name=settings.bot_name,
                        role=role.mention,
                        collectibles=appearance.collectible_plural,
                    )
                )

    @server.command(name="language")
    async def serverlanguage(
        self, interaction: discord.Interaction, language: Languages
    ):
        """
        Set your preferred Language
        """

        server, _ = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        server.language = language
        await server.save()
        await interaction.response.send_message(
            f"you have successfully changed your server language to **{language.name}**"
        )

    @server.command(name="info")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def serverinfo(self, interaction: discord.Interaction):
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
            title=translate(
                "server_info_title", config.language, server_name=guild.name
            ),
            color=settings.default_embed_color,
        )
        embed.description = (
            f"{emojis}\n"
            f"**Ⅲ {translate('server_settings', config.language)}**\n"
            f"\u200b **⋄ {translate('language_selected', config.language)}:** {LANGUAGE_MAP[config.language]}\n"
            f"\u200b **⋄ {translate('spawn_state', config.language)}:** "
            f"{translate('enabled' if config.enabled else 'disabled', config.language)}\n"
            f"\u200b **⋄ {translate('spawn_channel', config.language)}:** "
            f"{spawn_channel or translate('not_set', config.language)}\n"
            f"\u200b **⋄ {translate('spawn_alert_role', config.language)}:** "
            f"{spawn_role or translate('not_set', config.language)}\n\n"
            f"**Ⅲ {translate('server_info', config.language)}**\n"
            f"\u200b **⋄ {translate('server_id', config.language)}:** {guild.id}\n"
            f"\u200b **⋄ {translate('server_owner', config.language)}:** <@{guild.owner_id}>\n"
            f"\u200b **⋄ {translate('member_count', config.language)}:** {guild.member_count}\n"
            f"\u200b **⋄ {translate('created_since', config.language)}:** {format_dt(guild.created_at, style='R')}\n\n"
            f"\u200b **⋄ {translate('cars_caught_here', config.language)}:** {await CarInstance.filter(server_id=guild.id).count()}"
        )

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await interaction.response.send_message(embed=embed)
