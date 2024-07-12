import datetime
from collections import defaultdict
from typing import TYPE_CHECKING, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING
from tortoise.expressions import Q

from ballsdex.core.models import Player
from ballsdex.core.models import Trade as BattleModel
from ballsdex.core.utils.buttons import ConfirmChoiceView
from ballsdex.core.utils.paginator import Pages
from ballsdex.core.utils.transformers import (
    BallInstanceTransform,
    SpecialEnabledTransform,
)
from ballsdex.core.utils.transformers import TradeCommandType as BattleCommandType
from ballsdex.packages.battle.menu import BattleMenu
from ballsdex.packages.battle.battle_user import BattlingUser
from ballsdex.settings import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class Battle(commands.GroupCog):
    """
    Battle countryballs with other players.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.battles: dict[int, dict[int, list[BattleMenu]]] = defaultdict(lambda: defaultdict(list))

    def get_battle(
        self,
        interaction: discord.Interaction | None = None,
        *,
        channel: discord.TextChannel | None = None,
        user: discord.User | discord.Member = MISSING,
    ) -> tuple[BattleMenu, BattlingUser] | tuple[None, None]:
        """
        Find an ongoing battle for the given interaction.

        Parameters
        ----------
        interaction: discord.Interaction
            The current interaction, used for getting the guild, channel and author.

        Returns
        -------
        tuple[BattleMenu, BattlingUser] | tuple[None, None]
            A tuple with the `BattleMenu` and `BattlingUser` if found, else `None`.
        """
        guild: discord.Guild
        if interaction:
            guild = cast(discord.Guild, interaction.guild)
            channel = cast(discord.TextChannel, interaction.channel)
            user = interaction.user
        elif channel:
            guild = channel.guild
        else:
            raise TypeError("Missing interaction or channel")

        if guild.id not in self.battles:
            return (None, None)
        if channel.id not in self.battles[guild.id]:
            return (None, None)
        to_remove: list[BattleMenu] = []
        for battle in self.battles[guild.id][channel.id]:
            if (
                battle.current_view.is_finished()
                or battle.battler1.cancelled
                or battle.battler2.cancelled
            ):
                # remove what was supposed to have been removed
                to_remove.append(battle)
                continue
            try:
                battler = battle._get_battler(user)
            except RuntimeError:
                continue
            else:
                break
        else:
            for battle in to_remove:
                self.battles[guild.id][channel.id].remove(battle)
            return (None, None)

        for battle in to_remove:
            self.battles[guild.id][channel.id].remove(battle)
        return (battle, battler)

    @app_commands.command()
    async def begin(self, interaction: discord.Interaction["BallsDexBot"], user: discord.User):
        """
        Begin a battle with the chosen user.

        Parameters
        ----------
        user: discord.User
            The user you want to battle with
        """
        if user.bot:
            await interaction.response.send_message("You cannot battle with bots.", ephemeral=True)
            return
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot battle with yourself.", ephemeral=True
            )
            return

        battle1, battler1 = self.get_battle(interaction)
        battle2, battler2 = self.get_battle(channel=interaction.channel, user=user)  # type: ignore
        if battle1 or battler1:
            await interaction.response.send_message(
                "You already have an ongoing battle.", ephemeral=True
            )
            return
        if battle2 or battler2:
            await interaction.response.send_message(
                "The user you are trying to battle with is already in a battle.", ephemeral=True
            )
            return

        player1, _ = await Player.get_or_create(discord_id=interaction.user.id)
        player2, _ = await Player.get_or_create(discord_id=user.id)
        if player2.discord_id in self.bot.blacklist:
            await interaction.response.send_message(
                "You cannot battle with a blacklisted user.", ephemeral=True
            )
            return

        menu = BattleMenu(
            self, interaction, BattlingUser(interaction.user, player1), BattlingUser(user, player2)
        )
        self.battles[interaction.guild.id][interaction.channel.id].append(menu)  # type: ignore
        await menu.start()
        await interaction.response.send_message("Battle started!", ephemeral=True)

    @app_commands.command(extras={"trade": BattleCommandType.PICK})
    async def add(
        self,
        interaction: discord.Interaction,
        countryball: BallInstanceTransform,
        special: SpecialEnabledTransform | None = None,
        shiny: bool | None = None,
    ):
        """
        Add a countryball to the ongoing battle.

        Parameters
        ----------
        countryball: BallInstance
            The countryball you want to add to your proposal
        special: Special
            Filter the results of autocompletion to a special event. Ignored afterwards.
        shiny: bool
            Filter the results of autocompletion to shinies. Ignored afterwards.
        """
        if not countryball:
            return
        if not countryball.is_tradeable:
            await interaction.response.send_message(
                "You cannot battle this countryball.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        battle, battler = self.get_battle(interaction)
        if not battle or not battler:
            await interaction.followup.send("You do not have an ongoing battle.", ephemeral=True)
            return
        if battler.locked:
            await interaction.followup.send(
                "You have locked your proposal, it cannot be edited! "
                "You can click the cancel button to stop the battle instead.",
                ephemeral=True,
            )
            return
        if countryball in battler.proposal:
            await interaction.followup.send(
                f"You already have this {settings.collectible_name} in your proposal.",
                ephemeral=True,
            )
            return
        if await countryball.is_locked():
            await interaction.followup.send(
                f"This {settings.collectible_name} is currently in an active battle, trade or donation, "
                "please try again later.",
                ephemeral=True,
            )
            return

        await countryball.lock_for_trade()
        battler.proposal.append(countryball)
        await interaction.followup.send(
            f"{countryball.countryball.country} added.", ephemeral=True
        )

    @app_commands.command(extras={"trade": BattleCommandType.REMOVE})
    async def remove(self, interaction: discord.Interaction, countryball: BallInstanceTransform):
        """
        Remove a countryball from what you proposed in the ongoing battle.

        Parameters
        ----------
        countryball: BallInstance
            The countryball you want to remove from your proposal
        """
        if not countryball:
            return

        battle, battler = self.get_battle(interaction)
        if not battle or not battler:
            await interaction.response.send_message(
                "You do not have an ongoing battle.", ephemeral=True
            )
            return
        if battler.locked:
            await interaction.response.send_message(
                "You have locked your proposal, it cannot be edited! "
                "You can click the cancel button to stop the battle instead.",
                ephemeral=True,
            )
            return
        if countryball not in battler.proposal:
            await interaction.response.send_message(
                f"That {settings.collectible_name} is not in your proposal.", ephemeral=True
            )
            return
        battler.proposal.remove(countryball)
        await interaction.response.send_message(
            f"{countryball.countryball.country} removed.", ephemeral=True
        )
        await countryball.unlock()
