from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, cast

import discord
from discord.ui import Button, View, button

from carfigures.core.models import CarInstance, Trade, TradeObject
from carfigures.packages.trade.display import fill_trade_embed_fields
from carfigures.packages.trade.trade_user import TradingUser
from carfigures.settings import settings, appearance

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot
    from carfigures.packages.trade.cog import Trade as TradeCog

log = logging.getLogger("carfigures.packages.trade.menu")


class InvalidTradeOperation(Exception):
    pass


class TradeView(View):
    def __init__(self, trade: TradeMenu):
        super().__init__(timeout=60 * 30)
        self.trade = trade

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        try:
            self.trade._get_trader(interaction.user)
        except RuntimeError:
            await interaction.response.send_message(
                "You are not allowed to interact with this trade.", ephemeral=True
            )
            return False
        else:
            return True

    @button(label="Lock proposal", emoji="\N{LOCK}", style=discord.ButtonStyle.primary)
    async def lock(self, interaction: discord.Interaction, button: Button):
        trader = self.trade._get_trader(interaction.user)
        if trader.locked:
            await interaction.response.send_message(
                "You have already locked your proposal!", ephemeral=True
            )
            return
        await self.trade.lock(trader)
        if self.trade.trader1.locked and self.trade.trader2.locked:
            await interaction.response.send_message(
                "Your proposal has been locked. Now confirm again to end the trade.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Your proposal has been locked. "
                "You can wait for the other user to lock their proposal.",
                ephemeral=True,
            )

    @button(label="Reset", emoji="\N{DASH SYMBOL}", style=discord.ButtonStyle.secondary)
    async def clear(self, interaction: discord.Interaction, button: Button):
        trader = self.trade._get_trader(interaction.user)
        if trader.locked:
            await interaction.response.send_message(
                "You have locked your proposal, it cannot be edited! "
                "You can click the cancel button to stop the trade instead.",
                ephemeral=True,
            )
        else:
            for carfigure in trader.proposal:
                await carfigure.unlock()
            trader.proposal.clear()
            await interaction.response.send_message("Proposal cleared.", ephemeral=True)

    @button(
        label="Cancel trade",
        emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
        style=discord.ButtonStyle.danger,
    )
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await self.trade.user_cancel(self.trade._get_trader(interaction.user))
        await interaction.response.send_message("Trade has been cancelled.", ephemeral=True)


