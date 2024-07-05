import zipfile
from io import BytesIO
import discord
import logging

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands

from carfigures.core.models import DonationPolicy, PrivacyPolicy, Player as PlayerModel
from carfigures.core.utils.buttons import ConfirmChoiceView
from carfigures.packages.players.components import (
    _get_10_cars_emojis,
    get_items_csv,
    get_trades_csv,
)


from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.players")


class Player(commands.GroupCog, group_name=settings.player_group_name):
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
            app_commands.Choice(
                name="Accept all donations", value=DonationPolicy.ALWAYS_ACCEPT
            ),
            app_commands.Choice(
                name="Request your approval first",
                value=DonationPolicy.REQUEST_APPROVAL,
            ),
            app_commands.Choice(
                name="Deny all donations", value=DonationPolicy.ALWAYS_DENY
            ),
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
                "immediately.",
                ephemeral=True,
            )
        elif policy.value == DonationPolicy.REQUEST_APPROVAL:
            await interaction.response.send_message(
                "Setting updated, you will now have to approve donation requests manually.",
                ephemeral=True,
            )
        elif policy.value == DonationPolicy.ALWAYS_DENY:
            await interaction.response.send_message(
                "Setting updated, it is now impossible to use "
                f"`/{settings.player_group_name} give` with "
                "you. It is still possible to perform donations using the trade system.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("Invalid input!", ephemeral=True)
            return
        await user.save()  # do not save if the input is invalid

    @app_commands.command()
    async def profile(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ):
        """
        Show your/other profile.
        """

        # Setting Up variables
        player_obj = user or interaction.user

        if settings.profiles_emojis:
            cars = await _get_10_cars_emojis(self)
        else:
            cars = []

        player, _ = await PlayerModel.get_or_create(discord_id=player_obj.id)
        await player.fetch_related("cars")

        # Creating the Embed and Storting the variables in it
        embed = discord.Embed(
            title=f" ❖ {player_obj.display_name}'s Profile",
            color=settings.default_embed_color,
        )

        if player.privacy_policy == PrivacyPolicy.ALLOW:
            privacy = "Open Inventory"
        else:
            privacy = "Private Inventory"

        if player.donation_policy == DonationPolicy.ALWAYS_ACCEPT:
            donation = "All Accepted"
        elif player.donation_policy == DonationPolicy.REQUEST_APPROVAL:
            donation = "Approval Required"
        else:
            donation = "All Denied"

        embed.description = (
            f"{' '.join(str(x) for x in cars)}\n"
            f"**∨ Player Settings**\n"
            f"\u200b **⋄ Privacy Policy:** {privacy}\n"
            f"\u200b **⋄ Donation Policy:** {donation}\n\n"
            f"**∧ Player Info\n**"
            f"\u200b **⋄ Cars Collected:** {len(player.cars)}\n"
        )

        embed.set_thumbnail(url=player_obj.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    async def delete(self, interaction: discord.Interaction):
        """
        Delete your player data.
        """
        view = ConfirmChoiceView(interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            player = await PlayerModel.get(discord_id=interaction.user.id)
        except DoesNotExist:
            await interaction.followup.send("You haven't got any data to delete.")
            return
        else:
            await interaction.followup.send(
                "Are you sure you want to delete your player data?", 
                view=view, 
            )
        await view.wait()
        if view.value is None or not view.value:
            return
        
        await player.delete()
        await interaction.followup.send("Player data deleted.", ephemeral=True)

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
