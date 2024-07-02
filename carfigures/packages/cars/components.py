from __future__ import annotations

from typing import TYPE_CHECKING, Union, List
import enum

import discord
from discord.ui import Button, View, button

from carfigures.core.models import CarInstance, Player, Trade, TradeObject, PrivacyPolicy
from carfigures.core.utils import menus
from carfigures.core.utils.paginator import Pages

from carfigures.settings import settings
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
                "@original", view=self  # type: ignore
            )
        except discord.NotFound:
            pass
        await self.carfigure.unlock()

    @button(
        style=discord.ButtonStyle.success, emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}"
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
            trade=trade, carinstance=self.carfigure, player=self.carfigure.trade_player)
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
    alphabetic = "car__full_name"
    catch_date = "-catch_date"
    rarity = "car__rarity"
    event = "event__id"
    favorite = "-favorite"
    limited = "limited"
    weight = "weight"
    horsepower = "horsepower"
    weight_bonus = "-weight_bonus"
    horsepower_bonus = "-horsepower_bonus"
    stats_bonus = "stats"
    total_stats = "total_stats"

    # manual sorts are not sorted by SQL queries but by our code
    # this may be do-able with SQL still, but I don't have much experience ngl
    duplicates = "manualsort-duplicates"

class SortingChoices2(enum.Enum):
    alphabetic = "event__name"
    expired = "expired"
    running = "running"
    newest = "newest"
    oldest = "oldest"


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
            emoji = self.bot.get_emoji(int(car.carfigure.emoji_id))
            favorite = "❤️ " if car.favorite else ""
            limited = "💠 " if car.limited else ""
            event = car.event_emoji(self.bot, True)
            options.append(
                discord.SelectOption(
                    label=f"{favorite}{limited}{event}#{car.pk:0X} {car.carfigure.full_name}",
                    description=f"{settings.hp_replacement}: {car.horsepower_bonus:+d}% • {settings.kg_replacement}: {car.weight_bonus:+d}% • "
                    f"Caught on {car.catch_date.strftime('%d/%m/%y %H:%M')}",
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
    async def car_selected(self, interaction: discord.Interaction, car_instance: CarInstance):
        content, file = await car_instance.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()


async def inventory_privacy(
    bot: "CarFiguresBot",
    interaction: discord.Interaction,
    player: Player,
    player_obj: Union[discord.User, discord.Member],
):
    privacy_policy = player.privacy_policy
    if interaction.guild and interaction.guild.id in settings.superuser_guild_ids:
        roles = settings.superuser_role_ids + settings.root_role_ids
        if any(role.id in roles for role in interaction.user.roles):  # type: ignore
            return True
    if privacy_policy == PrivacyPolicy.DENY:
        if interaction.user.id != player_obj.id:
            await interaction.followup.send(
                "This user has set their inventory to private.", ephemeral=True
            )
            return False
        else:
            return True
    elif privacy_policy == PrivacyPolicy.SAME_SERVER:
        if not bot.intents.members:
            await interaction.followup.send(
                "This user has their policy set to `Same Server`, "
                "however I do not have the `members` intent to check this.",
                ephemeral=True,
            )
            return False
        if interaction.guild is None:
            await interaction.followup.send(
                "This user has set their inventory to private.", ephemeral=True
            )
            return False
        elif interaction.guild.get_member(player_obj.id) is None:
            await interaction.followup.send("This user is not in the server.", ephemeral=True)
            return False
    return True
