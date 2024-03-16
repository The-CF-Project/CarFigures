import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from tortoise.exceptions import DoesNotExist

from carfigures.core.models import (
    CarInstance,
    DonationPolicy,
    Trade,
    TradeObject,
    Player,
    cars,
)
from carfigures.core.utils import menus
from carfigures.core.utils.paginator import FieldPageSource, Pages
from carfigures.core.utils.transformers import (
    CarEnabledTransform,
    CarInstanceTransform,
    SpecialEnabledTransform,
    TradeCommandType,
)
from carfigures.packages.cars.components import (
    SortingChoices,
    DonationRequest,
    CarFiguresViewer,
    inventory_privacy
)
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.carfigures")



class Cars(commands.GroupCog, group_name=settings.players_group_cog_name):
    """
    View and manage your carfigures collection.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def garage(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User | None = None,
        sort: SortingChoices | None = None,
        reverse: bool = False,
        carfigure: CarEnabledTransform | None = None,
    ):
        """
        Show Your Garage!

        Parameters
        ----------
        user: discord.User
            The user whose collection you want to view, if not yours.
        sort: SortingChoices
            Choose how carfigures are sorted. Can be used to show duplicates.
        reverse: bool
            Reverse the output of the list.
        carfigure: Car
            Filter the list by a specific carfigure.
        """
        player_obj = user or interaction.user
        await interaction.response.defer(thinking=True)

        try:
            player = await Player.get(discord_id=player_obj.id)
        except DoesNotExist:
            if player_obj == interaction.user:
                await interaction.followup.send(
                    f"You don't have any {settings.collectible_name} yet."
                )
            else:
                await interaction.followup.send(
                    f"{player_obj.name} doesn't have any {settings.collectible_name} yet."
                )
            return
        if player is not None:
            if await inventory_privacy(self.bot, interaction, player, player_obj) is False:
                return

        await player.fetch_related("cars")
        filters = {"car__id": carfigure.pk} if carfigure else {}
        if sort:
            if sort == SortingChoices.duplicates:
                carfigures = await player.cars.filter(**filters)
                count = defaultdict(int)
                for car in carfigures:
                    count[car.carfigure.pk] += 1
                carfigures.sort(key=lambda m: (-count[m.carfigure.pk], m.carfigure.pk))
            elif sort == SortingChoices.stats_bonus:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weight_bonus + x.horsepower_bonus, reverse=True)
            elif sort == SortingChoices.weight:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weight, reverse=True)
            elif sort == SortingChoices.horsepower:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.horsepower, reverse=True)
            elif sort == SortingChoices.total_stats:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weight + x.horsepower, reverse=True)
            else:
                carfigures = await player.cars.filter(**filters).order_by(sort.value)
        else:
            carfigures = await player.cars.filter(**filters).order_by("-favorite", "-limited")

        if len(carfigures) < 1:
            car_txt = carfigure.full_name if carfigure else ""
            if player_obj == interaction.user:
                await interaction.followup.send(
                    f"You don't have any {car_txt} {settings.collectible_name} yet."
                )
            else:
                await interaction.followup.send(
                    f"{player_obj.name} doesn't have any {car_txt} {settings.collectible_name} yet."
                )
            return
        if reverse:
            carfigures.reverse()

        paginator = CarFiguresViewer(interaction, carfigures)
        if player_obj == interaction.user:
            await paginator.start()
        else:
            await paginator.start(
                content=f"Viewing {player_obj.name}'s {settings.collectible_name}s"
            )

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def showroom(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User | None = None,
        special: SpecialEnabledTransform | None = None,
        limited: bool | None = None,
    ):
        """
        Show your showroom of the CarFigures.

        Parameters
        ----------
        user: discord.User
            The user whose showroom you want to view, if not yours.
        special: Special
            The special you want to see the showroom of
        limited: bool
            Whether you want to see the showroom of limited carfigures
        """
        player_obj = user or interaction.user
        if user is not None:
            try:
                user = await Player.get(discord_id=player_obj.id)
            except DoesNotExist:
                await interaction.response.send_message(
                    f"{player_obj.name} doesn't have any {settings.collectible_name} yet."
                )
                return
            if await inventory_privacy(self.bot, interaction, user, player_obj) is False:
                return
        # Filter disabled cars, they do not count towards progression
        # Only ID and emoji is interesting for us
        bot_carfigures = {x: y.emoji_id for x, y in cars.items() if y.enabled}

        # Set of car IDs owned by the user
        filters = {"player__discord_id": player_obj.id, "car__enabled": True}
        if special:
            filters["special"] = special
            bot_carfigures = {
                x: y.emoji_id
                for x, y in cars.items()
                if y.enabled and y.created_at < special.end_date
            }
        if not bot_carfigures:
            await interaction.response.send_message(
                f"There are no {settings.collectible_name}s registered on this bot yet.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(thinking=True)

        if limited is not None:
            filters["limited"] = limited
        owned_carfigures = set(
            x[0]
            for x in await CarInstance.filter(**filters)
            .distinct()  # Do not query everything
            .values_list("car_id")
        )

        entries: list[tuple[str, str]] = []

        def fill_fields(title: str, emoji_ids: set[int]):
            # check if we need to add "(continued)" to the field name
            first_field_added = False
            buffer = ""

            for emoji_id in emoji_ids:
                emoji = self.bot.get_emoji(emoji_id)
                if not emoji:
                    continue

                text = f"{emoji} "
                if len(buffer) + len(text) > 1024:
                    # hitting embed limits, adding an intermediate field
                    if first_field_added:
                        entries.append(("\u200B", buffer))
                    else:
                        entries.append((f"__**{title}**__", buffer))
                        first_field_added = True
                    buffer = ""
                buffer += text

            if buffer:  # add what's remaining
                if first_field_added:
                    entries.append(("\u200B", buffer))
                else:
                    entries.append((f"__**{title}**__", buffer))

        if owned_carfigures:
            # Getting the list of emoji IDs from the IDs of the owned carfigures
            fill_fields(
                f"Owned {settings.collectible_name}s | {len(owned_carfigures) if len(owned_carfigures)>0 else 0} total",
                set(bot_carfigures[x] for x in owned_carfigures),
            )
        else:
            entries.append((f"__**Owned {settings.collectible_name}s**__", "Nothing yet."))

        if missing := set(y for x, y in bot_carfigures.items() if x not in owned_carfigures):
            fill_fields(f"Missing {settings.collectible_name}s | {len(missing) if len(missing)>0 else 0} total", missing)
        else:
            entries.append(
                (
                    f"__**:partying_face: No missing {settings.collectible_name}, "
                    "congratulations! :partying_face:**__",
                    "\u200B",
                )
            )  # force empty field value

        source = FieldPageSource(entries, per_page=5, inline=False, clear_description=False)
        special_str = f" ({special.name})" if special else ""
        limited_str = " limited" if limited else ""
        source.embed.description = (
            f"{settings.bot_name}{special_str}{limited_str} progression: "
            f"**{round(len(owned_carfigures)/len(bot_carfigures)*100, 1)}% | {len(owned_carfigures)}/{len(bot_carfigures)}**"
        )
        source.embed.colour = discord.Colour.blurple()
        source.embed.set_author(name=player_obj.display_name, icon_url=player_obj.display_avatar.url)

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command()
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def check(
        self,
        interaction: discord.Interaction,
        carfigure: CarInstanceTransform,
        special: SpecialEnabledTransform | None = None,
        limited: bool | None = None,
        ):
        """
        Display info from your carfigures collection.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to inspect
        special: Special
            The special you want to inspect
        limited: bool
            Whether you want to inspect limited carfigures
        """
        if not carfigure:
            return
        await interaction.response.defer(thinking=True)
        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command()
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def info(self, interaction: discord.Interaction, carfigure: CarEnabledTransform):
        """
        Display info from a specific carfigure.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to inspect
        """
        if not carfigure:
            return 

        else:
            emoji = self.bot.get_emoji(carfigure.emoji_id) or "" # Get emoji or an empty string if not found
            car_info_embed = discord.Embed(
                title=f"{emoji} {carfigure.full_name} Information:",
                description=(
                f"**Short Name:** {carfigure.short_name}\n"
                f"**Catch Names:** {''.join(carfigure.catch_names)}\n"
                f"**CarType:** {carfigure.cached_cartype.name}\n"
                f"**Country:** {carfigure.cached_country.name}\n"
                f"**Rarity:** {carfigure.rarity}\n"
                f"**Horsepower:** {carfigure.horsepower}\n"
                f"**Weight:** {carfigure.weight}\n"
                f"**Capacity Name:** {carfigure.capacity_name}\n"
                f"**Capacity Description:** {carfigure.capacity_description}\n"
                f"**Image Credits:** {carfigure.credits}\n"
                ),
                color=discord.Color.blurple()
                )
        await interaction.response.send_message(embed=car_info_embed) # Send the car information embed as a response

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def last(self, interaction: discord.Interaction, user: discord.User | None = None):
        """
        Display info of your or another users last caught carfigure.

        Parameters
        ----------
        user: discord.Member
            The user you would like to see
        """
        user_obj = user if user else interaction.user
        await interaction.response.defer(thinking=True)
        try:
            user = await Player.get(discord_id=user_obj.id)
        except DoesNotExist:
            msg = f"{'You do' if user is None else f'{user_obj.display_name} does'}"
            await interaction.followup.send(
                f"{msg} not have any {settings.collectible_name} yet.",
                ephemeral=True,
            )
            return

        if user is not None:
            if await inventory_privacy(self.bot, interaction, user, user_obj) is False:
                return

        carfigure = await user.cars.all().order_by("-id").first().select_related("car")
        if not carfigure:
            msg = f"{'You do' if user is None else f'{user_obj.display_name} does'}"
            await interaction.followup.send(
                f"{msg} not have any {settings.collectible_name} yet.",
                ephemeral=True,
            )
            return

        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command()
    async def favorite(self, interaction: discord.Interaction, carfigure: CarInstanceTransform):
        """
        Set favorite carfigures.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to set/unset as favorite
        """
        if not carfigure:
            return

        if not carfigure.favorite:
            user = await Player.get(discord_id=interaction.user.id).prefetch_related("cars")
            if await user.cars.filter(favorite=True).count() >= settings.max_favorites:
                await interaction.response.send_message(
                    f"You cannot set more than {settings.max_favorites} "
                    f"favorite {settings.collectible_name}s.",
                    ephemeral=True,
                )
                return

            carfigure.favorite = True  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji_id) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.full_name} "
                f"is now a favorite {settings.collectible_name}!",
                ephemeral=True,
            )

        else:
            carfigure.favorite = False  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji_id) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.full_name} "
                f"isn't a favorite {settings.collectible_name} anymore.",
                ephemeral=True,
            )

    @app_commands.command(extras={"trade": TradeCommandType.PICK})
    async def give(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        carfigure: CarInstanceTransform,
    ):
        """
        Give a carfigure to a user.

        Parameters
        ----------
        user: discord.User
            The user you want to give a carfigure to
        carfigure: CarInstance
            The carfigure you're giving away
        """
        if not carfigure:
            return
        if not carfigure.is_tradeable:
            await interaction.response.send_message(
                "You cannot donate this carfigure.", ephemeral=True
            )
            return
        if user.bot:
            await interaction.response.send_message("You cannot donate to bots.")
            return
        if await carfigure.is_locked():
            await interaction.response.send_message(
                "This carfigure is currently locked for a trade. Please try again later."
            )
            return
        await carfigure.lock_for_trade()
        new_player, _ = await Player.get_or_create(discord_id=user.id)
        old_player = carfigure.player

        if new_player == old_player:
            await interaction.response.send_message(
                f"You cannot give a {settings.collectible_name} to yourself."
            )
            await carfigure.unlock()
            return
        if new_player.donation_policy == DonationPolicy.ALWAYS_DENY:
            await interaction.response.send_message(
                "This user does not accept donations. You can use trades instead."
            )
            await carfigure.unlock()
            return
        if new_player.discord_id in self.bot.blacklist:
            await interaction.response.send_message(
                "You cannot donate to a blacklisted user", ephemeral=True
            )
            await carfigure.unlock()
            return
        elif new_player.donation_policy == DonationPolicy.REQUEST_APPROVAL:
            await interaction.response.send_message(
                f"Hey {user.mention}, {interaction.user.name} wants to give you "
                f"{carfigure.description(include_emoji=True, bot=self.bot, is_trade=True)}!\n"
                "Do you accept this donation?",
                view=DonationRequest(self.bot, interaction, carfigure, new_player),
            )
            return

        carfigure.user = new_player
        carfigure.trade_user = old_player
        carfigure.favorite = False
        await carfigure.save()

        trade = await Trade.create(player1=old_player, player2=new_player)
        await TradeObject.create(trade=trade, carinstance=carfigure, player=new_player)

        cf_txt = carfigure.description(
            short=True, include_emoji=True, bot=self.bot, is_trade=True
        )

        await interaction.response.send_message(
            f"You just gave the {settings.collectible_name} {cf_txt} to {user.mention}!"
        )
        await carfigure.unlock()

    @app_commands.command()
    async def count(
        self,
        interaction: discord.Interaction,
        carfigure: CarEnabledTransform | None = None,
        special: SpecialEnabledTransform | None = None,
        limited: bool | None = None,
        current_server: bool = False,
    ):
        """
        Count how many carfigures you have.

        Parameters
        ----------
        carfigure: Car
            The carfigure you want to count
        special: Special
            The special you want to count
        limited: bool
            Whether you want to count limited carfigures
        current_server: bool
            Only count carfigures caught in the current server
        """
        if interaction.response.is_done():
            return
        assert interaction.guild
        filters = {}
        if carfigure:
            filters["car"] = carfigure
        if limited is not None:
            filters["limited"] = limited
        if special:
            filters["special"] = special
        if current_server:
            filters["server_id"] = interaction.guild.id
        filters["user__discord_id"] = interaction.user.id
        await interaction.response.defer(ephemeral=True, thinking=True)
        cars = await CarInstance.filter(**filters).count()
        full_name = f"{carfigure.full_name} " if carfigure else ""
        plural = "s" if cars > 1 or cars == 0 else ""
        limited_str = "limited " if limited else ""
        special_str = f"{special.name} " if special else ""
        guild = f" caught in {interaction.guild.name}" if current_server else ""
        await interaction.followup.send(
            f"You have {cars} {special_str}{limited_str}"
            f"{full_name}{settings.collectible_name}{plural}{guild}."
        )

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def rarity(self, interaction: discord.Interaction):
        """
        Show the rarity list of the bot
        """

        # Filter enabled collectibles
        enabled_collectibles = [x for x in cars.values() if x.enabled]

        if not enabled_collectibles:
            await interaction.response.send_message(
                f"There are no collectibles registered in {settings.bot_name} yet.",
                ephemeral=True,
            )
            return

        # Group collectibles by rarity
        rarity_to_collectibles = {}
        for collectible in enabled_collectibles:
            rarity = collectible.rarity
            if rarity not in rarity_to_collectibles:
                rarity_to_collectibles[rarity] = []
            rarity_to_collectibles[rarity].append(collectible)

        # Sort the rarity_to_collectibles dictionary by rarity
        sorted_rarities = sorted(rarity_to_collectibles.keys())

        # Display collectibles grouped by rarity
        entries = []
        for rarity in sorted_rarities:
            collectible_names = "\n".join([f"{self.bot.get_emoji(c.emoji_id) or 'N/A'} {c.full_name}" for c in rarity_to_collectibles[rarity]])
            entry = (f"Rarity: {rarity}", collectible_names)
            entries.append(entry)

        per_page = 2  # Number of collectibles displayed on one page
        source = FieldPageSource(entries, per_page=per_page, inline=False, clear_description=False)
        source.embed.description = f"__**{settings.bot_name} rarity**__"
        source.embed.colour = discord.Colour.blurple()
        source.embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()