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
    EventTransform,
    ExclusiveTransform,
)
from carfigures.packages.cars.components import (
    SortingChoices,
    DonationRequest,
    CarFiguresViewer,
    inventory_privacy,
)
from carfigures.configs import appearance, commandconfig, settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.carfigures")


class Cars(commands.GroupCog, group_name=commandconfig.cars_group):
    """
    View and manage your carfigures collection.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command(
        name=commandconfig.garage_name,
        description=commandconfig.garage_desc
    )
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def garage(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User | None = None,
        sort: SortingChoices | None = None,
        reverse: bool = False,
        carfigure: CarEnabledTransform | None = None,
        event: EventTransform | None = None,
        exclusive: ExclusiveTransform | None = None
        
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
        event: Event
            Filter the list for a specific event
        exclusive: Exclusive
            Filter the list for an exclusive card
        """
        # simple variables
        player_obj = user or interaction.user
        await interaction.response.defer(thinking=True)

        try:
            player = await Player.get(discord_id=player_obj.id)
        except DoesNotExist:
            pov = f"{player_obj.name} doesn't" if user else "You don't"
            await interaction.followup.send(
                f"{pov} have any {appearance.collectible_plural} yet.",
                ephemeral=True,
            )
            return

        # Seeing if the player's garage is private.
        if player is not None:
            if (
                await inventory_privacy(self.bot, interaction, player, player_obj)
                is False
            ):
                return

        await player.fetch_related("cars")
        filters = {"car__id": carfigure.pk} if carfigure else {}
        if event:
            filters["event"] = event
        if exclusive:
            filters["exclusive"] = exclusive
        
        # Having match statement to filter the garage
        # based on the player sorting selection
        match sort:
            case SortingChoices.duplicates:
                carfigures = await player.cars.filter(**filters)
                count = defaultdict(int)
                for car in carfigures:
                    count[car.carfigure.pk] += 1
                carfigures.sort(key=lambda m: (-count[m.carfigure.pk], m.carfigure.pk))
            case SortingChoices.favorite:
                carfigures = await player.cars.filter(**filters).order_by("-favorite")
            case SortingChoices.stats_bonus:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(
                    key=lambda carfigure: carfigure.weight_bonus + carfigure.horsepower_bonus,
                    reverse=True,
                )
            case SortingChoices.weight:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda carfigure: carfigure.weight, reverse=True)
            case SortingChoices.horsepower:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(key=lambda carfigure: carfigure.horsepower, reverse=True)
            case SortingChoices.total_stats:
                carfigures = await player.cars.filter(**filters)
                carfigures.sort(
                    key=lambda carfigure: carfigure.weight + carfigure.horsepower,
                    reverse=True,
                )
            case _:
                if sort:
                    carfigures = await player.cars.filter(**filters).order_by(sort.value)
                else:
                    carfigures = await player.cars.filter(**filters).order_by("-favorite")

        # Error Handling where the player chooses a car 
        # he doesn't have or has no cars in general
        if not carfigures:
            car = carfigure.full_name if carfigure else ""
            pov = "You don't" if player_obj == interaction.user else f"{player_obj.display_name} doesn't"
            await interaction.followup.send(
                f"{pov} have any {car} {appearance.collectible_plural} yet."
            )
        if reverse:
            carfigures.reverse()

        # Starting the Dropdown menu
        paginator = CarFiguresViewer(interaction, carfigures)
        if player_obj == interaction.user:
            await paginator.start()
        else:
            await paginator.start(content=f"Viewing {player_obj.name}'s garage!")

    @app_commands.command(
        name=commandconfig.exhibit_name,
        description=commandconfig.exhibit_desc
    )
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def exhibit(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
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
        event: Event
            The event you want to see the showroom of
        exclusive: Exclusive
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
                    f"{player_obj.name} doesn't have any {appearance.collectible_plural} yet."
                )
                return
            if (
                await inventory_privacy(self.bot, interaction, player, player_obj)
                is False
            ):
                return
        # Filter disabled cars, they do not count towards progression
        # Only ID and emoji is interesting for us
        bot_carfigures = {
            emoji: carfigure.emoji_id
            for emoji, carfigure in cars.items()
            if carfigure.enabled
        }

        # Set of car IDs owned by the user
        filters = {"player__discord_id": player_obj.id, "car__enabled": True}
        if event:
            filters["event"] = event
            bot_carfigures = {
                emoji: carfigure.emoji_id
                for emoji, carfigure in cars.items()
                if carfigure.enabled and carfigure.created_at < event.end_date
            }
        if not bot_carfigures:
            await interaction.response.send_message(
                f"There are no {appearance.collectible_plural} registered on this bot yet.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(thinking=True)

        if exclusive is not None:
            filters["exclusive"] = exclusive
            bot_carfigures = {
                emoji: carfigure.emoji_id
                for emoji, carfigure in cars.items()
                if carfigure.enabled
            }
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
                f"⋄ Owned {appearance.collectible_plural} | {len(owned_carfigures) if owned_carfigures else 'Zero'} total",
                set(bot_carfigures[carfigure] for carfigure in owned_carfigures),
            )
        else:
            entries.append((
                f"__**Owned {appearance.collectible_plural.title()}s**__",
                "Nothing yet.",
            ))
        # Getting the list of emoji IDs of any carfigures not owned by the player
        if missing := set(
            emoji
            for carfigure, emoji in bot_carfigures.items()
            if carfigure not in owned_carfigures
        ):
            fill_fields(
                f"⋄ Missing {appearance.collectible_plural.title()}s | {len(missing) if missing else 'Zero'} total",
                missing,
            )
        else:
            entries.append((
                f"__**:partying_face: No missing {appearance.collectible_plural}, "
                "congratulations! :partying_face:**__",
                "\u200b",
            ))  # force empty field value
        # Running a pager to navigate between pages of Emoji IDs
        source = FieldPageSource(
            entries, per_page=5, inline=False, clear_description=False
        )
        event_str = f" | {event.name} " if event else ""
        exclusive_str = f" | {exclusive.name} " if exclusive else ""
        source.embed.description = (
            f"**⊾ {settings.bot_name}{event_str}{exclusive_str} Progression: "
            f"{round(len(owned_carfigures) / len(bot_carfigures) * 100, 1)}% | {len(owned_carfigures)}/{len(bot_carfigures)}**"
        )
        source.embed.colour = settings.default_embed_color
        source.embed.set_author(
            name=player_obj.display_name, icon_url=player_obj.display_avatar.url
        )

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command(name=commandconfig.show_name, description=commandconfig.show_desc)
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

    @app_commands.command(name=commandconfig.info_name, description=commandconfig.info_desc)
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def info(
        self, interaction: discord.Interaction, carfigure: CarEnabledTransform
    ):
        """
        Display info from a specific carfigure.

        Parameters
        ----------
        carfigure: CarInstance
            The carfigure you want to inspect
        """
        emoji = self.bot.get_emoji(carfigure.emoji_id) or ""

        embed = discord.Embed(
            title=f"{emoji} {carfigure.full_name} Information:",
            description=(
                f"**⋄ Short Name:** {carfigure.short_name}\n"
                f"**⋄ Catch Names:** {''.join(carfigure.catch_names)}\n"
                f"**⋄ {appearance.cartype}:** {carfigure.cached_cartype.name}\n"
                f"**⋄ {appearance.country}:** {carfigure.cached_country.name if carfigure.cached_country else 'None'}\n"
                f"**⋄ Rarity:** {carfigure.rarity}\n"
                f"**⋄ {appearance.horsepower}:** {carfigure.horsepower}\n"
                f"**⋄ {appearance.weight}:** {carfigure.weight}\n"
                f"**⋄ Capacity Name:** {carfigure.capacity_name}\n"
                f"**⋄ Capacity Description:** {carfigure.capacity_description}\n"
                f"**⋄ Image Credits:** {carfigure.image_credits}\n"
                f"**⋄ {appearance.collectible_singular.title()} Suggester:** {carfigure.car_suggester}"
            ),
            color=settings.default_embed_color,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name=commandconfig.last_name, description=commandconfig.last_desc)
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def last(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ):
        """
        Display info of your or another users last caught carfigure.

        Parameters
        ----------
        user: discord.Member
            The user you would like to see
        """
        player_obj = user or interaction.user
        await interaction.response.defer(thinking=True)
        # Try to check if the player have any carfigures
        try:
            player = await Player.get(discord_id=player_obj.id)
        except DoesNotExist:
            pov = f"{player_obj.display_name} doesn't" if user else "You don't"
            await interaction.followup.send(
                f"{pov} have any {appearance.collectible_plural} yet.",
                ephemeral=True,
            )
            return

        if user is not None:
            if (
                await inventory_privacy(self.bot, interaction, player, player_obj)
                is False
            ):
                return
        # Sort the cars in the player inventory by -id which means by id but reversed
        # Then Selects the first car in that list
        carfigure = (
            await player.cars.all().order_by("-id").first().select_related("car")
        )
        if not carfigure:
            pov = (
                f"{player_obj.display_name} doesn't" if player is None else "You don't"
            )
            await interaction.followup.send(
                f"{pov} have any {appearance.collectible_plural} yet.",
                ephemeral=True,
            )
            return

        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command(
        name=commandconfig.favorite_name,
        description=commandconfig.favorite_desc
    )
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
        user = interaction.user
        if not carfigure.favorite:
            player = await Player.get(discord_id=user.id).prefetch_related("cars")

            # Checks if the amount of the cars that have been favorited equals to the limit
            if (
                await player.cars.filter(favorite=True).count()
                >= settings.max_favorites
            ):
                await interaction.response.send_message(
                    f"You cannot set more than {settings.max_favorites} "
                    f"favorite {appearance.collectible_plural}.",
                    ephemeral=True,
                )
                return
            # Sends a request to favorite the car and saves it in the database
            carfigure.favorite = True  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji_id) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.full_name} "
                f"is now a favorite {appearance.collectible_singular}!",
                ephemeral=True,
            )
        # Unfavorite the carfigure
        else:
            carfigure.favorite = False  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji_id) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.full_name} "
                f"isn't a favorite {appearance.collectible_singular} anymore.",
                ephemeral=True,
            )

    @app_commands.command(
        name=commandconfig.gift_name, description=commandconfig.gift_desc
    )
    async def gift(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        carfigure: CarInstanceTransform,
    ):
        """
        Gift a carfigure to a user.

        Parameters
        ----------
        user: discord.User
            The user you want to gift the carfigure to
        carfigure: CarInstance
            The carfigure you're gifting
        """
        if not carfigure.is_tradeable:
            await interaction.response.send_message(
                f"You cannot gift this {appearance.collectible_singular}.",
                ephemeral=True,
            )
            return
        if user.bot:
            await interaction.response.send_message(
                "You cannot gift to bots.", ephemeral=True
            )
            return
        if await carfigure.is_locked():
            await interaction.response.send_message(
                f"This {appearance.collectible_singular} is currently locked for a trade. "
                "Please try again later."
            )
            return
        await carfigure.lock_for_trade()
        new_player, _ = await Player.get_or_create(discord_id=user.id)
        old_player = carfigure.player

        if new_player == old_player:
            await interaction.response.send_message(
                f"You cannot gift a {appearance.collectible_singular} to yourself.",
                ephemeral=True,
            )
            await carfigure.unlock()
            return
        if new_player.donation_policy == DonationPolicy.ALWAYS_DENY:
            await interaction.response.send_message(
                "This user does not accept gifts. You can use trades instead.",
                ephemeral=True,
            )
            await carfigure.unlock()
            return
        if new_player.discord_id in self.bot.blacklist_user:
            await interaction.response.send_message(
                "You cannot gift to a blacklisted user", ephemeral=True
            )
            await carfigure.unlock()
            return
        elif new_player.donation_policy == DonationPolicy.APPROVAL_REQUIRED:
            await interaction.response.send_message(
                f"Hey {user.mention}, {interaction.user.name} wants to gift you "
                f"{carfigure.description(include_emoji=True, bot=self.bot, is_trade=True)}!\n"
                "Do you accept this gift?",
                view=DonationRequest(self.bot, interaction, carfigure, new_player),
            )
            return

        carfigure.player = new_player
        carfigure.trade_player = old_player
        carfigure.favorite = False
        await carfigure.save()

        car = carfigure.description(
            short=True, include_emoji=True, bot=self.bot, is_trade=False
        )

        await interaction.response.send_message(
            f"You just gifted the {car} to {user.mention}!"
        )
        await carfigure.unlock()

    @app_commands.command(
        name=commandconfig.count_name, description=commandconfig.count_desc
    )
    async def count(
        self,
        interaction: discord.Interaction,
        carfigure: CarEnabledTransform | None = None,
        event: EventEnabledTransform | None = None,
        exclusive: ExclusiveTransform | None = None,
        current_server: bool = False,
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
            The exclusive card you want to count
        current_server: bool
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
        if exclusive:
            filters["exclusive"] = exclusive
        if event:
            filters["event"] = event
        if current_server:
            filters["server_id"] = interaction.guild.id
        filters["player__discord_id"] = interaction.user.id
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Entering the filter selected in the bot then give back info based on it
        cars = await CarInstance.filter(**filters).count()
        full_name = f"{carfigure.full_name} " if carfigure else ""
        collectible = (
            f"{appearance.collectible_singular}"
            if cars == 1
            else f"{appearance.collectible_plural}"
        )
        exclusive_str = f"{exclusive.name} " if exclusive else ""
        event_str = f"{event.name} " if event else ""
        guild = f" caught in {interaction.guild.name}" if current_server else ""
        await interaction.followup.send(
            f"You have {cars} {event_str}{exclusive_str}"
            f"{full_name}{collectible}{guild}."
        )

    @app_commands.command(
        name=commandconfig.rarity_name, description=commandconfig.rarity_desc
    )
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def rarity(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
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
            collectible_names = "\n".join([
                f"\u200b ⋄ {self.bot.get_emoji(c.emoji_id) or 'N/A'} {c.full_name}"
                for c in rarity_to_collectibles[rarity]
            ])
            entry = (f"∥ Rarity: {rarity}", f"{collectible_names}")
            entries.append(entry)

        # Starting the Pager
        per_page = 2  # Number of collectibles displayed on one page
        source = FieldPageSource(
            entries, per_page=per_page, inline=False, clear_description=False
        )
        source.embed.title = f"{settings.bot_name} Rarity List"
        source.embed.colour = settings.default_embed_color
        pages = Pages(source=source, interaction=interaction, compact=False)
        await pages.start()

    @app_commands.command(
        name=commandconfig.compare_name, description=commandconfig.compare_desc
    )
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
        player_obj = interaction.user
        await interaction.response.defer(thinking=True)
        assert interaction.guild

        # Making a placeholder for the player, and if statements to make sure it works perfectly
        player = await Player.get(discord_id=player_obj.id)
        if not player:
            await interaction.response.send_message(
                f"You do not have any {appearance.collectible_plural} yet.",
                ephemeral=True,
            )
            return

        if first == second:
            await interaction.response.send_message(
                f"You can't compare identical {appearance.collectible_plural}."
            )

        # Creating an Embed to hold all these
        embed = discord.Embed(
            title=f"❖ {player_obj.display_name} Comparison!",
            description=f"⊰ **{first.carfigure.full_name} vs. {second.carfigure.full_name} ⊱**",
            colour=settings.default_embed_color,
        )

        embed.add_field(
            name="◊ Name",
            value=f""
            f"• ID\n"
            f"• {appearance.cartype}\n"
            f"• {appearance.country}\n"
            f"• Rarity\n"
            f"• {appearance.horsepower}\n"
            f"• {appearance.horsepower} Bonus\n"
            f"• {appearance.weight}\n"
            f"• {appearance.weight} Bonus\n"
            f"• Catch Date",
            inline=True,
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(first.carfigure.emoji_id) or 'N/A'} **{first.carfigure.short_name}**\n",
            value=f"≛ {first.pk}\n"
            f"≛ {first.carfigure.cached_cartype.name}\n"
            f"≛ {first.carfigure.cached_country.name if first.carfigure.cached_country else 'None'}\n"
            f"≛ {first.carfigure.rarity}\n"
            f"≛ {first.horsepower}\n"
            f"≛ {first.horsepower_bonus}\n"
            f"≛ {first.carfigure.weight}\n"
            f"≛ {first.weight_bonus}\n"
            f"≛ {format_dt(first.catch_date, style='R') if first.catch_date else 'N/A'}\n",
            inline=True,
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(second.carfigure.emoji_id) or 'N/A'} **{second.carfigure.short_name}**",
            value=f"≛ {second.pk}\n"
            f"≛ {second.carfigure.cached_cartype.name}\n"
            f"≛ {second.carfigure.cached_country.name if second.carfigure.cached_country else 'None'}\n"
            f"≛ {second.carfigure.rarity}\n"
            f"≛ {second.horsepower}\n"
            f"≛ {second.horsepower_bonus}\n"
            f"≛ {second.weight}\n"
            f"≛ {second.weight_bonus}\n"
            f"≛ {format_dt(second.catch_date, style='R') if second.catch_date else 'N/A'}\n",
            inline=True,
        )

        embed.set_footer(
            text=f"Requested by {player_obj.display_name}",
            icon_url=player_obj.display_avatar.url,
        )

        await interaction.followup.send(embed=embed)
