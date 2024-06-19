from __future__ import annotations

import logging
import math
import random
from typing import TYPE_CHECKING, cast

import discord
from discord.ui import Button, Modal, TextInput, View
from prometheus_client import Counter
from tortoise.timezone import now as datetime_now

from carfigures.core.models import CarInstance, Player, events
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot
    from carfigures.core.models import Event
    from carfigures.packages.carfigures.carfigure import CarFigure

log = logging.getLogger("carfigures.packages.carfigures.components")
caught_cars = Counter(
    "caught_cf", "Caught carfigures", ["full_name", "limited", "event", "guild_size"]
)


class CarFigureNamePrompt(Modal, title="Catch this Entity!"):
    name = TextInput(
        label="Name of this Entity",
        style=discord.TextStyle.short,
        placeholder="Your guess",
    )

    def __init__(self, car: "CarFigure", button: CatchButton):
        super().__init__()
        self.car = car
        self.button = button

    async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None:
        log.exception("An error occurred in carfigure catching prompt", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(
                f"An error occurred with this {settings.collectible_name}."
            )
        else:
            await interaction.response.send_message(
                f"An error occurred with this {settings.collectible_name}."
            )

    async def on_submit(self, interaction: discord.Interaction["CarFiguresBot"]):
        # TODO: use lock
        if self.car.caught:
            await interaction.response.send_message(
                f"{interaction.user.mention} I was caught already!"
            )
            return
        if self.car.model.catch_names:
            possible_names = (self.car.name.lower(), *self.car.model.catch_names.split(";"))
        else:
            possible_names = (self.car.name.lower(),)
        if self.name.value.lower().strip() in possible_names:
            self.car.caught = True
            await interaction.response.defer(thinking=True)
            car, has_caught_before = await self.catch_car(
                interaction.client, cast(discord.Member, interaction.user)
            )

            event = ""
            if car.limited:
                event += f"💠 ***Its a Limited Edition {settings.collectible_name}!!!*** 💠\n"
            if car.eventcard and car.eventcard.catch_phrase:
                event += f"*{car.eventcard.catch_phrase}*\n"
            if has_caught_before:
                name = settings.command_names["garage"]
                event += (
                    f"This is a **new {settings.collectible_name}** "
                    f"that has been added to your {name}!"
                )

            await interaction.followup.send(
                f"{interaction.user.mention} You caught **{self.car.name}!** "
                f"`(#{car.pk:0X}, {car.horsepower_bonus:+}%/{car.weight_bonus:+}%)`\n\n"
                f"{event}"
            )
            self.button.disabled = True
            await interaction.followup.edit_message(self.car.message.id, view=self.button.view)
        else:
            await interaction.response.send_message(f"{interaction.user.mention} Wrong name!")

    async def catch_car(
        self, bot: "CarFiguresBot", user: discord.Member
    ) -> tuple[CarInstance, bool]:
        player, created = await Player.get_or_create(discord_id=user.id)

        # stat may vary by +/- 50% of base stat
        bonus_horsepower = random.randint(-50, 50)
        bonus_weight = random.randint(-50, 50)
        limited = random.randint(1, 2048) == 1

        # check if we can spawn cards with the event card
        event: "Event | None" = None
        population = [x for x in events.values() if x.start_date <= datetime_now() <= x.end_date]
        if not limited and population:
            # Here we try to determine what should be the chance of having a common card
            # since the rarity field is a value between 0 and 1, 1 being no common
            # and 0 only common, we get the remaining value by doing (1-rarity)
            # We then sum each value for each current event, and we should get an algorithm
            # that kinda makes sense.
            common_weight = sum(1 - x.rarity for x in population)

            weights = [x.rarity for x in population] + [common_weight]
            # None is added representing the common carfigure
            event = random.choices(population=population + [None], weights=weights, k=1)[0]

        is_new = not await CarInstance.filter(player=player, car=self.car.model).exists()
        car = await CarInstance.create(
            car=self.car.model,
            player=player,
            limited=limited,
            event=event,
            horsepower_bonus=bonus_horsepower,
            weight_bonus=bonus_weight,
            server_id=user.guild.id,
            spawned_time=self.car.time
        )
        if user.id in bot.catch_log:
            log.info(
                f"{user} caught {settings.collectible_name}"
                f" {self.car.model}, {limited=} {event=}",
            )
        else:
            log.debug(
                f"{user} caught {settings.collectible_name}"
                f" {self.car.model}, {limited=} {event=}",
            )
        if user.guild.member_count:
            caught_cars.labels(
                full_name=self.car.model.full_name,
                limited=limited,
                event=event,
                # observe the size of the server, rounded to the nearest power of 10
                guild_size=10 ** math.ceil(math.log(max(user.guild.member_count - 1, 1), 10)),
            ).inc()
        return car, is_new


class CatchButton(Button):
    def __init__(self, car: "CarFigure"):
        super().__init__(style=discord.ButtonStyle.primary, label="Catch me!")
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

    async def interaction_check(self, interaction: discord.Interaction["CarFiguresBot"], /) -> bool:
        return await interaction.client.blacklist_check(interaction)

    async def on_timeout(self):
        self.button.disabled = True
        if self.car.message:
            try:
                await self.car.message.edit(view=self)
            except discord.HTTPException:
                pass
