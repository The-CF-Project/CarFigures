import zipfile
from io import BytesIO
import discord
import logging

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands
from tortoise.expressions import Q

from carfigures.core.models import (
    CarInstance,
    DonationPolicy,
    PrivacyPolicy,
    Trade,
    TradeObject,
    Player as PlayerModel
)
from carfigures.core.utils.buttons import ConfirmChoiceView
from carfigures.packages.players.components import _get_10_cars_emojis


from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.players")


class Player(commands.GroupCog, group_name=settings.group_cog_names["player"]):
    """
    Manage your account settings.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot
        if not self.bot.intents.members:
            self.__cog_app_commands_group__.get_command("privacy").parameters[  # type: ignore
                0
            ]._Parameter__parent.choices.pop()  # type: ignore

    @app_commands.command()
    @app_commands.choices(
        policy=[
            app_commands.Choice(name="Open Inventory", value=PrivacyPolicy.ALLOW),
            app_commands.Choice(name="Private Inventory", value=PrivacyPolicy.DENY),
            app_commands.Choice(name="Same Server", value=PrivacyPolicy.SAME_SERVER),
        ]
    )
    async def privacy(self, interaction: discord.Interaction, policy: PrivacyPolicy):
        """
        Set your privacy policy.
        """
        if policy == PrivacyPolicy.SAME_SERVER and not self.bot.intents.members:
            await interaction.response.send_message(
                "I need the `members` intent to use this policy.", ephemeral=True
            )
            return
        user, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        user.privacy_policy = policy
        await user.save()
        await interaction.response.send_message(
            f"Your privacy policy has been set to **{policy.name}**.", ephemeral=True
        )

    @app_commands.command()
    @app_commands.choices(
        policy=[
            app_commands.Choice(name="Accept all donations", value=DonationPolicy.ALWAYS_ACCEPT),
            app_commands.Choice(
                name="Request your approval first", value=DonationPolicy.REQUEST_APPROVAL
            ),
            app_commands.Choice(name="Deny all donations", value=DonationPolicy.ALWAYS_DENY),
        ]
    )
    async def donation_policy(
        self, interaction: discord.Interaction, policy: app_commands.Choice[int]
    ):
        """
        Change how you want to receive donations from /cars give

        Parameters
        ----------
        policy: DonationPolicy
            The new policy for accepting donations
        """
        user, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        user.donation_policy = DonationPolicy(policy.value)
        if policy.value == DonationPolicy.ALWAYS_ACCEPT:
            await interaction.response.send_message(
                f"Setting updated, you will now receive all donated {settings.collectible_name}s "
                "immediately."
            )
        elif policy.value == DonationPolicy.REQUEST_APPROVAL:
            await interaction.response.send_message(
                "Setting updated, you will now have to approve donation requests manually."
            )
        elif policy.value == DonationPolicy.ALWAYS_DENY:
            await interaction.response.send_message(
                "Setting updated, it is now impossible to use "
                f"`/{settings.players_group_cog_name} give` with "
                "you. It is still possible to perform donations using the trade system."
            )
        else:
            await interaction.response.send_message("Invalid input!")
            return
        await user.save()  # do not save if the input is invalid

    @app_commands.command()
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None
        ):
        """
        Show your/other profile.
        """

        # Setting Up variables
        if user == None:
            user = interaction.user

        cars = await _get_10_cars_emojis(self)
        player, _ = await PlayerModel.get_or_create(discord_id=user.id)
        await player.fetch_related("cars")

        # Creating the Embed and Storting the variables in it
        embed = discord.Embed(
            title=f" ❖ {user.display_name}'s Profile", color=settings.default_embed_color
        )

        embed.description = (
            f"{' '.join(str(x) for x in cars)}\n"
            f"**∨ Player Settings**\n"
            f"\u200b **⋄ Privacy Policy:** {player.privacy_policy.name}\n"
            f"\u200b **⋄ Donation Policy:** {player.donation_policy.name}\n\n"
            f"**∧ Player Info\n**"
            f"\u200b **⋄ Cars Collected:** {len(player.cars)}\n"
        )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def delete(self, interaction: discord.Interaction):
        """
        Delete your player data.
        """
        view = ConfirmChoiceView(interaction)
        await interaction.response.send_message(
            "Are you sure you want to delete your player data?", view=view, ephemeral=True
        )
        await view.wait()
        if view.value is None or not view.value:
            return
        player, _ = await PlayerModel.get_or_create(discord_id=interaction.user.id)
        await player.delete()

    @app_commands.command()
    @app_commands.choices(
        type=[
            app_commands.Choice(name=settings.collectible_name.title(), value="cars"),
            app_commands.Choice(name="Trades", value="trades"),
            app_commands.Choice(name="All", value="all"),
        ]
    )
    async def export(self, interaction: discord.Interaction, type: str):
        """
        Export your player data.
        """
        player = await PlayerModel.get_or_none(discord_id=interaction.user.id)
        if player is None:
            await interaction.response.send_message(
                "You don't have any player data to export.", ephemeral=True
            )
            return
        await interaction.response.defer()
        files = []
        if type == "cars":
            data = await get_items_csv(player)
            filename = f"{interaction.user.id}_{settings.collectible_name}.csv"
            data.filename = filename  # type: ignore
            files.append(data)
        elif type == "trades":
            data = await get_trades_csv(player)
            filename = f"{interaction.user.id}_trades.csv"
            data.filename = filename  # type: ignore
            files.append(data)
        elif type == "all":
            cars = await get_items_csv(player)
            trades = await get_trades_csv(player)
            cars_filename = f"{interaction.user.id}_{settings.collectible_name}.csv"
            trades_filename = f"{interaction.user.id}_trades.csv"
            cars.filename = cars_filename  # type: ignore
            trades.filename = trades_filename  # type: ignore
            files.append(cars)
            files.append(trades)
        else:
            await interaction.followup.send("Invalid input!", ephemeral=True)
            return
        zip_file = BytesIO()
        with zipfile.ZipFile(zip_file, "w") as z:
            for file in files:
                z.writestr(file.filename, file.getvalue())
        zip_file.seek(0)
        if zip_file.tell() > 25_000_000:
            await interaction.followup.send(
                "Your data is too large to export."
                "Please contact the bot support for more information.",
                ephemeral=True,
            )
            return
        files = [discord.File(zip_file, "player_data.zip")]
        try:
            await interaction.user.send("Here is your player data:", files=files)
            await interaction.followup.send(
                "Your player data has been sent via DMs.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't send the player data to you in DM. "
                "Either you blocked me or you disabled DMs in this server.",
                ephemeral=True,
            )


async def get_items_csv(player: PlayerModel) -> BytesIO:
    """
    Get a CSV file with all items of the player.
    """
    cars = await CarInstance.filter(player=player).prefetch_related(
        "car", "trade_player", "event"
    )
    txt = (
        f"id,hex id,{settings.collectible_name},catch date,trade_player"
        ",event,limited,horsepower,horsepower bonus,kg,kg_bonus\n"
    )
    for car in cars:
        txt += (
            f"{car.id},{car.id:0X},{car.car.full_name},{car.catch_date},"  # type: ignore
            f"{car.trade_player.discord_id if car.trade_player else 'None'},{car.event},"
            f"{car.limited},{car.horsepower},{car.horsepower_bonus},{car.weight},{car.weight_bonus}\n"
        )
    return BytesIO(txt.encode("utf-8"))


async def get_trades_csv(player: PlayerModel) -> BytesIO:
    """
    Get a CSV file with all trades of the player.
    """
    trade_history = (
        await Trade.filter(Q(player1=player) | Q(player2=player))
        .order_by("date")
        .prefetch_related("player1", "player2")
    )
    txt = "id,date,player1,player2,player1 received,player2 received\n"
    for trade in trade_history:
        player1_items = await TradeObject.filter(
            trade=trade, player=trade.player1
        ).prefetch_related("carinstance")
        player2_items = await TradeObject.filter(
            trade=trade, player=trade.player2
        ).prefetch_related("carinstance")
        txt += (
            f"{trade.id},{trade.date},{trade.player1.discord_id},{trade.player2.discord_id},"
            f"{','.join([i.carinstance.to_string() for i in player2_items])},"  # type: ignore
            f"{','.join([i.carinstance.to_string() for i in player1_items])}\n"  # type: ignore
        )
    return BytesIO(txt.encode("utf-8"))
