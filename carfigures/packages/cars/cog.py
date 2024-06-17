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
    Event,
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
    CarTypeTransform,
    CountryTransform,
    EventEnabledTransform,
    EventTransform,
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

class Cars(commands.GroupCog, group_name=settings.group_cog_names["cars"]):
    """
    View and manage your carfigures collection.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @app_commands.command(
        name=settings.command_names["garage"],
        description=settings.command_descs["garage"]
    )
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
        # simple variables
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

        # Seeing if the player's garage is private'
        if player is not None:
            if await inventory_privacy(self.bot, interaction, player, player_obj) is False:
                return

        await player.fetch_related("cars")
        filters = {"car__id": carfigure.pk} if carfigure else {}
        # Having Ifs to filter the garage based on the player selection
        if sort:
            if sort == SortingChoices.duplicates:
                carfigures = await player.cars.filter(**filters)
                count = defaultdict(int)
                for car in carfigures:
                    count[car.carfigure.pk] += 1
                carfigures.sort(key=lambda m: (-count[m.carfigure.pk], m.carfigure.pk))
            elif sort == SortingChoices.favorite:
                carfigures = await player.cars.filter(**filters).order_by("-favorite")
            elif sort == SortingChoices.limited:
                carfigures = await player.cars.filter(**filters).order_by("-limited")
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
        # Error Handling where the player chooses a car he doesn't have or have no cars in general
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
        # Starting the Dropdown menu
        paginator = CarFiguresViewer(interaction, carfigures)
        if player_obj == interaction.user:
            await paginator.start()
        else:
            await paginator.start(
                content=f"Viewing {player_obj.name}'s {settings.collectible_name}s"
            )

    @app_commands.command(
        name=settings.command_names["exhibit"],
        description=settings.command_descs["exhibit"]
    )
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
        if event:
            filters["event"] = event
            bot_carfigures = {
                x: y.emoji_id
                for x, y in cars.items()
                if y.enabled and y.created_at < event.end_date
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
                f"⋄ Owned {settings.collectible_name}s | {len(owned_carfigures) if len(owned_carfigures) > 0 else '0'} total",
                set(bot_carfigures[x] for x in owned_carfigures),
            )
        else:
            entries.append((f"__**Owned {settings.collectible_name.title()}s**__", "Nothing yet."))
        # Getting the list of emoji IDs of any carfigures not owned by the player
        if missing := set(y for x, y in bot_carfigures.items() if x not in owned_carfigures):
            fill_fields(f"⋄ Missing {settings.collectible_name.title()}s | {len(missing) if len(missing) > 0 else '0'} total",
                        missing)
        else:
            entries.append(
                (
                    f"__**:partying_face: No missing {settings.collectible_name}, "
                    "congratulations! :partying_face:**__",
                    "\u200B",
                )
            )  # force empty field value
        # Running a pager to navigate between pages of Emoji IDs
        source = FieldPageSource(entries, per_page=5, inline=False, clear_description=False)
        event_str = f" ({event.name})" if event else ""
        limited_str = " limited" if limited else ""
        source.embed.description = (
            f"**⊾ {settings.bot_name}{event_str}{limited_str} Progression: "
            f"{round(len(owned_carfigures) / len(bot_carfigures) * 100, 1)}% | {len(owned_carfigures)}/{len(bot_carfigures)}**"
        )
        source.embed.colour = settings.default_embed_color
        source.embed.set_author(name=player_obj.display_name, icon_url=player_obj.display_avatar.url)

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command(
        name=settings.command_names["show"],
        description=settings.command_descs["show"]
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def show(
            self,
            interaction: discord.Interaction,
            carfigure: CarInstanceTransform,
            event: EventEnabledTransform | None = None,
            limited: bool | None = None,
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
        if not carfigure:
            return
        await interaction.response.defer(thinking=True)
        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command(
        name=settings.command_names["info"],
        description=settings.command_descs["info"]
    )
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
            emoji = self.bot.get_emoji(carfigure.emoji_id) or ""  # Get emoji or an empty string if not found
            car_info_embed = discord.Embed(
                title=f"{emoji} {carfigure.full_name} Information:",
                description=(
                    f"**⋄ Short Name:** {carfigure.short_name}\n"
                    f"**⋄ Catch Names:** {''.join(carfigure.catch_names)}\n"
                    f"**⋄ {settings.cartype_replacement}:** {carfigure.cached_cartype.name}\n"
                    f"**⋄ {settings.country_replacement}:** {carfigure.cached_country.name}\n"
                    f"**⋄ Rarity:** {carfigure.rarity}\n"
                    f"**⋄ {settings.horsepower_replacement}:** {carfigure.horsepower}\n"
                    f"**⋄ {settings.weight_replacement}:** {carfigure.weight}\n"
                    f"**⋄ Capacity Name:** {carfigure.capacity_name}\n"
                    f"**⋄ Capacity Description:** {carfigure.capacity_description}\n"
                    f"**⋄ Image Credits:** {carfigure.image_credits}\n"
                    f"**⋄ {settings.collectible_name.title()} Suggester:** {carfigure.car_suggester}"
                ),
                color=settings.default_embed_color
            )
        await interaction.response.send_message(embed=car_info_embed)  # Send the car information embed as a response

    @app_commands.command(
        name=settings.command_names["last"],
        description=settings.command_descs["last"]
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
        player_obj = user if user else interaction.user
        await interaction.response.defer(thinking=True)
        # Try to check if the player have any carfigures
        try:
            player = await Player.get(discord_id=player_obj.id)
        except DoesNotExist:
            msg = f"{'You do' if player is None else f'{player_obj.display_name} does'}"
            await interaction.followup.send(
                f"{msg} not have any {settings.collectible_name} yet.",
                ephemeral=True,
            )
            return

        if user is not None:
            if await inventory_privacy(self.bot, interaction, player, player_obj) is False:
                return
        # Sort the cars in the player inventory by -id which means by id but reversed
        # Then Selects the first car in that list
        carfigure = await player.cars.all().order_by("-id").first().select_related("car")
        if not carfigure:
            msg = f"{'You do' if [player] is None else f'{player_obj.display_name} does'}"
            await interaction.followup.send(
                f"{msg} not have any {settings.collectible_name} yet.",
                ephemeral=True,
            )
            return

        content, file = await carfigure.prepare_for_message(interaction)
        await interaction.followup.send(content=content, file=file)
        file.close()

    @app_commands.command(
        name=settings.command_names["favorite"],
        description=settings.command_descs["favorite"]
    )
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
        # Checks if the car is not favorited
        if not carfigure.favorite:
            player = await Player.get(discord_id=interaction.user.id).prefetch_related("cars")
            # Checks if the amount of the cars that have been favorited equals to the limit
            if await player.cars.filter(favorite=True).count() >= settings.max_favorites:
                await interaction.response.send_message(
                    f"You cannot set more than {settings.max_favorites} "
                    f"favorite {settings.collectible_name}s.",
                    ephemeral=True,
                )
                return
            # Sends a request to favorite the car and saves it in the database
            carfigure.favorite = True  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji_id) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.full_name} "
                f"is now a favorite {settings.collectible_name}!",
                ephemeral=True,
            )
        # Unfavorite the carfigure
        else:
            carfigure.favorite = False  # type: ignore
            await carfigure.save()
            emoji = self.bot.get_emoji(carfigure.carfigure.emoji_id) or ""
            await interaction.response.send_message(
                f"{emoji} `#{carfigure.pk:0X}` {carfigure.carfigure.full_name} "
                f"isn't a favorite {settings.collectible_name} anymore.",
                ephemeral=True,
            )

    @app_commands.command(
        name=settings.command_names["give"],
        description=settings.command_descs["give"],
        extras={"trade": TradeCommandType.PICK}
    )
    async def give(
            self,
            interaction: discord.Interaction,
            user: discord.User,
            carfigure: CarInstanceTransform,
            event: EventEnabledTransform | None = None,
            limited: bool | None = None,
    ):
        """
        Give a carfigure to a user.

        Parameters
        ----------
        user: discord.User
            The user you want to give a carfigure to
        carfigure: CarInstance
            The carfigure you're giving away
        event: Event
            Filter the results of autocompletion to an event. Ignored afterwards.
        limited: bool
            Filter the results of autocompletion to limiteds. Ignored afterwards.
        """
        if not carfigure:
            return
        if not carfigure.is_tradeable:
            await interaction.response.send_message(
                f"You cannot donate this {settings.collectible_name}.", ephemeral=True
            )
            return
        if user.bot:
            await interaction.response.send_message("You cannot donate to bots.")
            return
        if await carfigure.is_locked():
            await interaction.response.send_message(
                f"This {settings.collectible_name} is currently locked for a trade. "
                "Please try again later."
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
        if new_player.discord_id in self.bot.blacklist_user:
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

        carfigure.player = new_player
        carfigure.trade_player = old_player
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

    @app_commands.command(
        name=settings.command_names["count"],
        description=settings.command_descs["count"]
    )
    async def count(
            self,
            interaction: discord.Interaction,
            carfigure: CarEnabledTransform | None = None,
            event: EventEnabledTransform | None = None,
            limited: bool | None = None,
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
        limited: bool
            Whether you want to count limited carfigures
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
        if limited is not None:
            filters["limited"] = limited
        if event:
            filters["event"] = event
        if current_server:
            filters["server_id"] = interaction.guild.id
        filters["player__discord_id"] = interaction.user.id
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Entering the filter selected in the bot then give back info based on it
        cars = await CarInstance.filter(**filters).count()
        full_name = f"{carfigure.full_name} " if carfigure else ""
        plural = "s" if cars > 1 or cars == 0 else ""
        limited_str = "limited " if limited else ""
        event_str = f"{event.name} " if event else ""
        guild = f" caught in {interaction.guild.name}" if current_server else ""
        await interaction.followup.send(
            f"You have {cars} {event_str}{limited_str}"
            f"{full_name}{settings.collectible_name}{plural}{guild}."
        )

    @app_commands.command(
        name=settings.command_names["rarity"],
        description=settings.command_descs["rarity"]
    )
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
            collectible_names = "\n".join([f"\u200B ⋄ {self.bot.get_emoji(c.emoji_id) or 'N/A'} {c.full_name}" for c in
                                           rarity_to_collectibles[rarity]])
            entry = (f"∥ Rarity: {rarity}", f"{collectible_names}")
            entries.append(entry)

        # Starting the Pager
        per_page = 2  # Number of collectibles displayed on one page
        source = FieldPageSource(entries, per_page=per_page, inline=False, clear_description=False)
        source.embed.title = f"{settings.bot_name} Rarity List"
        source.embed.colour = settings.default_embed_color
        pages = Pages(source=source, interaction=interaction, compact=False)
        await pages.start()

    @app_commands.command(
        name=settings.command_names["compare"],
        description=settings.command_descs["compare"]
    )
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def compare(
            self,
            interaction: discord.Interaction,
            first: CarInstanceTransform,
            second: CarInstanceTransform
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
                f"You do not have any {settings.collectible_name} yet.",
                ephemeral=True,
            )
            return

        if not first or not second:
            await interaction.response.send_message(
                f"Please provide a car for first or second",
                ephemeral=True,
            )
            return

        # Creating an Embed to hold all these
        embed = discord.Embed(
            title=f"❖ {player_obj.display_name} Comparison!",
            description=f"⊰ **{first.carfigure.full_name} vs. {second.carfigure.full_name} ⊱**",
            colour=settings.default_embed_color
        )

        embed.add_field(
            name=f"◊ Name",
            value=f""
                  f"• ID\n"
                  f"• {settings.cartype_replacement}\n"
                  f"• {settings.country_replacement}\n"
                  f"• Rarity\n"
                  f"• {settings.horsepower_replacement}\n"
                  f"• {settings.horsepower_replacement} Bonus\n"
                  f"• {settings.weight_replacement}\n"
                  f"• {settings.weight_replacement} Bonus\n"
                  f"• Catch Date",
            inline=True,
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(first.carfigure.emoji_id) or 'N/A'} **{first.carfigure.full_name}**\n",
            value=f""
                  f"≛ {first.id}\n"
                  f"≛ {first.carfigure.cached_cartype.name}\n"
                  f"≛ {first.carfigure.cached_country.name}\n"
                  f"≛ {first.carfigure.rarity}\n"
                  f"≛ {first.horsepower}\n"
                  f"≛ {first.horsepower_bonus}\n"
                  f"≛ {first.carfigure.weight}\n"
                  f"≛ {first.weight_bonus}\n"
                  f"≛ {format_dt(first.catch_date, style='R') if first.catch_date else 'N/A'}\n",
            inline=True
        )
        embed.add_field(
            name=f"◊ {self.bot.get_emoji(second.carfigure.emoji_id) or 'N/A'} **{second.carfigure.full_name}**",
            value=
            f"≛ {second.id}\n"
            f"≛ {second.carfigure.cached_cartype.name}\n"
            f"≛ {second.carfigure.cached_country.name}\n"
            f"≛ {second.carfigure.rarity}\n"
            f"≛ {second.horsepower}\n"
            f"≛ {second.horsepower_bonus}\n"
            f"≛ {second.weight}\n"
            f"≛ {second.weight_bonus}\n"
            f"≛ {format_dt(second.catch_date, style='R') if second.catch_date else 'N/A'}\n",
            inline=True
        )

        embed.set_footer(
            text=f"Requested by {player_obj.display_name}",
            icon_url=player_obj.display_avatar.url
        )

        await interaction.followup.send(embed=embed)
