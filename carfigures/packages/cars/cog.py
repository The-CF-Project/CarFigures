import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from carfigures.core.models import (
    CarInstance,
    DonationPolicy,
    Player,
    cars,
)
from carfigures.core.utils.paginators import FieldPageSource, Pages
from carfigures.core.utils.transformers import (
    CarEnabledTransform,
    CarInstanceTransform,
    ExclusiveTransform,
    CarTypeTransform,
    EventEnabledTransform,
)
from carfigures.packages.cars.components import (
    SortingChoices,
    DonationRequest,
    CarFiguresViewer,
    inventory_privacy_checker,
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

    @app_commands.command(name=appearance.garage_name, description=appearance.garage_desc)
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def garage(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User | None = None,
        sort: SortingChoices | None = None,
        reverse: bool = False,
        carfigure: CarEnabledTransform | None = None,
        album: CarTypeTransform | None = None,
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
        pov = "you don't" if not user else f"{player_obj.name} doesn't"

        await interaction.response.defer(thinking=True)
        player = await Player.get_or_none(discord_id=player_obj.id)
        if not player:
            await interaction.followup.send(f"{pov} have any {appearance.collectible_plural} yet.")
            return

        if not await inventory_privacy_checker(interaction, player, player_obj):
            return

        await player.fetch_related("cars")
        filters = {}
        if carfigure:
            filters["car__id"] = carfigure.pk
        if album:
            filters["car__cartype"] = album
        # Having Ifs to filter the garage based on the player selection
        match sort:
            case SortingChoices.duplicates:
                carfigures = await player.cars.filter(**filters)
                count = defaultdict(int)
                for car in carfigures:
                    count[car.carfigure.pk] += 1
                carfigures.sort(key=lambda m: (-count[m.carfigure.pk], m.carfigure.pk))
            case SortingChoices.statsBonus:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weightBonus + x.horsepowerBonus, reverse=True)
            case SortingChoices.totalStats:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda x: x.weight + x.horsepower, reverse=True)
            case _:
                if sort:
                    carfigures = await player.cars.filter(**filters).order_by(sort.value)
                else:
                    carfigures = await player.cars.filter(**filters).order_by("-favorite")

        # Error Handling where the player chooses a car he doesn't have or has no cars in general
        if len(carfigures) < 1:
            car_txt = carfigure.fullName if carfigure else ""
            await interaction.followup.send(
                f"{pov} have any {car_txt} {appearance.collectible_plural} yet."
            )
            return
        if reverse:
            carfigures.reverse()
        # Starting the Dropdown menu
        paginator = CarFiguresViewer(interaction, carfigures)
        if not user:
            await paginator.start()
        else:
            await paginator.start(content=f"Viewing {player_obj.name}'s {appearance.garage_name}!")

    @app_commands.command(name=appearance.exhibit_name, description=appearance.exhibit_desc)
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def exhibit(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        album: CarTypeTransform | None = None,
        user: discord.User | None = None,
        event: EventEnabledTransform | None = None,
        exclusive: ExclusiveTransform | None = None,
    ):
        """
        Show your showroom in the bot.

        Parameters
        ----------
        user: discord.User
            The user whose showroom you want to view, if not yours.
        album: CarType
            The album you want to see the showroom of
        event: Event
            The event you want to see the showroom of
        exclusive: Exclusive
            The exclusive you want to see the showroom of
        """
        # checking if the user is selected or Nothing
        # also Verify if the player's exhibit is private
        player_obj = user or interaction.user
        pov = "you don't" if not user else f"{player_obj.name} doesn't"
        await interaction.response.defer(thinking=True)

        player = await Player.get_or_none(discord_id=player_obj.id)
        if not player:
            await interaction.followup.send(f"{pov} have any {appearance.collectible_plural} yet.")
            return
        if not await inventory_privacy_checker(interaction, player, player_obj):
            return

        # Filter disabled cars, they do not count towards progression
        # Only ID and emoji is interesting for us
        bot_carfigures = {x: y.emoji for x, y in cars.items() if y.enabled}

        # Set of car IDs owned by the user
        filters = {"player__discord_id": player_obj.id, "car__enabled": True}
        if album:
            filters["car__cartype"] = album
            bot_carfigures = {
                emoji: carfigure.emoji
                for emoji, carfigure in cars.items()
                if carfigure.enabled and carfigure.cartype_id == album.pk
            }
        if exclusive:
            filters["exclusive"] = exclusive
        if event:
            filters["event"] = event
            bot_carfigures = {
                emoji: carfigure.emoji
                for emoji, carfigure in cars.items()
                if carfigure.enabled and carfigure.createdAt < event.endDate
            }

        if not bot_carfigures:
            await interaction.followup.send(
                f"There are no {appearance.collectible_plural} registered on this bot yet.",
                ephemeral=True,
            )
            return
        owned_instances = set(
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

        if owned_instances:
            # Getting the list of emoji IDs from the IDs of the owned carfigures
            fill_fields(
                f"⋄ Owned {appearance.collectible_plural.title()} | {len(owned_instances)} total",
                set(bot_carfigures[carfigure] for carfigure in owned_instances),
            )
        else:
            entries.append(
                (f"__**Owned {appearance.collectible_plural.title()}s**__", "Nothing yet.")
            )
        # Getting the list of emoji IDs of any carfigures not owned by the player
        if missing := set(y for x, y in bot_carfigures.items() if x not in owned_instances):
            fill_fields(
                f"⋄ Missing {appearance.collectible_plural.title()} | {len(missing)} total",
                missing,
            )
        else:
            entries.append(
                (
                    f"__**:partying_face: No missing {appearance.collectible_plural}, "
                    "congratulations! :partying_face:**__",
                    "\u200b",
                )
            )  # force empty field value
        # Running a pager to navigate between pages of Emoji IDs
        source = FieldPageSource(entries, per_page=5, inline=False, clear_description=False)
        event_str = f" | {event.name}" if event else ""
        exclusive_str = f" {exclusive.name}" if exclusive else ""
        source.embed.description = (
            f"**⊾ {settings.bot_name}{event_str}{exclusive_str} Progression: "
            f"{round(len(owned_instances) / len(bot_carfigures) * 100, 1)}% | {len(owned_instances)}/{len(bot_carfigures)}**"
        )
        source.embed.colour = settings.default_embed_color
        source.embed.set_author(name=player_obj.display_name, icon_url=player_obj.display_avatar.url)

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command(name=appearance.show_name, description=appearance.show_desc)
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
        """
        await interaction.response.defer(thinking=True)
        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command(name=appearance.info_name, description=appearance.info_desc)
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
                f"**⋄ {appearance.album}:** {carfigure.cached_album.name}\n"
                f"**⋄ {appearance.country}:** {carfigure.cached_country.name if carfigure.cached_country else 'None'}\n"
                f"**⋄ Rarity:** {carfigure.rarity}\n"
                f"**⋄ {appearance.horsepower}:** {carfigure.horsepower}\n"
                f"**⋄ {appearance.weight}:** {carfigure.weight}\n"
                f"**⋄ Capacity Name:** {carfigure.capacityName}\n"
                f"**⋄ Capacity Description:** {carfigure.capacityDescription}\n"
                f"**⋄ Image Credits:** {carfigure.carCredits}\n"
            ),
            color=settings.default_embed_color,
        )
        await interaction.response.send_message(
            embed=embed
        )  # Send the car information embed as a response

    @app_commands.command(
        description=f"Display info of your or another users last caught {appearance.collectible_singular}"
    )
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def last(self, interaction: discord.Interaction, user: discord.User | None = None):
        """
        Display info of your or another users last caught carfigure.

        Parameters
        ----------
        user: discord.Member
            The user you would like to see
        """
        player_obj = user or interaction.user
        pov = "you don't" if not user else f"{player_obj.name} doesn't"
        await interaction.response.defer(thinking=True)
        # Try to check if the player have any carfigures

        player = await Player.get_or_none(discord_id=player_obj.id)
        if not player:
            await interaction.response.send_message(
                f"{pov} have any {appearance.collectible_plural} yet."
            )
            return

        if not await inventory_privacy_checker(interaction, player, player_obj):
            return
        # Sort the cars in the player inventory by -id which means by id but reversed
        # Then Selects the first car in that list
        carfigure = await player.cars.all().order_by("-id").first().select_related("car")
        if not carfigure:
            await interaction.followup.send(
                f"{pov} not have any {appearance.collectible_plural} yet.",
                ephemeral=True,
            )
            return

        content, file = await carfigure.prepare_for_message(interaction)
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
        """
        # Checks if the car is not favorited
        if not carfigure.favorite:
            player = await Player.get(discord_id=interaction.user.id).prefetch_related("cars")
            # Checks if the amount of the cars that have been favorited equals to the limit
            if await player.cars.filter(favorite=True).count() >= settings.max_favorites:
                await interaction.response.send_message(
                    f"You cannot set more than {settings.max_favorites} "
                    f"favorite {appearance.collectible_plural}.",
                    ephemeral=True,
                )
                return
            # Sends a request to favorite the car and saves it in the database
            carfigure.favorite = True  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.fullName} "
                f"is now a favorite {appearance.collectible_singular}!",
                ephemeral=True,
            )
        # Unfavorite the carfigure
        else:
            carfigure.favorite = False  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.fullName} "
                f"isn't a favorite {appearance.collectible_singular} anymore.",
                ephemeral=True,
            )

    @app_commands.command(
        name=appearance.gift_name,
        description=appearance.gift_desc,
    )
    async def gift(
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
        if not carfigure.is_tradeable:
            await interaction.response.send_message(
                f"You cannot donate this {appearance.collectible_singular}.", ephemeral=True
            )
            return
        if user.bot:
            await interaction.response.send_message("You cannot donate to bots.", ephemeral=True)
            return
        if await carfigure.is_locked():
            await interaction.response.send_message(
                f"This {appearance.collectible_singular} is currently locked for a trade. "
                "Please try again later."
            )
            return
        receiver, _ = await Player.get_or_create(discord_id=user.id)
        gifter = carfigure.player

        if receiver == gifter:
            await interaction.response.send_message(
                f"You cannot gift a {appearance.collectible_singular} to yourself.",
                ephemeral=True,
            )
            return
        if receiver.discord_id in self.bot.blacklisted_users:
            await interaction.response.send_message(
                "You cannot donate to a blacklisted user", ephemeral=True
            )
            return

        await carfigure.lock_for_trade()
        match receiver.donationPolicy:
            case DonationPolicy.alwaysDeny:
                await interaction.response.send_message(
                    "This user does not accept donations. You can use trades instead.",
                    ephemeral=True,
                )
                await carfigure.unlock()
                return
            case DonationPolicy.requestApproval:
                await interaction.response.send_message(
                    f"Hey {user.mention}, {interaction.user.name} wants to give you "
                    f"{carfigure.description(include_emoji=True, bot=self.bot, is_trade=True)}!\n"
                    "Do you accept this donation?",
                    view=DonationRequest(self.bot, interaction, carfigure, receiver),
                )
                return

        carfigure.player = receiver
        carfigure.trade_player = gifter
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
        album: CarTypeTransform | None = None,
        event: EventEnabledTransform | None = None,
        exclusive: ExclusiveTransform | None = None,
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
        exclusive: Exclusive
            The exclusive you want to count
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
        if album:
            filters["cartype"] = album
        if exclusive:
            filters["exclusive"] = exclusive
        if event:
            filters["event"] = event
        if spawnedhere:
            filters["server"] = interaction.guild.id
        filters["player__discord_id"] = interaction.user.id
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Entering the filter selected in the bot then give back info based on it
        cars = await CarInstance.filter(**filters).count()
        fullName = f"{carfigure.fullName} " if carfigure else ""
        album_str = f"{album.name} " if album else ""
        exclusive_str = f"{exclusive.name} " if exclusive else ""
        event_str = f"{event.name} " if event else ""
        guild = f" caught in {interaction.guild.name}" if spawnedhere else ""
        await interaction.followup.send(
            f"You have {cars} {album_str}{event_str}{exclusive_str}" f"{fullName}{guild}."
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
        sorted_rarities = sorted(rarity_to_collectibles.keys(), reverse=reverse)

        # Display collectibles grouped by rarity
        entries = []
        for rarity in sorted_rarities:
            collectible_names = "\n".join(
                [
                    f"\u200b ⋄ {self.bot.get_emoji(c.emoji) or 'N/A'} {c.fullName}"
                    for c in rarity_to_collectibles[rarity]
                ]
            )
            entry = (f"∥ Rarity: {rarity}", f"{collectible_names}")
            entries.append(entry)

        # Starting the Pager
        source = FieldPageSource(entries, per_page=2, inline=False, clear_description=False)
        source.embed.title = f"{settings.bot_name} Rarity List"
        source.embed.colour = settings.default_embed_color
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

        interaction.user
        if interaction.response.is_done():
            return

        await interaction.response.defer(thinking=True)
        assert interaction.guild

        # Making a placeholder for the player, and if statements to make sure it works perfectly
        player = await Player.get_or_none(discord_id=interaction.user.id)
        if not player:
            await interaction.response.send_message(
                f"You do not have any {appearance.collectible_plural} yet.",
                ephemeral=True,
            )
            return

        # Creating an Embed to hold all these
        embed = discord.Embed(
            title=f"❖ {interaction.user.display_name} Comparison!",
            description=f"⊰ **{first.carfigure.fullName} vs. {second.carfigure.fullName} ⊱**",
            colour=settings.default_embed_color,
        )

        embed.add_field(
            name="◊ Name",
            value=f""
            f"• ID\n"
            f"• {appearance.album}\n"
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
            f"≛ {first.carfigure.cached_album.name}\n"
            f"≛ {first.carfigure.cached_country.name if first.carfigure.cached_country else 'None'}\n"
            f"≛ {first.carfigure.rarity}\n"
            f"≛ {first.horsepower}\n"
            f"≛ {first.weight}\n"
            f"≛ {format_dt(first.catchDate, style='R') or 'N/A'}\n",
            inline=True,
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(second.carfigure.emoji) or 'N/A'} **{second.carfigure.fullName}**",
            value=f"≛ {second.pk}\n"
            f"≛ {second.carfigure.cached_album.name}\n"
            f"≛ {second.carfigure.cached_country.name if second.carfigure.cached_country else 'None'}\n"
            f"≛ {second.carfigure.rarity}\n"
            f"≛ {second.horsepower}\n"
            f"≛ {second.weight}\n"
            f"≛ {format_dt(second.catchDate, style='R') or 'N/A'}\n",
            inline=True,
        )

        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed)
