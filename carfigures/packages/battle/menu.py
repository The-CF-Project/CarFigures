from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast

import discord
from discord.ui import Button, View, button

from ballsdex.core.models import BallInstance
from ballsdex.core.models import Trade as Battle
from ballsdex.core.models import TradeObject as BattleObject
from ballsdex.packages.battle.display import fill_battle_embed_fields
from ballsdex.packages.battle.battle_user import BattlingUser
from ballsdex.settings import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
    from ballsdex.packages.battle.cog import Battle as BattleCog

log = logging.getLogger("ballsdex.packages.battle.menu")


class InvalidBattleOperation(Exception):
    pass


class BattleView(View):
    def __init__(self, battle: BattleMenu):
        super().__init__(timeout=60 * 30)
        self.battle = battle

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        try:
            self.battle._get_battler(interaction.user)
        except RuntimeError:
            await interaction.response.send_message(
                "You are not allowed to interact with this battle.", ephemeral=True
            )
            return False
        else:
            return True

    @button(label="Lock proposal", emoji="\N{LOCK}", style=discord.ButtonStyle.primary)
    async def lock(self, interaction: discord.Interaction, button: Button):
        battler = self.battle._get_battler(interaction.user)
        if battler.locked:
            await interaction.response.send_message(
                "You have already locked your proposal!", ephemeral=True
            )
            return
        await self.battle.lock(battler)
        if self.battle.battler1.locked and self.battle.battler2.locked:
            await interaction.response.send_message(
                "Your proposal has been locked. Now confirm again to end the battle.",
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
        battler = self.battle._get_battler(interaction.user)
        if battler.locked:
            await interaction.response.send_message(
                "You have locked your proposal, it cannot be edited! "
                "You can click the cancel button to stop the battle instead.",
                ephemeral=True,
            )
        else:
            for countryball in battler.proposal:
                await countryball.unlock()
            battler.proposal.clear()
            await interaction.response.send_message("Proposal cleared.", ephemeral=True)

    @button(
        label="Cancel Battle",
        emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
        style=discord.ButtonStyle.danger,
    )
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await self.battle.user_cancel(self.battle._get_battler(interaction.user))
        await interaction.response.send_message("Battle has been cancelled.", ephemeral=True)


class ConfirmView(View):
    def __init__(self, battle: BattleMenu):
        super().__init__(timeout=90)
        self.battle = battle

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        try:
            self.battle._get_battler(interaction.user)
        except RuntimeError:
            await interaction.response.send_message(
                "You are not allowed to interact with this battle.", ephemeral=True
            )
            return False
        else:
            return True

    @discord.ui.button(
        style=discord.ButtonStyle.success, emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}"
    )
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        battler = self.battle._get_battler(interaction.user)
        if battler.accepted:
            await interaction.response.send_message(
                "You have already accepted this battle.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.battle.confirm(battler)
        if self.battle.battler1.accepted and self.battle.battler2.accepted:
            if result:
                await interaction.followup.send("The battle is now concluded.", ephemeral=True)
            else:
                await interaction.followup.send(
                    ":warning: An error occurred while concluding the battle.", ephemeral=True
                )
        else:
            await interaction.followup.send(
                "You have accepted the battle, waiting for the other user...", ephemeral=True
            )

    @discord.ui.button(
        style=discord.ButtonStyle.danger,
        emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
    )
    async def deny_button(self, interaction: discord.Interaction, button: Button):
        await self.battle.user_cancel(self.battle._get_battler(interaction.user))
        await interaction.response.send_message("Battle has been cancelled.", ephemeral=True)


class BattleMenu:
    def __init__(
        self,
        cog: BattleCog,
        interaction: discord.Interaction["BallsDexBot"],
        battler1: BattlingUser,
        battler2: BattlingUser,
    ):
        self.cog = cog
        self.bot = interaction.client
        self.channel: discord.TextChannel = cast(discord.TextChannel, interaction.channel)
        self.battler1 = battler1
        self.battler2 = battler2
        self.embed = discord.Embed()
        self.task: asyncio.Task | None = None
        self.current_view: BattleView | ConfirmView = BattleView(self)
        self.message: discord.Message

    def _get_battler(self, user: discord.User | discord.Member) -> BattlingUser:
        if user.id == self.battler1.user.id:
            return self.battler1
        elif user.id == self.battler2.user.id:
            return self.battler2
        raise RuntimeError(f"User with ID {user.id} cannot be found in the battle")

    def _generate_embed(self):
        add_command = self.cog.add.extras.get("mention", "`/battle add`")
        remove_command = self.cog.remove.extras.get("mention", "`/battle remove`")

        self.embed.title = f"{settings.collectible_name.title()}s trading"
        self.embed.color = discord.Colour.blurple()
        self.embed.description = (
            f"Add or remove {settings.collectible_name}s you want to propose to the other player "
            f"using the {add_command} and {remove_command} commands.\n"
            "Once you're finished, click the lock button below to confirm your proposal.\n"
            "You can also lock with nothing if you're receiving a gift.\n\n"
            "*You have 30 minutes before this interaction ends.*"
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
        start_time = datetime.utcnow()

        while True:
            await asyncio.sleep(15)
            if datetime.utcnow() - start_time > timedelta(minutes=15):
                self.embed.colour = discord.Colour.dark_red()
                await self.cancel("The battle timed out")
                return

            try:
                fill_battle_embed_fields(self.embed, self.bot, self.battler1, self.battler2)
                await self.message.edit(embed=self.embed)
            except Exception:
                log.exception(
                    "Failed to refresh the battle menu "
                    f"guild={self.message.guild.id} "  # type: ignore
                    f"battler1={self.battler1.user.id} battler2={self.battler2.user.id}"
                )
                self.embed.colour = discord.Colour.dark_red()
                await self.cancel("The battle timed out")
                return

    async def start(self):
        """
        Start the battle by sending the initial message and opening up the proposals.
        """
        self._generate_embed()
        fill_battle_embed_fields(self.embed, self.bot, self.battler1, self.battler2)
        self.message = await self.channel.send(
            content=f"Hey {self.battler2.user.mention}, {self.battler1.user.name} "
            "is proposing a battle with you!",
            embed=self.embed,
            view=self.current_view,
        )
        self.task = self.bot.loop.create_task(self.update_message_loop())

    async def cancel(self, reason: str = "The battle has been cancelled."):
        """
        Cancel the battle immediately.
        """
        if self.task:
            self.task.cancel()

        for countryball in self.battler1.proposal + self.battler2.proposal:
            await countryball.unlock()

        self.current_view.stop()
        for item in self.current_view.children:
            item.disabled = True  # type: ignore

        fill_battle_embed_fields(self.embed, self.bot, self.battler1, self.battler2)
        self.embed.description = f"**{reason}**"
        await self.message.edit(content=None, embed=self.embed, view=self.current_view)

    async def lock(self, battler: BattlingUser):
        """
        Mark a user's proposal as locked, ready for next stage
        """
        battler.locked = True
        if self.battler1.locked and self.battler2.locked:
            if self.task:
                self.task.cancel()
            self.current_view.stop()
            fill_battle_embed_fields(self.embed, self.bot, self.battler1, self.battler2)

            self.embed.colour = discord.Colour.yellow()
            self.embed.description = (
                "Both users locked their propositions! Now confirm to conclude this battle."
            )
            self.current_view = ConfirmView(self)
            await self.message.edit(content=None, embed=self.embed, view=self.current_view)

    async def user_cancel(self, battler: BattlingUser):
        """
        Register a user request to cancel the battle
        """
        battler.cancelled = True
        self.embed.colour = discord.Colour.red()
        await self.cancel()

    async def confirm(self, battler: BattlingUser) -> bool:
        """
        Mark a user's proposal as accepted. If both user accept, end the battle now

        If the battle is concluded, return True, otherwise if an error occurs, return False
        """
        for countryball in self.battler1.proposal:
            chealth1 = countryball.health
            health1 = health1 + chealth1
            cattack1 = countryball.attack
            attack1 = attack1 + cattack1

        for countryball in self.battler2.proposal:
            chealth2 = countryball.health
            health2 = health2 + chealth2
            cattack2 = countryball.attack
            attack2 = attack2 + cattack2
        
        worl1 = health1/attack2
        worl2 = health2/attack1

        if worl1 > worl2:
            winner = self.battler1
        elif worl2 > worl1:
            winner = self.battler2
        elif worl1==worl2:
            winner = None
        else:
            error = "An error occured!"

        result = True
        battler.accepted = True
        fill_battle_embed_fields(self.embed, self.bot, self.battler1, self.battler2)
        if self.battler1.accepted and self.battler2.accepted:
            if self.task and not self.task.cancelled():
                # shouldn't happen but just in case
                self.task.cancel()

            self.embed.description = f"Battle concluded! Winner : {winner}"
            self.embed.colour = discord.Colour.green()
            self.current_view.stop()
            for item in self.current_view.children:
                item.disabled = True  # type: ignore
        await self.message.edit(content=None, embed=self.embed, view=self.current_view)
        return result
