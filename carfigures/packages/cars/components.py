from __future__ import annotations

from typing import TYPE_CHECKING, Union, List
import enum

import discord
from discord.ui import Button, View, button

from carfigures.core.models import (
    CarInstance,
    Player,
    Trade,
    TradeObject,
    PrivacyPolicy,
)
from carfigures.core.utils import menus
from carfigures.core.utils.paginator import Pages

from carfigures.settings import settings, appearance

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


class DonationRequest(View):
    def __init__(
        self,
        bot: "CarFiguresBot",
        interaction: discord.Interaction,
        carfigure: CarInstance,
        new_player: Player,
    ):
        super().__init__(timeout=120)
        self.bot = bot
        self.original_interaction = interaction
        self.carfigure = carfigure
        self.new_player = new_player

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user.id != self.new_player.discord_id:
            await interaction.response.send_message(
                "You are not allowed to interact with this menu.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.original_interaction.followup.edit_message(
                "@original",
                view=self,  # type: ignore
            )
        except discord.NotFound:
            pass
        await self.carfigure.unlock()

    @button(
        style=discord.ButtonStyle.success,
        emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}",
    )
    async def accept(self, interaction: discord.Interaction, button: Button):
        self.stop()
        for item in self.children:
            item.disabled = True  # type: ignore
        self.carfigure.favorite = False
        self.carfigure.trade_player = self.carfigure.player
        self.carfigure.player = self.new_player
        await self.carfigure.save()
        trade = await Trade.create(user1=self.carfigure.trade_player, user2=self.new_player)
        await TradeObject.create(
            trade=trade, carinstance=self.carfigure, player=self.carfigure.trade_player
        )
        await interaction.response.edit_message(
            content=interaction.message.content  # type: ignore
            + "\n\N{WHITE HEAVY CHECK MARK} The donation was accepted!",
            view=self,
        )
        await self.carfigure.unlock()

    @button(
        style=discord.ButtonStyle.danger,
        emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
    )
    async def deny(self, interaction: discord.Interaction, button: Button):
        self.stop()
        for item in self.children:
            item.disabled = True  # type: ignore
        await interaction.response.edit_message(
            content=interaction.message.content  # type: ignore
            + "\n\N{CROSS MARK} The donation was denied.",
            view=self,
        )
        await self.carfigure.unlock()


class SortingChoices(enum.Enum):
    alphabetic = "car__fullName"
    catchDate = "-catchDate"
    rarity = "car__rarity"
    event = "event__id"
    favorite = "-favorite"
    exclusive = "exclusive__id"
    weight = "weight"
    horsepower = "horsepower"
    weightBonus = "-weightBonus"
    horsepowerBonus = "-horsepowerBonus"
    statsBonus = "stats"
    totalStats = "total_stats"

    # manual sorts are not sorted by SQL queries but by our code
    # this may be do-able with SQL still, but I don't have much experience ngl
    duplicates = "manualsort-duplicates"


class CarFiguresSource(menus.ListPageSource):
    def __init__(self, entries: List[CarInstance]):
        super().__init__(entries, per_page=25)

    async def format_page(self, menu: CarFiguresSelector, cars: List[CarInstance]):
        menu.set_options(cars)
        return True  # signal to edit the page


class CarFiguresSelector(Pages):
    def __init__(self, interaction: discord.Interaction["CarFiguresBot"], cars: List[CarInstance]):
        self.bot = interaction.client
        source = CarFiguresSource(cars)
        super().__init__(source, interaction=interaction)
        self.add_item(self.select_car_menu)

    def set_options(self, cars: List[CarInstance]):
        options: List[discord.SelectOption] = []
        for car in cars:
            emoji = self.bot.get_emoji(int(car.carfigure.emoji))
            favorite = "❤️ " if car.favorite else ""
            exclusive = car.exclusiveEmoji(self.bot, True)
            event = car.eventEmoji(self.bot, True)
            options.append(
                discord.SelectOption(
                    label=f"{favorite}{exclusive}{event}#{car.pk:0X} {car.carfigure.fullName}",
                    description=f"{appearance.hp}: {car.horsepowerBonus:+d}% • {appearance.kg}: {car.weightBonus:+d}% • "
                    f"Caught on {car.catchDate.strftime('%d/%m/%y %H:%M')}",
                    emoji=emoji,
                    value=f"{car.pk}",
                )
            )
        self.select_car_menu.options = options

    @discord.ui.select()
    async def select_car_menu(self, interaction: discord.Interaction, item: discord.ui.Select):
        await interaction.response.defer(thinking=True)
        car_instance = await CarInstance.get(
            id=int(interaction.data.get("values")[0])  # type: ignore
        )
        await self.car_selected(interaction, car_instance)

    async def car_selected(self, interaction: discord.Interaction, car_instance: CarInstance):
        raise NotImplementedError()


class CarFiguresViewer(CarFiguresSelector):
    async def car_selected(self, interaction: discord.Interaction, instance: CarInstance):
        content, file = await instance.prepareForMessage(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()


async def inventory_privacy(
    bot: "CarFiguresBot",
    interaction: discord.Interaction,
    player: Player,
    player_obj: Union[discord.User, discord.Member],
):
    if interaction.guild and interaction.guild.id in settings.superGuilds:
        roles = settings.superUsers
        if any(role.id in roles for role in interaction.user.roles):  # type: ignore
            return True
    match player.privacyPolicy:
        case PrivacyPolicy.ALLOW:
            return True
        case PrivacyPolicy.DENY:
            if interaction.user.id != player_obj.id:
                await interaction.followup.send(
                    "This user has set their inventory to private.", ephemeral=True
                )
                return False
            else:
                return True
        case PrivacyPolicy.SAME_SERVER:
            if not bot.intents.members:
                await interaction.followup.send(
                    "This user has their policy set to `Same Server`, "
                    "however I do not have the `members` intent to check this.",
                    ephemeral=True,
                )
                return False
            elif interaction.guild is None:
                await interaction.followup.send(
                    "This user has set their inventory to private.", ephemeral=True
                )
                return False
            elif interaction.guild.get_member(player_obj.id) is None:
                await interaction.followup.send("This user is not in the server.", ephemeral=True)
                return False
            else:
                return True
