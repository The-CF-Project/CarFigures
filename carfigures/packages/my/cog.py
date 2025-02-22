import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from tortoise.expressions import Q

from carfigures.core import models
from carfigures.core.utils.buttons import ConfirmChoiceView
from carfigures.packages.my.components import (
    AcceptTOSView,
    activation_embed,
)
from carfigures.settings import appearance, settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.my")


class My(commands.GroupCog):
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
    async def privacy(self, interaction: discord.Interaction, policy: models.PrivacyPolicy):
        """
        Set your privacy policy.
        """
        user, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        user.privacyPolicy = policy
        await user.save()
        await interaction.response.send_message(
            f"Your privacy policy has been set to **{policy.name}**.", ephemeral=True
        )

    @own.command()
    async def policy(self, interaction: discord.Interaction, policy: models.DonationPolicy):
        """
        Change how you want to receive donations.
        """
        user, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        user.donationPolicy = policy
        await user.save()
        await interaction.response.send_message(
            f"Your gift policy has been set to **{policy.name}**.", ephemeral=True
        )

    @own.command()
    async def profile(self, interaction: discord.Interaction):
        """
        Show your profile.
        """

        player, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        await player.fetch_related("cars")
        # Creating the Embed and Storting the variables in it
        embed = discord.Embed(
            title=f" ❖ {interaction.user.display_name}'s Profile",
            color=settings.defaultEmbedColor,
        )
        embed.description = (
            f"**Ⅲ Player Settings**\n"
            f"\u200b **⋄ Privacy Policy:** {player.privacyPolicy.name}\n"
            f"\u200b **⋄ Donation Policy:** {player.donationPolicy.name}\n\n"
            f"**Ⅲ Player Info\n**"
            f"\u200b **⋄ {appearance.collectiblePlural.title()} Collected:** {await player.cars.filter().count()}\n"
            f"\u200b **⋄ Rebirths Done:** {player.rebirths}\n"
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @own.command()
    async def rebirth(self, interaction: discord.Interaction):
        """
        Restart the game
        """

        player, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        bot_carfigures = {x: y.pk for x, y in models.cars.items() if y.enabled}

        filters = {
            "player__discord_id": interaction.user.id,
            "car__enabled": True,
            "favorite": False,
            "exclusive": None,
            "event": None,
        }
        if not bot_carfigures:
            await interaction.response.send_message(
                f"There are no {appearance.collectiblePlural} registered on this bot yet.",
                ephemeral=True,
            )
            return

        owned_carfigures = set(
            x[0]
            for x in await models.CarInstance.filter(**filters)
            .distinct()  # Do not query everything
            .values_list("car_id")
        )

        if missing := set(y for x, y in bot_carfigures.items() if x not in owned_carfigures):
            await interaction.response.send_message(
                "You haven't reached 100% of the bot collection yet." f"there is still {missing}",
                ephemeral=True,
            )
            return

        view = ConfirmChoiceView(interaction)
        await interaction.response.send_message(
            f"Are you sure you want to delete all your {appearance.collectiblePlural} for advantages?",
            view=view,
        )

        await view.wait()
        if view.value is None or not view.value:
            return
        player.rebirths += 1
        await player.save()
        await models.CarInstance.filter(player=player).delete()

        await interaction.followup.send(
            f"Congratulations! this is the rebirth number {player.rebirths}, hopefully u get even more!"
        )

    @friends.command(name="profiles")
    async def friendsprofiles(self, interaction: discord.Interaction):
        """
        List all your friends' profiles
        """
        player, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        friendships = await models.Friendship.filter(
            Q(friender=player) | Q(friended=player)
        ).prefetch_related("friender", "friended")

        if not friendships:
            await interaction.response.send_message(
                "Imagine having no friends bro", ephemeral=True
            )
            return

        options = []
        for friendship in friendships:
            friend_player = (
                friendship.friended
                if friendship.friender.discord_id == player.discord_id
                else friendship.friender
            )

            friend = await self.bot.fetch_user(friend_player.discord_id)
            options.append(
                discord.SelectOption(
                    label=f"{friend.display_name}",
                    description=f"{'Bestie ' if friendship.bestie else ''}Since {friendship.since.strftime('%Y-%m-%d')}",
                    value=str(friendship.id),
                )
            )

        select = discord.ui.Select(
            placeholder="Choose a friend...",
            min_values=1,
            max_values=1,
            options=options,
        )

        embed = discord.Embed(
            title="Select your friend!",
            description="Please select a friend to view their profile.",
            color=settings.defaultEmbedColor,
        )
        view = discord.ui.View()

        async def select_callback(interaction: discord.Interaction):
            friendship_id = int(select.values[0])
            friendship = await models.Friendship.get(id=friendship_id).prefetch_related(
                "friender", "friended"
            )
            friend = (
                friendship.friended
                if friendship.friender.discord_id == player.discord_id
                else friendship.friender
            )

            friend_user = await self.bot.fetch_user(friend.discord_id)
            embed = discord.Embed(
                title=f"❖ {friend_user.display_name}'s Profile",
                description=(
                    f"**Ⅲ Player Settings**\n"
                    f"\u200b **⋄ Privacy Policy:** {friend.privacyPolicy.name}\n"
                    f"\u200b **⋄ Donation Policy:** {friend.donationPolicy.name}\n\n"
                    f"**Ⅲ Player Info\n**"
                    f"\u200b **⋄ {appearance.collectiblePlural.title()} Collected:** {await friend.cars.filter().count()}\n"
                    f"\u200b **⋄ Rebirths Done:** {friend.rebirths}\n"
                ),
                color=settings.defaultEmbedColor,
            )
            embed.set_thumbnail(url=friend_user.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=view)

        select.callback = select_callback  # type: ignore
        await interaction.response.send_message(embed=embed, view=view.add_item(select))

    @friends.command(name="add")
    async def friendsadd(self, interaction: discord.Interaction, user: discord.User):
        """
        Send a friend request to another user.
        """
        sender, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        receiver, _ = await models.Player.get_or_create(discord_id=user.id)

        if sender == receiver:
            await interaction.response.send_message(
                "You can't add yourself as a friend.", ephemeral=True
            )
            return

        existing_request = (
            await models.FriendshipRequest.filter(
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
                "You have already sent a friend request to {user.display_name}", ephemeral=True
            )
            return
        existing_friendship = await models.Friendship.filter(
            Q(
                friender__discord_id=sender.discord_id,
                friended__discord_id=receiver.discord_id,
            )
            | Q(
                friender__discord_id=receiver.discord_id,
                friended__discord_id=sender.discord_id,
            )
        ).first()

        if existing_friendship:
            await interaction.response.send_message(
                f"You are already friends with {user.display_name}!",
                ephemeral=True,
            )
            return

        await models.FriendshipRequest.create(sender=sender, receiver=receiver)
        await interaction.response.send_message(
            f"You have sent a friend request to {user.display_name}",
            ephemeral=True,
        )

    @friends.command(name="requests")
    async def friendsrequests(self, interaction: discord.Interaction):
        """
        View and manage your friend requests.
        """
        player, _ = await models.Player.get_or_create(discord_id=interaction.user.id)
        requests = await models.FriendshipRequest.filter(receiver=player).prefetch_related(
            "sender"
        )

        if not requests:
            await interaction.response.send_message(
                "You currently don't have any friend requests", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Coming Friend requests!",
            description="select one of the requests to view!",
            color=settings.defaultEmbedColor,
        )

        options = []
        for request in requests:
            sender = request.sender
            senderuser = await self.bot.fetch_user(sender.discord_id)
            options.append(
                discord.SelectOption(
                    label=f"{senderuser.display_name}",
                    description=f"This Friend request came at {request.created_at}",
                    value=str(request.id),
                )
            )

        select = discord.ui.Select(
            placeholder="Pls select one of the people",
            options=options,
        )

        async def select_callback(interaction: discord.Interaction):
            request_id = int(select.values[0])
            friend_request = await models.FriendshipRequest.get(id=request_id).prefetch_related(
                "sender"
            )
            view = ConfirmChoiceView(interaction)
            await interaction.response.send_message(
                f"you sure u want to accept this request from {friend_request.sender.discord_id}?",
                view=view,
                ephemeral=True,
            )

            await view.wait()
            if view.value:
                await models.Friendship.create(
                    friender=await friend_request.sender,
                    friended=await friend_request.receiver,
                )
                await friend_request.delete()
                await interaction.followup.send(
                    "you have accepted this request",
                    ephemeral=True,
                )
            else:
                await friend_request.delete()
                await interaction.followup.send(
                    "you have rejected this request",
                    ephemeral=True,
                )

        select.callback = select_callback  # type: ignore
        view = discord.ui.View()
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @server.command(
        description=f"Set the channel where {appearance.collectiblePlural} will spawn."
    )
    async def spawnchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        """
        Set the channel where carfigures will spawn.
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

    @server.command(description=f"Disable or enable {settings.botName} from spawning.")
    async def spawnstate(self, interaction: discord.Interaction):
        """
        Disable or enable CarFigures from spawning.
        """
        guild = cast(discord.Guild, interaction.guild)  # guild-only command
        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this.",
                ephemeral=True,
            )
            return
        config, _ = await models.GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if config.enabled:
            config.enabled = False  # type: ignore
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=False)
            await interaction.response.send_message(
                f"{settings.botName} is now disabled in this server. Commands will still be "
                f"available, but the spawn of new {appearance.collectiblePlural} is suspended.\n"
                "To re-enable the spawn, use the same command."
            )
        else:
            config.enabled = True  # type: ignore
            await config.save()
            self.bot.dispatch("carfigures_settings_change", guild, enabled=True)
            if config.spawnChannel and (channel := guild.get_channel(config.spawnChannel)):
                await interaction.response.send_message(
                    f"{settings.botName} is now enabled in this server, "
                    f"{appearance.collectiblePlural} will start spawning soon in {channel.mention}."
                )
            else:
                await interaction.response.send_message(
                    f"{settings.botName} is now enabled in this server, however there is no "
                    "spawning channel set. Please configure one with `/my server spawnchannel`."
                )

    @server.command()
    async def spawnrole(self, interaction: discord.Interaction, role: discord.Role):
        """
        Set the role spawn alert for your server
        """

        user = cast(discord.Member, interaction.user)
        if not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the permission to manage the server to use this.",
                ephemeral=True,
            )
            return
        config, _ = await models.GuildConfig.get_or_create(guild_id=interaction.guild_id)
        if config.spawnRole == role.id:
            config.spawnRole = None  # type: ignore
            await config.save()
            await interaction.response.send_message(
                f"{settings.botName} will no longer alert {role.mention} when {appearance.collectiblePlural} spawn."
            )
        else:
            config.spawnRole = role.id
            await config.save()
            await interaction.response.send_message(
                f"{settings.botName} will now alert {role.mention} when {appearance.collectiblePlural} spawn."
            )
            return

    @server.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def info(self, interaction: discord.Interaction):
        """
        Display information about the server.
        """

        guild = cast(discord.Guild, interaction.guild)
        config = await models.GuildConfig.get(guild_id=guild.id)
        embed = discord.Embed(
            title=f"❖ {guild.name} Server Info",
            color=settings.defaultEmbedColor,
        )
        embed.description = (
            f"**Ⅲ Server Settings**\n"
            f"\u200b **⋄ Spawn State:** {'Enabled' if config.enabled else 'Disabled'}\n"
            f"\u200b **⋄ Spawn Channel:** {guild.get_channel(config.spawnChannel) or 'Not set'}\n"
            f"\u200b **⋄ Spawn Alert Role:** {guild.get_role(config.spawnRole) or 'Not set'}\n\n"
            f"**Ⅲ Server Info**\n"
            f"\u200b **⋄ Server ID:** {guild.id}\n"
            f"\u200b **⋄ Server Owner:** <@{guild.owner_id}>\n"
            f"\u200b **⋄ Member Count:** {guild.member_count}\n"
            f"\u200b **⋄ Created Since:** {format_dt(guild.created_at, style='R')}\n\n"
            f"\u200b **⋄ {appearance.collectiblePlural.title()} Caught Here:**"
            f" {await models.CarInstance.filter(server=guild.id).count()}"
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await interaction.response.send_message(embed=embed)
