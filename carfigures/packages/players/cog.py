import discord
import logging

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands

from carfigures.core.models import (
    DonationPolicy,
    PrivacyPolicy,
    Player as PlayerModel
)
from carfigures.packages.players.components import _get_10_cars_emojis


from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.players")


class Player(commands.GroupCog):
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
                "Setting updated, it is now impossible to use `cars give` with "
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
