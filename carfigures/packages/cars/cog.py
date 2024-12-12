import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from tortoise.exceptions import DoesNotExist

from carfigures.core.models import (
    CarInstance,
    DonationPolicy,
    Player,
    cars,
)
from carfigures.core.utils.paginator import FieldPageSource, Pages
from carfigures.core.utils.transformers import (
    CarEnabledTransform,
    CarInstanceTransform,
    EventEnabledTransform,
)
from carfigures.packages.cars.components import (
    SortingChoices,
    DonationRequest,
    CarFiguresViewer,
    inventory_privacy,
)
from carfigures.settings import settings, appearance

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.carfigures")


class Cars(commands.GroupCog, group_name=appearance.cars):
    """
    View and manage your carfigures collection.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command(name=appearance.garageName, description=appearance.garageDesc)
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
        Show your garage!

        Parameters
        ----------
        user: discord.User
            The user whose garage you want to view, if not yours.
        sort: SortingChoices
            Choose how carfigures are sorted. Can be used to show duplicates.
        reverse: bool
            Reverse the output of the list.
        carfigure: Car
            Filter the list by a specific carfigure.
        """
        # simple variables
        player_obj = user or interaction.user
        await interaction.response.defer(thinking=True)

        try:
            player = await Player.get(discord_id=player_obj.id)
        except DoesNotExist:
            if player_obj == interaction.user:
                await interaction.followup.send(
                    f"You don't have any {appearance.collectiblePlural} yet."
                )
            else:
                await interaction.followup.send(
                    f"{player_obj.name} doesn't have any {appearance.collectiblePlural} yet."
                )
            return

        # Seeing if the player's garage is private.
        if player is not None:
            if await inventory_privacy(self.bot, interaction, player, player_obj) is False:
                return

        await player.fetch_related("cars")
        filters = {"car__id": carfigure.pk} if carfigure else {}
        # Having Ifs to filter the garage based on the player selection
        match sort:
            case SortingChoices.duplicates:
                carfigures = await player.cars.filter(**filters)
                count = defaultdict(int)
                for car in carfigures:
                    count[car.carfigure.pk] += 1
                carfigures.sort(key=lambda m: (-count[m.carfigure.pk], m.carfigure.pk))
            case SortingChoices.favorite:
                carfigures = await player.cars.filter(**filters).order_by("-favorite")
            case SortingChoices.statsBonus:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weightBonus + x.horsepowerBonus, reverse=True)
            case SortingChoices.weight:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weight, reverse=True)
            case SortingChoices.horsepower:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.horsepower, reverse=True)
            case SortingChoices.totalStats:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weight + x.horsepower, reverse=True)
            case SortingChoices.exclusive:
                carfigures = await player.cars.filter(**filters).order_by("exclusive__id")
            case SortingChoices.event:
                carfigures = await player.cars.filter(**filters).order_by("event__id")
            case _:
                if sort:
                    carfigures = await player.cars.filter(**filters).order_by(sort.value)
                else:
                    carfigures = await player.cars.filter(**filters).order_by("-favorite")

        # Error Handling where the player chooses a car he doesn't have or has no cars in general
        if len(carfigures) < 1:
            car_txt = carfigure.fullName if carfigure else ""
            if player_obj == interaction.user:
                await interaction.followup.send(
                    f"You don't have any {car_txt} {appearance.collectiblePlural} yet."
                )
            else:
                await interaction.followup.send(
                    f"{player_obj.name} doesn't have any {car_txt} {appearance.collectiblePlural} yet."
                )
            return
        if reverse:
            carfigures.reverse()
        # Starting the Dropdown menu
        paginator = CarFiguresViewer(interaction, carfigures)
        if player_obj == interaction.user:
            await paginator.start()
        else:
            await paginator.start(content=f"Viewing {player_obj.name}'s {appearance.garageName}!")

    @app_commands.command(name=appearance.exhibitName, description=appearance.exhibitDesc)
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def exhibit(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User | None = None,
        event: EventEnabledTransform | None = None,
        limited: bool | None = None,
    ):
        """
        Show your showroom in the bot.

        Parameters
        ----------
        user: discord.User
            The user whose showroom you want to view, if not yours.
        event: Event
            The event you want to see the showroom of
        limited: bool
            Whether you want to see the showroom of limited carfigures
        """
        # checking if the user is selected or Nothing
        # also Verify if the player's exhibit is private
        player_obj = user or interaction.user
        if user is not None:
            try:
                player = await Player.get(discord_id=player_obj.id)
            except DoesNotExist:
                await interaction.response.send_message(
                    f"{player_obj.name} doesn't have any {appearance.collectiblePlural} yet."
                )
                return
            if await inventory_privacy(self.bot, interaction, player, player_obj) is False:
                return
        # Filter disabled cars, they do not count towards progression
        # Only ID and emoji is interesting for us
        bot_carfigures = {x: y.emoji for x, y in cars.items() if y.enabled}

        # Set of car IDs owned by the user
        filters = {"player__discord_id": player_obj.id, "car__enabled": True}
        if event:
            filters["event"] = event
            bot_carfigures = {
                emoji: carfigure.emoji
                for emoji, carfigure in cars.items()
                if carfigure.enabled and carfigure.createdAt < event.endDate
            }
        if not bot_carfigures:
            await interaction.response.send_message(
                f"There are no {appearance.collectiblePlural} registered on this bot yet.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(thinking=True)

        if limited is not None:
            filters["limited"] = limited
        owned_carfigures = set(
            carfigures[0]
            for carfigures in await CarInstance.filter(**filters)
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
                        entries.append(("\u200b", buffer))
                    else:
                        entries.append((f"__**{title}**__", buffer))
                        first_field_added = True
                    buffer = ""
                buffer += text

            if buffer:  # add what's remaining
                if first_field_added:
                    entries.append(("\u200b", buffer))
                else:
                    entries.append((f"__**{title}**__", buffer))

        if owned_carfigures:
            # Getting the list of emoji IDs from the IDs of the owned carfigures
            fill_fields(
                f"⋄ Owned {appearance.collectiblePlural} | {len(owned_carfigures) or '0'} total",
                set(bot_carfigures[carfigure] for carfigure in owned_carfigures),
            )
        else:
            entries.append(
                (f"__**Owned {appearance.collectiblePlural.title()}s**__", "Nothing yet.")
            )
        # Getting the list of emoji IDs of any carfigures not owned by the player
        if missing := set(y for x, y in bot_carfigures.items() if x not in owned_carfigures):
            fill_fields(
                f"⋄ Missing {appearance.collectiblePlural.title()} | {len(missing) or '0'} total",
                missing,
            )
        else:
            entries.append(
                (
                    f"__**:partying_face: No missing {appearance.collectiblePlural}, "
                    "congratulations! :partying_face:**__",
                    "\u200b",
                )
            )  # force empty field value
        # Running a pager to navigate between pages of Emoji IDs
        source = FieldPageSource(entries, per_page=5, inline=False, clear_description=False)
        event_str = f" ({event.name})" if event else ""
        limited_str = " limited" if limited else ""
        source.embed.description = (
            f"**⊾ {settings.botName}{event_str}{limited_str} Progression: "
            f"{round(len(owned_carfigures) / len(bot_carfigures) * 100, 1)}% | {len(owned_carfigures)}/{len(bot_carfigures)}**"
        )
        source.embed.colour = settings.defaultEmbedColor
        source.embed.set_author(
            name=player_obj.display_name, icon_url=player_obj.display_avatar.url
        )

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command(name=appearance.showName, description=appearance.showDesc)
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def show(
        self,
        interaction: discord.Interaction,
        carfigure: CarInstanceTransform,
    ):
        """
        Display info from your carfigures collection.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to inspect
        event: Event
            The event you want to inspect
        limited: bool
            Whether you want to inspect limited carfigures
        """
        await interaction.response.defer(thinking=True)
        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command(name=appearance.infoName, description=appearance.infoDesc)
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def info(self, interaction: discord.Interaction, carfigure: CarEnabledTransform):
        """
        Display info from a specific carfigure.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to inspect
        """
        emoji = (
            self.bot.get_emoji(carfigure.emoji) or ""
        )  # Get emoji or an empty string if not found
        embed = discord.Embed(
            title=f"{emoji} {carfigure.fullName} Information:",
            description=(
                f"**⋄ Short Name:** {carfigure.shortName}\n"
                f"**⋄ Catch Names:** {''.join(carfigure.catchNames)}\n"
                f"**⋄ {appearance.cartype}:** {carfigure.cachedCartype.name}\n"
                f"**⋄ {appearance.country}:** {carfigure.cachedCountry.name or 'None'}\n"
                f"**⋄ Rarity:** {carfigure.rarity}\n"
                f"**⋄ {appearance.horsepower}:** {carfigure.horsepower}\n"
                f"**⋄ {appearance.weight}:** {carfigure.weight}\n"
                f"**⋄ Capacity Name:** {carfigure.capacityName}\n"
                f"**⋄ Capacity Description:** {carfigure.capacityDescription}\n"
                f"**⋄ Image Credits:** {carfigure.carCredits}\n"
            ),
            color=settings.defaultEmbedColor,
        )
        await interaction.response.send_message(
            embed=embed
        )  # Send the car information embed as a response

    @app_commands.command(name=appearance.lastName, description=appearance.lastDesc)
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def last(self, interaction: discord.Interaction, user: discord.User | None = None):
        """
        Display info of your or another users last caught carfigure.

        Parameters
        ----------
        user: discord.Member
            The user you would like to see
        """
        playerObj = user or interaction.user
        await interaction.response.defer(thinking=True)
        # Try to check if the player have any carfigures
        try:
            player = await Player.get(discord_id=playerObj.id)
        except DoesNotExist:
            msg = f"{'You do' if user is None else f'{playerObj.display_name} does'}"
            await interaction.followup.send(
                f"{msg} not have any {appearance.collectiblePlural} yet.",
                ephemeral=True,
            )
            return

        if user is not None:
            if await inventory_privacy(self.bot, interaction, player, playerObj) is False:
                return
        # Sort the cars in the player inventory by -id which means by id but reversed
        # Then Selects the first car in that list
        carfigure = await player.cars.all().order_by("-id").first().select_related("car")
        if not carfigure:
            msg = f"{'You do' if player is None else f'{playerObj.display_name} does'}"
            await interaction.followup.send(
                f"{msg} not have any {appearance.collectiblePlural} yet.",
                ephemeral=True,
            )
            return

        content, file = await carfigure.prepareForMessage(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command()
    async def favorite(
        self,
        interaction: discord.Interaction,
        carfigure: CarInstanceTransform,
    ):
        """
        Set favorite carfigures.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to set/unset as favorite
        event: Event
            Filter the results of autocompletion to an event. Ignored afterwards.
        limited: bool
            Filter the results of autocompletion to limiteds. Ignored afterwards.
        """
        # Checks if the car is not favorited
        if not carfigure.favorite:
            player = await Player.get(discord_id=interaction.user.id).prefetch_related("cars")
            # Checks if the amount of the cars that have been favorited equals to the limit
            if await player.cars.filter(favorite=True).count() >= settings.maxFavorites:
                await interaction.response.send_message(
                    f"You cannot set more than {settings.maxFavorites} "
                    f"favorite {appearance.collectiblePlural}.",
                    ephemeral=True,
                )
                return
            # Sends a request to favorite the car and saves it in the database
            carfigure.favorite = True  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.fullName} "
                f"is now a favorite {appearance.collectibleSingular}!",
                ephemeral=True,
            )
        # Unfavorite the carfigure
        else:
            carfigure.favorite = False  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.fullName} "
                f"isn't a favorite {appearance.collectibleSingular} anymore.",
                ephemeral=True,
            )

    @app_commands.command(
        name=appearance.giftName,
        description=appearance.giftDesc,
        # extras={"trade": TradeCommandType.PICK},
    )
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
        if not carfigure.isTradeable:
            await interaction.response.send_message(
                f"You cannot donate this {appearance.collectibleSingular}.", ephemeral=True
            )
            return
        if user.bot:
            await interaction.response.send_message("You cannot donate to bots.", ephemeral=True)
            return
        if await carfigure.isLocked():
            await interaction.response.send_message(
                f"This {appearance.collectibleSingular} is currently locked for a trade. "
                "Please try again later."
            )
            return
        await carfigure.lockForTrade()
        new_player, _ = await Player.get_or_create(discord_id=user.id)
        old_player = carfigure.player

        if new_player == old_player:
            await interaction.response.send_message(
                f"You cannot give a {appearance.collectibleSingular} to yourself.",
                ephemeral=True,
            )
            await carfigure.unlock()
            return
        if new_player.discord_id in self.bot.blacklist_user:
            await interaction.response.send_message(
                "You cannot donate to a blacklisted user", ephemeral=True
            )
            await carfigure.unlock()
            return

        match new_player.donationPolicy:
            case DonationPolicy.ALWAYS_DENY:
                await interaction.response.send_message(
                    "This user does not accept donations. You can use trades instead.",
                    ephemeral=True,
                )
                await carfigure.unlock()
                return
            case DonationPolicy.REQUEST_APPROVAL:
                await interaction.response.send_message(
                    f"Hey {user.mention}, {interaction.user.name} wants to give you "
                    f"{carfigure.description(include_emoji=True, bot=self.bot, is_trade=True)}!\n"
                    "Do you accept this donation?",
                    view=DonationRequest(self.bot, interaction, carfigure, new_player),
                )
                return

        carfigure.player = new_player
        carfigure.trade_player = old_player
        carfigure.favorite = False
        await carfigure.save()

        cf_txt = carfigure.description(short=True, include_emoji=True, bot=self.bot, is_trade=True)

        await interaction.response.send_message(f"You just gave the {cf_txt} to {user.mention}!")
        await carfigure.unlock()

    @app_commands.command()
    async def count(
        self,
        interaction: discord.Interaction,
        carfigure: CarEnabledTransform | None = None,
        event: EventEnabledTransform | None = None,
        limited: bool | None = None,
        spawnedhere: bool = False,
    ):
        """
        Count how many carfigures you have.

        Parameters
        ----------
        carfigure: Car
            The carfigure you want to count
        event: Event
            The event you want to count
        limited: bool
            Whether you want to count limited carfigures
        spawnedhere: bool
            Only count carfigures caught in the current server
        """
        # Making Sure no errors happen when responding
        if interaction.response.is_done():
            return
        assert interaction.guild

        # Creating Filters to fullfil the parameters
        filters = {}
        if carfigure:
            filters["car"] = carfigure
        if limited is not None:
            filters["limited"] = limited
        if event:
            filters["event"] = event
        if spawnedhere:
            filters["server"] = interaction.guild.id
        filters["player__discord_id"] = interaction.user.id
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Entering the filter selected in the bot then give back info based on it
        cars = await CarInstance.filter(**filters).count()
        fullName = f"{carfigure.fullName} " if carfigure else ""
        limited_str = "limited " if limited else ""
        event_str = f"{event.name} " if event else ""
        guild = f" caught in {interaction.guild.name}" if spawnedhere else ""
        await interaction.followup.send(
            f"You have {cars} {event_str}{limited_str}" f"{fullName}{guild}."
        )

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def rarity(
        self,
        interaction: discord.Interaction,
        reverse: bool = False,
    ):
        """
        Show the rarity list of the bot

        Parameters
        ----------
        reverse: bool
            Whether to show the rarity list in reverse
        """

        # Filter enabled collectibles
        enabledCollectibles = [x for x in cars.values() if x.enabled]

        if not enabledCollectibles:
            await interaction.response.send_message(
                f"There are no collectibles registered in {settings.botName} yet.",
                ephemeral=True,
            )
            return

        # Group collectibles by rarity
        rarityToCollectibles = {}
        for collectible in enabledCollectibles:
            rarity = collectible.rarity
            if rarity not in rarityToCollectibles:
                rarityToCollectibles[rarity] = []
            rarityToCollectibles[rarity].append(collectible)

        # Sort the rarityToCollectibles dictionary by rarity
        sortedRarities = sorted(rarityToCollectibles.keys(), reverse=reverse)

        # Display collectibles grouped by rarity
        entries = []
        for rarity in sortedRarities:
            collectible_names = "\n".join(
                [
                    f"\u200b ⋄ {self.bot.get_emoji(c.emoji) or 'N/A'} {c.fullName}"
                    for c in rarityToCollectibles[rarity]
                ]
            )
            entry = (f"∥ Rarity: {rarity}", f"{collectible_names}")
            entries.append(entry)

        # Starting the Pager
        per_page = 2  # Number of collectibles displayed on one page
        source = FieldPageSource(entries, per_page=per_page, inline=False, clear_description=False)
        source.embed.title = f"{settings.botName} Rarity List"
        source.embed.colour = settings.defaultEmbedColor
        pages = Pages(source=source, interaction=interaction, compact=False)
        await pages.start()

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def compare(
        self,
        interaction: discord.Interaction,
        first: CarInstanceTransform,
        second: CarInstanceTransform,
    ):
        """
        Compare two carfigures

        Parameters
        ----------
        first: Car
            The first carfigure you want to compare
        second: Car
            The second carfigure you want to compare
        """

        # Simple variables
        playerObj = interaction.user
        await interaction.response.defer(thinking=True)
        assert interaction.guild

        # Making a placeholder for the player, and if statements to make sure it works perfectly
        player = await Player.get(discord_id=playerObj.id)
        if not player:
            await interaction.response.send_message(
                f"You do not have any {appearance.collectiblePlural} yet.",
                ephemeral=True,
            )
            return

        # Creating an Embed to hold all these
        embed = discord.Embed(
            title=f"❖ {playerObj.display_name} Comparison!",
            description=f"⊰ **{first.carfigure.fullName} vs. {second.carfigure.fullName} ⊱**",
            colour=settings.defaultEmbedColor,
        )

        embed.add_field(
            name="◊ Name",
            value=f""
            f"• ID\n"
            f"• {appearance.cartype}\n"
            f"• {appearance.country}\n"
            f"• Rarity\n"
            f"• {appearance.horsepower}\n"
            f"• {appearance.weight}\n"
            f"• Catch Date",
            inline=True,
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(first.carfigure.emoji) or 'N/A'} **{first.carfigure.fullName}**\n",
            value=f"≛ {first.pk}\n"
            f"≛ {first.carfigure.cachedCartype.name}\n"
            f"≛ {first.carfigure.cachedCountry.name if first.carfigure.cachedCountry else 'None'}\n"
            f"≛ {first.carfigure.rarity}\n"
            f"≛ {first.horsepower}\n"
            f"≛ {first.weight}\n"
            f"≛ {format_dt(first.catchDate, style='R') or 'N/A'}\n",
            inline=True,
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(second.carfigure.emoji) or 'N/A'} **{second.carfigure.fullName}**",
            value=f"≛ {second.pk}\n"
            f"≛ {second.carfigure.cachedCartype.name}\n"
            f"≛ {second.carfigure.cachedCountry.name if second.carfigure.cachedCountry else 'None'}\n"
            f"≛ {second.carfigure.rarity}\n"
            f"≛ {second.horsepower}\n"
            f"≛ {second.weight}\n"
            f"≛ {format_dt(second.catchDate, style='R') or 'N/A'}\n",
            inline=True,
        )

        embed.set_footer(
            text=f"Requested by {playerObj.display_name}",
            icon_url=playerObj.display_avatar.url,
        )

        await interaction.followup.send(embed=embed)
