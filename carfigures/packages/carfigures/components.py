from __future__ import annotations

import logging
import math
import random
from typing import TYPE_CHECKING, cast

import discord
from discord.ui import Button, Modal, TextInput, View
from tortoise.timezone import now as datetime_now

from carfigures.core.metrics import caught_cars
from carfigures.core.models import CarInstance, Player, events, exclusives
from carfigures.settings import appearance, settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot
    from carfigures.core.models import Event, Exclusive
    from carfigures.packages.carfigures.carfigure import CarFigure

log = logging.getLogger("carfigures.packages.carfigures.components")


class CarFigureNamePrompt(Modal):
    name = TextInput(
        label=f"Name of this {appearance.collectible_singular}",
        style=discord.TextStyle.short,
        placeholder="Your guess",
    )

    def __init__(self, car: "CarFigure", button: CatchButton):
        super().__init__(title=f"Catch this {appearance.collectible_singular}!")
        self.car = car
        self.button = button

    async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None:
        log.exception("An error occurred in carfigure catching prompt", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(
                f"An error occurred with this {appearance.collectible_singular}."
            )
        else:
            await interaction.response.send_message(
                f"An error occurred with this {appearance.collectible_singular}."
            )

    async def on_submit(self, interaction: discord.Interaction["CarFiguresBot"]):
        # TODO: use lock
        await interaction.response.defer(thinking=True)
        if self.car.caught:
            await interaction.followup.send(f"{interaction.user.mention} I was caught already!")
            return
        if self.car.model.catchNames:
            possible_names = (
                self.car.name.lower(),
                *self.car.model.catchNames.split(";"),
            )
        else:
            possible_names = (self.car.name.lower(),)
        if self.name.value.lower().strip() in possible_names:
            self.car.caught = True
            car, has_caught_before = await self.catch_car(
                interaction.client, cast(discord.Member, interaction.user)
            )

            event = ""
            if car.exclusive_card and car.exclusive_card.catchPhrase:
                event += f"*{car.exclusive_card.catchPhrase}*\n"
            if car.event_card and car.event_card.catchPhrase:
                event += f"*{car.event_card.catchPhrase}*\n"
            if has_caught_before:
                event += f"This is a **new {appearance.collectible_singular}** that has been added to your {appearance.garage_name}!"

            await interaction.followup.send(
                f"{interaction.user.mention} You caught **{self.car.name}!** "
                + f"`(#{car.pk:0X}, {car.horsepowerBonus:+}%/{car.weightBonus:+}%)`\n\n"
                + f"{event}"
            )
            self.button.disabled = True
            await interaction.followup.edit_message(self.car.message.id, view=self.button.view)
        else:
            wrong_message = random.choices(
                population=[message["message"] for message in settings.wrong_name_messages],
                weights=[float(message["rarity"]) for message in settings.wrong_name_messages],
                k=1,
            )[0]
            await interaction.followup.send(f"{interaction.user.mention} " + wrong_message)

    async def catch_car(
        self, bot: "CarFiguresBot", user: discord.Member
    ) -> tuple[CarInstance, bool]:
        player, _ = await Player.get_or_create(discord_id=user.id)

        event: "Event | None" = None
        exclusive: "Exclusive | None" = None
        chance = random.randint(1, 2048) == 1
        exclusive_population = [
            exclusive
            for exclusive in exclusives.values()
            if exclusive.rebirthRequired <= player.rebirths
        ]
        event_population = [
            event
            for event in events.values()
            if event.startDate <= datetime_now() <= event.endDate
        ]

        if chance and exclusive_population:
            common_weight = sum(1 - exclusive.rarity for exclusive in exclusive_population)
            weights = [exclusive.rarity for exclusive in exclusive_population] + [common_weight]
            exclusive = random.choices(
                population=exclusive_population + [None], weights=weights, k=1
            )[0]

        if event_population:
            # Here we try to determine what should be the chance of having a common card
            # since the rarity field is a value between 0 and 1, 1 being no common
            # and 0 only common, we get the remaining value by doing (1-rarity)
            # We then sum each value for each current event, and we should get an algorithm
            # that kinda makes sense.
            common_weight = sum(1 - event.rarity for event in event_population)

            weights = [event.rarity for event in event_population] + [common_weight]
            # None is added representing the common carfigure
            event = random.choices(population=event_population + [None], weights=weights, k=1)[0]

        is_new = not await CarInstance.filter(player=player, car=self.car.model).exists()
        car = await CarInstance.create(
            car=self.car.model,
            player=player,
            exclusive=exclusive,
            event=event,
            horsepowerBonus=random.randint(*settings.catch_bonus_rate),
            weightBonus=random.randint(*settings.catch_bonus_rate),
            server=user.guild.id,
            spawnedTime=self.car.time,
        )
        if user.guild.member_count:
            caught_cars.labels(
                fullName=self.car.model.fullName,
                exclusive=exclusive,
                event=event,
                # observe the size of the server, rounded to the nearest power of 10
                guild_size=10 ** math.ceil(math.log(max(user.guild.member_count - 1, 1), 10)),
            ).inc()
        return car, is_new


class CatchButton(Button):
    def __init__(self, car: "CarFigure"):
        catch_button_message = random.choices(
            population=[message["message"] for message in settings.catch_button_messages],
            weights=[float(message["rarity"]) for message in settings.catch_button_messages],
            k=1,
        )[0]
        super().__init__(style=discord.ButtonStyle.primary, label=catch_button_message)
        self.car = car

    async def callback(self, interaction: discord.Interaction):
        if self.car.caught:
            await interaction.response.send_message("I was caught already!", ephemeral=True)
        else:
            await interaction.response.send_modal(CarFigureNamePrompt(self.car, self))


class CatchView(View):
    def __init__(self, car: "CarFigure"):
        super().__init__()
        self.car = car
        self.button = CatchButton(car)
        self.add_item(self.button)

    async def interaction_check(
        self, interaction: discord.Interaction["CarFiguresBot"], /
    ) -> bool:
        return await interaction.client.blacklist_check(interaction)

    async def on_timeout(self):
        self.button.disabled = True
        if self.car.message:
            try:
                await self.car.message.edit(view=self)
            except discord.HTTPException:
                pass
