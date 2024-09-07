from __future__ import annotations
from typing import List

import random
import discord
from discord.ui import Button, View, Select, button

from carfigures.core.models import (
    Player,
    Friendship,
    GuildConfig,
    Car,
    cars as carfigures,
)
from carfigures.configs import settings, information, appearance
from carfigures.langs import translate, LANGUAGE_MAP

activation_embed = discord.Embed(
    colour=settings.default_embed_color,
    title=f"{settings.bot_name} activation",
    description=f"To enable {settings.bot_name} in your server, you must "
    f"read and accept the [Terms of Service]({information.terms_of_service}).\n\n"
    "As a summary, these are the rules of the bot:\n"
    f"- No farming (spamming or creating servers for {appearance.collectible_plural})\n"
    "- Do not attempt to abuse the bot's internals\n"
    "**Not respecting these rules will lead to a blacklist**",
)


class AcceptTOSView(View):
    """
    Button prompting the developer setting up the bot to accept the terms of service.
    """

    def __init__(self, interaction: discord.Interaction, channel: discord.TextChannel):
        super().__init__()
        self.original_interaction = interaction
        self.channel = channel
        self.add_item(
            Button(
                style=discord.ButtonStyle.link,
                label="Terms of Service",
                url=f"{information.terms_of_service}",
            )
        )
        self.add_item(
            Button(
                style=discord.ButtonStyle.link,
                label="Privacy Policy",
                url=f"{information.privacy_policy}",
            )
        )

    @button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}",
    )
    async def accept_button(
        self, interaction: discord.Interaction, item: discord.ui.Button
    ):
        config, _ = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        config.spawn_channel = self.channel.id
        await config.save()
        interaction.client.dispatch(
            "carfigures_settings_change", interaction.guild, channel=self.channel
        )
        self.stop()
        await interaction.response.send_message(
            f"{appearance.collectible_plural.title()}s will start spawning as"
            " users talk unless the bot is disabled."
        )

        self.accept_button.disabled = True
        if self.original_interaction.message:
            try:
                await self.original_interaction.followup.edit_message(
                    self.original_interaction.message.id,
                    view=self,
                )
            except discord.HTTPException:
                pass

    async def on_timeout(self) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True  # type: ignore
        if self.original_interaction.message:
            try:
                await self.original_interaction.followup.edit_message(
                    self.original_interaction.message.id,
                    view=self,
                )
            except discord.HTTPException:
                pass


class GoalSource(Select):
    def __init__(self, friends: List[Friendship], user: Player):
        self.user = user
        options = []
        for friend in friends:
            friend_player = (
                friend.player2
                if friend.player1.discord_id == user.discord_id
                else friend.player1
            )
            options.append(
                discord.SelectOption(
                    label=f"{friend_player.discord_id}",
                    description=f"Goals count: {friend_player.goals.filter().count()}",
                    value=str(friend_player.pk),
                )
            )
        super().__init__(
            placeholder="Choose a friend...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        friendship_id = int(self.values[0])
        goals = await Friendship.get(id=friendship_id).prefetch_related(
            "player1", "player2"
        )
        friend = (
            goals.player2
            if goals.player1.discord_id == self.user.discord_id
            else goals.player1
        )
        embed = discord.Embed(
            title=translate(
                "profile_title",
                self.user.language,
                username=interaction.user.display_name,
            ),
            color=settings.default_embed_color,
        )

        embed.description = (
            f"**Ⅲ {translate('player_settings', self.user.language)}**\n"
            f"\u200b **⋄ {translate('privacy_policy', self.user.language)}:** "
            f"{translate(friend.privacy_policy.name.lower(), self.user.language)}\n"
            f"\u200b **⋄ {translate('donation_policy', self.user.language)}:** "
            f"{translate(friend.donation_policy.name.lower(), self.user.language)}\n"
            f"\u200b **⋄ {translate('language_selected', self.user.language)}:** {LANGUAGE_MAP[friend.language]}\n\n"
            f"**Ⅲ {translate('player_info', self.user.language)}**\n"
            f"\u200b **⋄ {translate('cars_collected', self.user.language)}:** {await friend.cars.filter().count()}\n"
            f"\u200b **⋄ {translate('rebirths_done', self.user.language)}:** {friend.rebirths}\n"
            f"\u200b **⋄ {translate('bolts_acquired', self.user.language)}:** {friend.bolts}\n"
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class FriendSource(Select):
    def __init__(self, friends: List[Friendship], user: Player):
        self.user = user
        options = []
        for friend in friends:
            friend_player = (
                friend.player2
                if friend.player1.discord_id == user.discord_id
                else friend.player1
            )
            options.append(
                discord.SelectOption(
                    label=f"{friend_player.discord_id}",
                    description=f"{'Bestie ' if friend.bestie else ''}Since {friend.since.strftime('%Y-%m-%d')}",
                    value=str(friend.id),
                )
            )
        super().__init__(
            placeholder="Choose a friend...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        friendship_id = int(self.values[0])
        friendship = await Friendship.get(id=friendship_id).prefetch_related(
            "player1", "player2"
        )
        friend = (
            friendship.player2
            if friendship.player1.discord_id == self.user.discord_id
            else friendship.player1
        )
        embed = discord.Embed(
            title=translate(
                "profile_title",
                self.user.language,
                username=interaction.user.display_name,
            ),
            color=settings.default_embed_color,
        )

        embed.description = (
            f"**Ⅲ {translate('player_settings', self.user.language)}**\n"
            f"\u200b **⋄ {translate('privacy_policy', self.user.language)}:** "
            f"{translate(friend.privacy_policy.name.lower(), self.user.language)}\n"
            f"\u200b **⋄ {translate('donation_policy', self.user.language)}:** "
            f"{translate(friend.donation_policy.name.lower(), self.user.language)}\n"
            f"\u200b **⋄ {translate('language_selected', self.user.language)}:** {LANGUAGE_MAP[friend.language]}\n\n"
            f"**Ⅲ {translate('player_info', self.user.language)}**\n"
            f"\u200b **⋄ {translate('cars_collected', self.user.language)}:** {await friend.cars.filter().count()}\n"
            f"\u200b **⋄ {translate('rebirths_done', self.user.language)}:** {friend.rebirths}\n"
            f"\u200b **⋄ {translate('bolts_acquired', self.user.language)}:** {friend.bolts}\n"
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class FriendSelector(View):
    def __init__(self, friends: List[Friendship], user: Player, request: str):
        super().__init__()
        match request:
            case "profiles":
                self.add_item(FriendSource(friends, user))
            case "goals":
                self.add_item(FriendSource(friends, user))


async def _get_10_cars_emojis(self) -> list[discord.Emoji]:
    """
    Return a list of up to 10 Discord emojis representing cars.
    """
    cars: list[Car] = random.choices(
        [x for x in carfigures.values() if x.enabled], k=min(10, len(carfigures))
    )
    emotes: list[discord.Emoji] = []
    for car in cars:
        if emoji := self.bot.get_emoji(car.emoji_id):
            emotes.append(emoji)
    return emotes
