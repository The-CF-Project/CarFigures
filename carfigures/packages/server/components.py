from __future__ import annotations

import random
from typing import List, TYPE_CHECKING

import discord
from discord.ui import Button, View, button

from carfigures.core.models import GuildConfig, Car, cars as carfigures
from carfigures.settings import settings


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
                url=f"{settings.terms_of_service}",
            )
        )
        self.add_item(
            Button(
                style=discord.ButtonStyle.link,
                label="Privacy Policy",
                url=f"{settings.privacy_policy}",
            )
        )

    @button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}",
    )
    async def accept_button(self, interaction: discord.Interaction, item: discord.ui.Button):
        config, created = await GuildConfig.get_or_create(guild_id=interaction.guild_id)
        config.spawn_channel = self.channel.id  # type: ignore
        await config.save()
        interaction.client.dispatch(
            "carfigures_settings_change", interaction.guild, channel=self.channel
        )
        self.stop()
        await interaction.response.send_message(
            f"{settings.collectible_name.title()}s will start spawning as"
            " users talk unless the bot is disabled."
        )

        self.accept_button.disabled = True
        try:
            await self.original_interaction.followup.edit_message(
                "@original", view=self  # type: ignore
            )
        except discord.HTTPException:
            pass

    async def on_timeout(self) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.original_interaction.followup.edit_message(
                "@original", view=self  # type: ignore
            )
        except discord.HTTPException:
            pass


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