class ConfirmView(View):
    def __init__(self, trade: TradeMenu):
        super().__init__(timeout=90)
        self.trade = trade

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        try:
            self.trade._get_trader(interaction.user)
        except RuntimeError:
            await interaction.response.send_message(
                "You are not allowed to interact with this trade.", ephemeral=True
            )
            return False
        else:
            return True

    @discord.ui.button(
        style=discord.ButtonStyle.success, emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}"
    )
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        trader = self.trade._get_trader(interaction.user)
        if trader.accepted:
            await interaction.response.send_message(
                "You have already accepted this trade.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.trade.confirm(trader)
        if self.trade.trader1.accepted and self.trade.trader2.accepted:
            if result:
                await interaction.followup.send("The trade is now concluded.", ephemeral=True)
            else:
                await interaction.followup.send(
                    ":warning: An error occurred while concluding the trade.", ephemeral=True
                )
        else:
            await interaction.followup.send(
                "You have accepted the trade, waiting for the other user...", ephemeral=True
            )

    @discord.ui.button(
        style=discord.ButtonStyle.danger,
        emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
    )
    async def deny_button(self, interaction: discord.Interaction, button: Button):
        await self.trade.user_cancel(self.trade._get_trader(interaction.user))
        await interaction.response.send_message("Trade has been cancelled.", ephemeral=True)


class TradeMenu:
    def __init__(
        self,
        cog: TradeCog,
        interaction: discord.Interaction["CarFiguresBot"],
        trader1: TradingUser,
        trader2: TradingUser,
    ):
        self.cog = cog
        self.bot = interaction.client
        self.channel: discord.TextChannel = cast(discord.TextChannel, interaction.channel)
        self.trader1 = trader1
        self.trader2 = trader2
        self.embed = discord.Embed()
        self.task: asyncio.Task | None = None
        self.current_view: TradeView | ConfirmView = TradeView(self)
        self.message: discord.Message
        self.end_time = math.ceil((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())

    def _get_trader(self, user: discord.User | discord.Member) -> TradingUser:
        if user.id == self.trader1.user.id:
            return self.trader1
        elif user.id == self.trader2.user.id:
            return self.trader2
        raise RuntimeError(f"User with ID {user.id} cannot be found in the trade")

    def _generate_embed(self):
        add_command = self.cog.add.extras.get("mention", "`/trade add`")
        remove_command = self.cog.remove.extras.get("mention", "`/trade remove`")
        timestamp = f"<t:{self.end_time}:R>"

        self.embed.title = f"{appearance.collectible_plural.title()} trading"
        self.embed.color = settings.default_embed_color
        self.embed.description = (
            f"Add or remove {appearance.collectible_plural} you want to propose to the other player "
            f"using the {add_command} and {remove_command} commands.\n"
            "Once you're finished, click the lock button below to confirm your proposal.\n"
            "You can also lock with nothing if you're receiving a gift.\n\n"
            f"*This interaction ends {timestamp}.*"
        )
        self.embed.set_footer(
            text="This message is updated every 15 seconds, "
            "but you can keep on editing your proposal."
        )

    async def update_message_loop(self):
        """
        A loop task that updates each 5 second the menu with the new content.
        """

        assert self.task
        start_time = datetime.now(timezone.utc)

        while True:
            await asyncio.sleep(15)
            if datetime.now(timezone.utc) - start_time > timedelta(minutes=15):
                self.embed.colour = discord.Colour.dark_red()
                await self.cancel("The trade timed out")
                return

            try:
                fill_trade_embed_fields(self.embed, self.bot, self.trader1, self.trader2)
                await self.message.edit(embed=self.embed)
            except Exception:
                log.exception(
                    "Failed to refresh the trade menu "
                    f"guild={self.message.guild.id} "  # type: ignore
                    f"trader1={self.trader1.user.id} trader2={self.trader2.user.id}"
                )
                self.embed.colour = discord.Colour.dark_red()
                await self.cancel("The trade timed out")
                return

    async def start(self):
        """
        Start the trade by sending the initial message and opening up the proposals.
        """
        self._generate_embed()
        fill_trade_embed_fields(self.embed, self.bot, self.trader1, self.trader2)
        self.message = await self.channel.send(
            content=f"Hey {self.trader2.user.mention}, {self.trader1.user.name} "
            "is proposing a trade with you!",
            embed=self.embed,
            view=self.current_view,
        )
        self.task = self.bot.loop.create_task(self.update_message_loop())

    async def cancel(self, reason: str = "The trade has been cancelled."):
        """
        Cancel the trade immediately.
        """
        if self.task:
            self.task.cancel()

        for carfigure in self.trader1.proposal + self.trader2.proposal:
            await carfigure.unlock()

        self.current_view.stop()
        for item in self.current_view.children:
            item.disabled = True  # type: ignore

        fill_trade_embed_fields(self.embed, self.bot, self.trader1, self.trader2)
        self.embed.description = f"**{reason}**"
        await self.message.edit(content=None, embed=self.embed, view=self.current_view)

    async def lock(self, trader: TradingUser):
        """
        Mark a user's proposal as locked, ready for next stage
        """
        trader.locked = True
        if self.trader1.locked and self.trader2.locked:
            if self.task:
                self.task.cancel()
            self.current_view.stop()
            fill_trade_embed_fields(self.embed, self.bot, self.trader1, self.trader2)

            self.embed.colour = discord.Colour.yellow()
            self.embed.description = (
                "Both users locked their propositions! Now confirm to conclude this trade."
            )
            self.current_view = ConfirmView(self)
            await self.message.edit(content=None, embed=self.embed, view=self.current_view)

    async def user_cancel(self, trader: TradingUser):
        """
        Register a user request to cancel the trade
        """
        trader.cancelled = True
        self.embed.colour = discord.Colour.red()
        await self.cancel()

    async def perform_trade(self):
        valid_transferable_carfigures: list[CarInstance] = []

        trade = await Trade.create(player1=self.trader1.player, player2=self.trader2.player)

        for carfigure in self.trader1.proposal:
            await carfigure.refresh_from_db()
            if carfigure.player.discord_id != self.trader1.player.discord_id:
                # This is a invalid mutation, the player is not the owner of the carfigure
                raise InvalidTradeOperation()
            carfigure.player = self.trader2.player
            carfigure.trade_player = self.trader1.player
            carfigure.favorite = False
            valid_transferable_carfigures.append(carfigure)
            await TradeObject.create(
                trade=trade, carinstance=carfigure, player=self.trader1.player
            )

        for carfigure in self.trader2.proposal:
            if carfigure.player.discord_id != self.trader2.player.discord_id:
                # This is a invalid mutation, the player is not the owner of the carfigure
                raise InvalidTradeOperation()
            carfigure.player = self.trader1.player
            carfigure.trade_player = self.trader2.player
            carfigure.favorite = False
            valid_transferable_carfigures.append(carfigure)
            await TradeObject.create(
                trade=trade, carinstance=carfigure, player=self.trader2.player
            )

        for carfigure in valid_transferable_carfigures:
            await carfigure.unlock()
            await carfigure.save()

    async def confirm(self, trader: TradingUser) -> bool:
        """
        Mark a user's proposal as accepted. If both user accept, end the trade now

        If the trade is concluded, return True, otherwise if an error occurs, return False
        """
        result = True
        trader.accepted = True
        fill_trade_embed_fields(self.embed, self.bot, self.trader1, self.trader2)
        if self.trader1.accepted and self.trader2.accepted:
            if self.task and not self.task.cancelled():
                # shouldn't happen but just in case
                self.task.cancel()

            self.embed.description = "Trade concluded!"
            self.embed.colour = discord.Colour.green()
            self.current_view.stop()
            for item in self.current_view.children:
                item.disabled = True  # type: ignore

            try:
                await self.perform_trade()
            except InvalidTradeOperation:
                log.warning(f"Illegal trade operation between {self.trader1=} and {self.trader2=}")
                self.embed.description = (
                    f":warning: An attempt to modify the {appearance.collectible_singular} "
                    "during the trade was detected and the trade was cancelled."
                )
                self.embed.colour = discord.Colour.red()
                result = False
            except Exception:
                log.exception(f"Failed to conclude trade {self.trader1=} {self.trader2=}")
                self.embed.description = "An error occurred when concluding the trade."
                self.embed.colour = discord.Colour.red()
                result = False

        await self.message.edit(content=None, embed=self.embed, view=self.current_view)
        return result
