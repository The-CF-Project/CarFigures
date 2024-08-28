from __future__ import annotations
from typing import List

import random
import discord
from discord.ui import Button, View, Select, button

from carfigures.core.models import (
    Friendship,
    GuildConfig,
    Car,
    cars as carfigures,
)
from carfigures.configs import settings, information, appearance


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
        config.spawn_channel = self.channel.id  # type: ignore
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
                    view=self,  # type: ignore
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
                    view=self,  # type: ignore
                )
            except discord.HTTPException:
                pass


class FriendSelector(View):
    def __init__(self, friends: List[Friendship]):
        super().__init__()
        self.add_item(FriendSource(friends))


class FriendSource(Select):
    def __init__(self, friends: List[Friendship]):
        options = [
            discord.SelectOption(
                label=f"{friend.player1}",
                description=f"{friend.pk}",
                value=str(friend.pk),
            )
            for friend in friends
        ]
        super().__init__(
            placeholder="Choose a topic...", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        topic_id = int(self.values[0])
        selected_topic = await Friendship.get(id=topic_id)
        embed = discord.Embed(
            title=f"☳ {settings.bot_name} Documentations",
            description=f"∴ {selected_topic.player1}",
            color=settings.default_embed_color,
        )
        embed.add_field(
            name=f"⋄ {selected_topic.bestie} | {selected_topic.since}",
            value=f"{selected_topic.id}",
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


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
