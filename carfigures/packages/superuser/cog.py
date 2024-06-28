import asyncio
import datetime
import logging
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button
from discord.utils import format_dt
from tortoise.exceptions import BaseORMException, DoesNotExist, IntegrityError
from tortoise.expressions import Q

from carfigures.core.models import (
    Car,
    CarInstance,
    BlacklistedGuild,
    BlacklistedUser,
    GuildConfig,
    Player,
    Trade,
    TradeObject,
)
from carfigures.core.utils.buttons import ConfirmChoiceView
from carfigures.core.utils.enums import DONATION_POLICY_MAP, PRIVATE_POLICY_MAP
from carfigures.core.utils.logging import log_action
from carfigures.core.utils.paginator import FieldPageSource, Pages, TextPageSource
from carfigures.core.utils.transformers import (
    CarTransform,
    CarTypeTransform,
    CountryTransform,
    EventTransform,
)
from carfigures.packages.carfigures.carfigure import CarFigure
from carfigures.packages.trade.display import TradeViewFormat, fill_trade_embed_fields
from carfigures.packages.trade.trade_user import TradingUser
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot
    from carfigures.packages.carfigures.cog import CarFiguresSpawner

log = logging.getLogger("carfigures.packages.superuser.cog")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")


async def save_file(attachment: discord.Attachment) -> Path:
    path = Path(f"./static/uploads/{attachment.filename}")
    match = FILENAME_RE.match(attachment.filename)
    if not match:
        raise TypeError("The file you uploaded lacks an extension.")
    i = 1
    while path.exists():
        path = Path(f"./static/uploads/{match.group(1)}-{i}{match.group(2)}")
        i = i + 1
    await attachment.save(path)
    return path


@app_commands.guilds(*settings.superuser_guild_ids)
@app_commands.default_permissions(administrator=True)
class SuperUser(commands.GroupCog, group_name=settings.group_cog_names["superuser"]):
    """
    Bot admin commands.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot
        self.blacklist_user.parent = self.__cog_app_commands_group__
        self.cars.parent = self.__cog_app_commands_group__

    blacklist_user = app_commands.Group(name="blacklistuser", description="User blacklist management")
    blacklist_guild = app_commands.Group(
        name="blacklistguild", description="Guild blacklist management"
    )
    cars = app_commands.Group(
        name=settings.group_cog_names["cars"], description="s management"
    )
    logs = app_commands.Group(name="logs", description="Bot logs management")
    history = app_commands.Group(name="history", description="Trade history management")
    info = app_commands.Group(name=settings.group_cog_names["info"], description="Information Commands")

    @app_commands.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def status(
        self,
        interaction: discord.Interaction,
        status: discord.Status | None = None,
        name: str | None = None,
        state: str | None = None,
        activity_type: discord.ActivityType | None = None,
    ):
        """
        Change the status of the bot. Provide at least status or text.

        Parameters
        ----------
        status: discord.Status
            The status you want to set
        name: str
            Title of the activity, if not custom
        state: str
            Custom status or subtitle of the activity
        activity_type: discord.ActivityType
            The type of activity
        """
        if not status and not name and not state:
            await interaction.response.send_message(
                "You must provide at least `status`, `name` or `state`.", ephemeral=True
            )
            return

        activity: discord.Activity | None = None
        status = status or discord.Status.online
        activity_type = activity_type or discord.ActivityType.custom

        if activity_type == discord.ActivityType.custom and name and not state:
            await interaction.response.send_message(
                "You must provide `state` for custom activities. `name` is unused.", ephemeral=True
            )
            return
        if activity_type != discord.ActivityType.custom and not name:
            await interaction.response.send_message(
                "You must provide `name` for pre-defined activities.", ephemeral=True
            )
            return
        if name or state:
            activity = discord.Activity(name=name or state, state=state, type=activity_type)
        await self.bot.change_presence(status=status, activity=activity)
        await interaction.response.send_message("Status updated.", ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def rarity(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        chunked: bool = True,
        include_disabled: bool = False,
        ):
        """
        Generate a list of carfigures ranked by rarity.

        Parameters
        ----------
        chunked: bool
            Group together carfigures with the same rarity.
        include_disabled: bool
            Include the carfigures that are disabled or with a rarity of 0.
        """
        text = ""
        cars_queryset = Car.all().order_by("rarity")
        if not include_disabled:
            cars_queryset = cars_queryset.filter(rarity__gt=0, enabled=True)
        sorted_cars = await cars_queryset

        if chunked:
            indexes: dict[float, list[Car]] = defaultdict(list)
            for car in sorted_cars:
                indexes[car.rarity].append(car)
            i = 1
            for chunk in indexes.values():
                for car in chunk:
                    text += f"{i}. {car.full_name}\n"
                i += len(chunk)
        else:
            for i, car in enumerate(sorted_cars, start=1):
                text += f"{i}. {car.full_name}\n"

        source = TextPageSource(text, prefix="```md\n", suffix="```")
        pages = Pages(source=source, interaction=interaction, compact=True)
        pages.remove_item(pages.stop_pages)
        await pages.start(ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def cooldown(
        self,
        interaction: discord.Interaction,
        guild_id: str | None = None,
    ):
        """
        Show the details of the spawn cooldown system for the given server

        Parameters
        ----------
        guild_id: int | None
            ID of the server you want to inspect. If not given, inspect the current server.
        """
        if guild_id:
            try:
                guild = self.bot.get_guild(int(guild_id))
            except ValueError:
                await interaction.response.send_message(
                    "Invalid guild ID. Please make sure it's a number.", ephemeral=True
                )
                return
        else:
            guild = interaction.guild
        if not guild or not guild.member_count:
            await interaction.response.send_message(
                "The given guild could not be found.", ephemeral=True
            )
            return

        spawn_manager = cast(
            "CarFiguresSpawner", self.bot.get_cog("CarFiguresSpawner")
        ).spawn_manager
        cooldown = spawn_manager.cooldowns.get(guild.id)
        if not cooldown:
            await interaction.response.send_message(
                "No spawn manager could be found for that guild. Spawn may have been disabled.",
                ephemeral=True,
            )
            return

        embed = discord.Embed()
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.colour = discord.Colour.orange()

        delta = (interaction.created_at - cooldown.time).total_seconds()
        # change how the threshold varies according to the member count, while nuking farm servers
        if guild.member_count < 5:
            multiplier = 0.1
            range = "1-4"
        elif guild.member_count < 100:
            multiplier = 0.8
            range = "5-99"
        elif guild.member_count < 1000:
            multiplier = 0.5
            range = "100-999"
        else:
            multiplier = 0.2
            range = "1000+"

        penalties: list[str] = []
        if guild.member_count < 5 or guild.member_count > 1000:
            penalties.append("Server has less than 5 or more than 1000 members")
        if any(len(x.content) < 5 for x in cooldown.message_cache):
            penalties.append("Some cached messages are less than 5 characters long")

        authors_set = set(x.author_id for x in cooldown.message_cache)
        low_chatters = len(authors_set) < 4
        # check if one author has more than 40% of messages in cache
        major_chatter = any(
            (
                len(list(filter(lambda x: x.author_id == author, cooldown.message_cache)))
                / cooldown.message_cache.maxlen  # type: ignore
                > 0.4
            )
            for author in authors_set
        )
        # this mess is needed since either conditions make up to a single penality
        if low_chatters:
            if not major_chatter:
                penalties.append("Message cache has less than 4 chatters")
            else:
                penalties.append(
                    "Message cache has less than 4 chatters **and** "
                    "one user has more than 40% of messages within message cache"
                )
        elif major_chatter:
            if not low_chatters:
                penalties.append("One user has more than 40% of messages within cache")

        penality_multiplier = 0.5 ** len(penalties)
        if penalties:
            embed.add_field(
                name="\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Penalties",
                value="Each penality divides the progress by 2\n\n- " + "\n- ".join(penalties),
            )

        chance = cooldown.chance - multiplier * (delta // 60)

        embed.description = (
            f"Manager initiated **{format_dt(cooldown.time, style='R')}**\n"
            f"Initial number of points to reach: **{cooldown.chance}**\n"
            f"Message cache length: **{len(cooldown.message_cache)}**\n\n"
            f"Time-based multiplier: **x{multiplier}** *({range} members)*\n"
            "*This affects how much the number of points to reach reduces over time*\n"
            f"Penalty multiplier: **x{penality_multiplier}**\n"
            "*This affects how much a message sent increases the number of points*\n\n"
            f"__Current count: **{cooldown.amount}/{chance}**__\n\n"
        )

        information: list[str] = []
        if cooldown.lock.locked():
            information.append("The manager is currently on cool down.")
        if delta < 600:
            information.append(
                "The manager is less than 10 minutes old, cars cannot spawn at the moment."
            )
        if information:
            embed.add_field(
                name="\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} Information's",
                value="- " + "\n- ".join(information),
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def guilds(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User | None = None,
        user_id: str | None = None,
    ):
        """
        Shows the guilds shared with the specified user. Provide either user or user_id

        Parameters
        ----------
        user: discord.User | None
            The user you want to check, if available in the current server.
        user_id: str | None
            The ID of the user you want to check, if it's not in the current server.
        """
        if (user and user_id) or (not user and not user_id):
            await interaction.response.send_message(
                "You must provide either `user` or `user_id`.", ephemeral=True
            )
            return

        if not user:
            try:
                user = await self.bot.fetch_user(int(user_id))  # type: ignore
            except ValueError:
                await interaction.response.send_message(
                    "The user ID you gave is not valid.", ephemeral=True
                )
                return
            except discord.NotFound:
                await interaction.response.send_message(
                    "The given user ID could not be found.", ephemeral=True
                )
                return

        if self.bot.intents.members:
            guilds = user.mutual_guilds
        else:
            guilds = [x for x in self.bot.guilds if x.owner_id == user.id]

        if not guilds:
            if self.bot.intents.members:
                await interaction.response.send_message(
                    f"The user does not own any server with {settings.bot_name}.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"The user does not own any server with {settings.bot_name}.\n"
                    ":warning: *The bot cannot be aware of the member's presence in servers, "
                    "it is only aware of server ownerships.*",
                    ephemeral=True,
                )
            return

        entries: list[tuple[str, str]] = []
        for guild in guilds:
            if config := await GuildConfig.get_or_none(guild_id=guild.id):
                spawn_enabled = config.enabled and config.guild_id
            else:
                spawn_enabled = False

            field_name = f"`{guild.id}`"
            field_value = ""

            # highlight suspicious server names
            if any(x in guild.name.lower() for x in (
                    "farm", "grind", "spam"
            )):
                field_value += f"- :warning: **{guild.name}**\n"
            else:
                field_value += f"- {guild.name}\n"

            # highlight low member count
            if guild.member_count <= 3:  # type: ignore
                field_value += f"- :warning: **{guild.member_count} members**\n"
            else:
                field_value += f"- {guild.member_count} members\n"

            # highlight if spawning is enabled
            if spawn_enabled:
                field_value += "- :warning: **Spawn is enabled**"
            else:
                field_value += "- Spawn is disabled"

            entries.append((field_name, field_value))

        source = FieldPageSource(entries, per_page=25, inline=True)
        source.embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)

        if len(guilds) > 1:
            source.embed.title = f"{len(guilds)} servers shared"
        else:
            source.embed.title = "1 server shared"

        if not self.bot.intents.members:
            source.embed.set_footer(
                text="\N{WARNING SIGN} The bot cannot be aware of the member's "
                "presence in servers, it is only aware of server ownerships."
            )

        pages = Pages(source=source, interaction=interaction, compact=True)
        pages.add_item(
            Button(
                style=discord.ButtonStyle.link,
                label="View profile",
                url=f"discord://-/users/{user.id}",
                emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
            )
        )
        await pages.start(ephemeral=True)

    async def _spawn_bomb(
        self,
        interaction: discord.Interaction,
        carfigure: Car | None,
        channel: discord.TextChannel,
        n: int,
    ):
        spawned = 0

        async def update_message_loop():
            nonlocal spawned
            for i in range(5 * 12 * 10):  # timeout progress after 10 minutes
                await interaction.followup.edit_message(
                    "@original",  # type: ignore
                    content=f"Spawn bomb in progress in {channel.mention}, "
                    f"{settings.collectible_name.title()}: {carfigure or 'Random'}\n"
                    f"{spawned}/{n} spawned ({round((spawned/n)*100)}%)",
                )
                await asyncio.sleep(5)
            await interaction.followup.edit_message(
                "@original", content="Spawn bomb seems to have timed out."  # type: ignore
            )

        await interaction.response.send_message(f"Starting spawn bomb in {channel.mention}...")
        task = self.bot.loop.create_task(update_message_loop())
        try:
            for i in range(n):
                if not carfigure:
                    car = await CarFigure.get_random()
                else:
                    car = CarFigure(carfigure)
                result = await car.spawn(channel)
                if not result:
                    task.cancel()
                    await interaction.followup.edit_message(
                        "@original",  # type: ignore
                        content=f"A {settings.collectible_name} failed to spawn, probably "
                        "indicating a lack of permissions to send messages "
                        f"or upload files in {channel.mention}.",
                    )
                    return
                spawned += 1
            task.cancel()
            await interaction.followup.edit_message(
                "@original",  # type: ignore
                content=f"Successfully spawned {spawned} {settings.collectible_name}s "
                f"in {channel.mention}!",
            )
        finally:
            task.cancel()

    @cars.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def spawn(
        self,
        interaction: discord.Interaction,
        carfigure: CarTransform | None = None,
        channel: discord.TextChannel | None = None,
        n: int = 1,
    ):
        """
        Force spawn a random or specified car.

        Parameters
        ----------
        car: Car | None
            The carfigure you want to spawn. Random according to rarities if not specified.
        channel: discord.TextChannel | None
            The channel you want to spawn the carfigure in. Current channel if not specified.
        n: int
            The number of carfigures to spawn. If no carfigure was specified, it's random
            every time.
        """
        # the transformer triggered a response, meaning user tried an incorrect input
        if interaction.response.is_done():
            return

        if n < 1:
            await interaction.response.send_message(
                "`n` must be superior or equal to 1.", ephemeral=True
            )
            return
        if n > 100:
            await interaction.response.send_message(
                f"That doesn't seem reasonable to spawn {n} times, "
                "the bot will be rate-limited. Try something lower than 100.",
                ephemeral=True,
            )
            return

        if n > 1:
            await self._spawn_bomb(
                interaction, carfigure, channel or interaction.channel, n  # type: ignore
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        if not carfigure:
            car = await CarFigure.get_random()
        else:
            car = CarFigure(carfigure)
        result = await car.spawn(channel or interaction.channel)  # type: ignore

        if result:
            await interaction.followup.send(
                f"{settings.collectible_name.title()} spawned.", ephemeral=True
            )
            await log_action(
                f"{interaction.user} spawned {settings.collectible_name} {car.name} "
                f"in {channel or interaction.channel}.",
                self.bot,
            )

    @cars.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def give(
        self,
        interaction: discord.Interaction,
        car: CarTransform,
        user: discord.User,
        amount: int | None = 1,
        event: EventTransform | None = None,
        limited: bool | None = None,
        weight_bonus: int | None = None,
        horsepower_bonus: int | None = None,
    ):
        """
        Give the specified carfigure to a player.

        Parameters
        ----------
        car: Car
        user: discord.User
        amount: int
        event: Event | None
        limited: bool
            Omit this to make it random.
        weight_bonus: int | None
            Omit this to make it random (-50/+50%).
        horsepower_bonus: int | None
            Omit this to make it random (-50/+50%).
        """
        # the transformers triggered a response, meaning user tried an incorrect input
        if interaction.response.is_done():
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        player, created = await Player.get_or_create(discord_id=user.id)
        for i in range(amount):
            instance = await CarInstance.create(
                car=car,
                player=player,
                limited=(limited if limited is not None else random.randint(1, 2048) == 1),
                horsepower_bonus=(horsepower_bonus if horsepower_bonus is not None else random.randint(-50, 50)),
                weight_bonus=(weight_bonus if weight_bonus is not None else random.randint(-50, 50)),
                event=event,
            )
        await interaction.followup.send(
            f"`{amount}``{car.full_name + 's' if amount > 1 else car.full_name}` {settings.collectible_name} was successfully given to `{user}`.\n"
            f"Event: `{event.name if event else None}` • `{settings.hp_replacement}`:`{instance.horsepower_bonus:+d}` • "
            f"{settings.kg_replacement}:`{instance.weight_bonus:+d}` • Limited: `{instance.limited}`"
        )
        await log_action(
            f"{interaction.user} gave {amount} {settings.collectible_name} {car.full_name + 's' if amount > 1 else car.full_name} to {user}. "
            f"Event={event.name if event else None} {settings.hp_replacement}={instance.horsepower_bonus:+d} "
            f"{settings.kg_replacement}={instance.weight_bonus:+d} limited={instance.limited}",
            self.bot,
        )

    @blacklist_user.command(name="add")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def blacklist_add(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        user_id: str | None = None,
        reason: str | None = None,
    ):
        """
        Add a user to the blacklist. No reload is needed.

        Parameters
        ----------
        user: discord.User | None
            The user you want to blacklist, if available in the current server.
        user_id: str | None
            The ID of the user you want to blacklist, if it's not in the current server.
        reason: str | None
        """
        if (user and user_id) or (not user and not user_id):
            await interaction.response.send_message(
                "You must provide either `user` or `user_id`.", ephemeral=True
            )
            return

        if not user:
            try:
                user = await self.bot.fetch_user(int(user_id))  # type: ignore
            except ValueError:
                await interaction.response.send_message(
                    "The user ID you gave is not valid.", ephemeral=True
                )
                return
            except discord.NotFound:
                await interaction.response.send_message(
                    "The given user ID could not be found.", ephemeral=True
                )
                return

        final_reason = (
            f"{reason}\nDone through the bot by {interaction.user} ({interaction.user.id})"
        )

        try:
            await BlacklistedUser.create(discord_id=user.id, reason=final_reason)
        except IntegrityError:
            await interaction.response.send_message(
                "That user was already blacklisted.", ephemeral=True
            )
        else:
            self.bot.blacklist_user.add(user.id)
            await interaction.response.send_message("User is now blacklisted.", ephemeral=True)
        await log_action(
            f"{interaction.user} blacklisted {user} ({user.id})"
            f" for the following reason: {reason}",
            self.bot,
        )

    @blacklist_user.command(name="remove")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def blacklist_remove(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        user_id: str | None = None,
    ):
        """
        Remove a user from the blacklist. No reload is needed.

        Parameters
        ----------
        user: discord.User | None
            The user you want to unblacklist, if available in the current server.
        user_id: str | None
            The ID of the user you want to unblacklist, if it's not in the current server.
        """
        if (user and user_id) or (not user and not user_id):
            await interaction.response.send_message(
                "You must provide either `user` or `user_id`.", ephemeral=True
            )
            return

        if not user:
            try:
                user = await self.bot.fetch_user(int(user_id))  # type: ignore
            except ValueError:
                await interaction.response.send_message(
                    "The user ID you gave is not valid.", ephemeral=True
                )
                return
            except discord.NotFound:
                await interaction.response.send_message(
                    "The given user ID could not be found.", ephemeral=True
                )
                return

        try:
            blacklisted = await BlacklistedUser.get(discord_id=user.id)
        except DoesNotExist:
            await interaction.response.send_message("That user isn't blacklisted.", ephemeral=True)
        else:
            await blacklisted.delete()
            self.bot.blacklist_user.remove(user.id)
            await interaction.response.send_message(
                "User is now removed from blacklist.", ephemeral=True
            )
        await log_action(
            f"{interaction.user} removed blacklist for user {user} ({user.id})", self.bot
        )

    @blacklist_user.command(name="info")
    async def blacklist_info(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        user_id: str | None = None,
    ):
        """
        Check if a user is blacklisted and show the corresponding reason.

        Parameters
        ----------
        user: discord.User | None
            The user you want to check, if available in the current server.
        user_id: str | None
            The ID of the user you want to check, if it's not in the current server.
        """
        if (user and user_id) or (not user and not user_id):
            await interaction.response.send_message(
                "You must provide either `user` or `user_id`.", ephemeral=True
            )
            return

        if not user:
            try:
                user = await self.bot.fetch_user(int(user_id))  # type: ignore
            except ValueError:
                await interaction.response.send_message(
                    "The user ID you gave is not valid.", ephemeral=True
                )
                return
            except discord.NotFound:
                await interaction.response.send_message(
                    "The given user ID could not be found.", ephemeral=True
                )
                return
        # We assume that we have a valid discord.User object at this point.

        try:
            blacklisted = await BlacklistedUser.get(discord_id=user.id)
        except DoesNotExist:
            await interaction.response.send_message("That user isn't blacklisted.", ephemeral=True)
        else:
            if blacklisted.date:
                await interaction.response.send_message(
                    f"`{user}` (`{user.id}`) was blacklisted on {format_dt(blacklisted.date)}"
                    f"({format_dt(blacklisted.date, style='R')}) for the following reason:\n"
                    f"{blacklisted.reason}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"`{user}` (`{user.id}`) is currently blacklisted (date unknown)"
                    " for the following reason:\n"
                    f"{blacklisted.reason}",
                    ephemeral=True,
                )

    @blacklist_guild.command(name="add")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def blacklist_add_guild(
        self,
        interaction: discord.Interaction,
        guild_id: str,
        reason: str,
    ):
        """
        Add a guild to the blacklist. No reload is needed.

        Parameters
        ----------
        guild_id: str
            The ID of the guild you want to blacklist.
        reason: str
        """

        try:
            guild = await self.bot.fetch_guild(int(guild_id))  # type: ignore
        except ValueError:
            await interaction.response.send_message(
                "The guild ID you gave is not valid.", ephemeral=True
            )
            return
        except discord.NotFound:
            await interaction.response.send_message(
                "The given guild ID could not be found.", ephemeral=True
            )
            return

        final_reason = f"{reason}\nBy: {interaction.user} ({interaction.user.id})"

        try:
            await BlacklistedGuild.create(discord_id=guild.id, reason=final_reason)
        except IntegrityError:
            await interaction.response.send_message(
                "That guild was already blacklisted.", ephemeral=True
            )
        else:
            self.bot.blacklist_guild.add(guild.id)
            await interaction.response.send_message("Guild is now blacklisted.", ephemeral=True)
        await log_action(
            f"{interaction.user} blacklisted the guild {guild}({guild.id}) "
            f"for the following reason: {reason}",
            self.bot,
        )

    @blacklist_guild.command(name="remove")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def blacklist_remove_guild(
        self,
        interaction: discord.Interaction,
        guild_id: str,
    ):
        """
        Remove a guild from the blacklist. No reload is needed.

        Parameters
        ----------
        guild_id: str
            The ID of the guild you want to unblacklist.
        """

        try:
            guild = await self.bot.fetch_guild(int(guild_id))  # type: ignore
        except ValueError:
            await interaction.response.send_message(
                "The guild ID you gave is not valid.", ephemeral=True
            )
            return
        except discord.NotFound:
            await interaction.response.send_message(
                "The given guild ID could not be found.", ephemeral=True
            )
            return

        try:
            blacklisted = await BlacklistedGuild.get(discord_id=guild.id)
        except DoesNotExist:
            await interaction.response.send_message(
                "That guild isn't blacklisted.", ephemeral=True
            )
        else:
            await blacklisted.delete()
            self.bot.blacklist_guild.remove(guild.id)
            await interaction.response.send_message(
                "Guild is now removed from blacklist.", ephemeral=True
            )
            await log_action(
                f"{interaction.user} removed blacklist for guild {guild} ({guild.id})", self.bot
            )

    @blacklist_guild.command(name="info")
    async def blacklist_info_guild(
        self,
        interaction: discord.Interaction,
        guild_id: str,
    ):
        """
        Check if a guild is blacklisted and show the corresponding reason.

        Parameters
        ----------
        guild_id: str
            The ID of the guild you want to check.
        """

        try:
            guild = await self.bot.fetch_guild(int(guild_id))  # type: ignore
        except ValueError:
            await interaction.response.send_message(
                "The guild ID you gave is not valid.", ephemeral=True
            )
            return
        except discord.NotFound:
            await interaction.response.send_message(
                "The given guild ID could not be found.", ephemeral=True
            )
            return

        try:
            blacklisted = await BlacklistedGuild.get(discord_id=guild.id)
        except DoesNotExist:
            await interaction.response.send_message(
                "That guild isn't blacklisted.", ephemeral=True
            )
        else:
            if blacklisted.date:
                await interaction.response.send_message(
                    f"`{guild}` (`{guild.id}`) was blacklisted on {format_dt(blacklisted.date)}"
                    f"({format_dt(blacklisted.date, style='R')}) for the following reason:\n"
                    f"{blacklisted.reason}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"`{guild}` (`{guild.id}`) is currently blacklisted (date unknown)"
                    " for the following reason:\n"
                    f"{blacklisted.reason}",
                    ephemeral=True,
                )

    @cars.command(name="info")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    async def cars_info(self, interaction: discord.Interaction, car_id: str):
        """
        Show information about a car.

        Parameters
        ----------
        car_id: str
            The ID of the car you want to get information about.
        """
        try:
            pk = int(car_id, 16)
        except ValueError:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave is not valid.", ephemeral=True
            )
            return
        try:
            car = await CarInstance.get(id=pk).prefetch_related(
                "player", "trade_player", "event"
            )
        except DoesNotExist:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave does not exist.", ephemeral=True
            )
            return
        spawned_time = format_dt(car.spawned_time, style="R") if car.spawned_time else "N/A"
        catch_time = (
            (car.catch_date - car.spawned_time).total_seconds()
            if car.catch_date and car.spawned_time
            else "N/A"
        )
        await interaction.response.send_message(
            f"**{settings.collectible_name.title()} ID:** {car.pk}\n"
            f"**Player:** {car.player}\n"
            f"**Name:** {car.carfigure}\n"
            f"**{settings.horsepower_replacement} bonus:** {car.horsepower_bonus}\n"
            f"**{settings.weight_replacement} bonus:** {car.weight_bonus}\n"
            f"**Limited:** {car.limited}\n"
            f"**Event:** {car.event.name if car.event else None}\n"
            f"**Caught at:** {format_dt(car.catch_date, style='R')}\n"
            f"**Spawned at:** {spawned_time}\n"
            f"**Catch time:** {catch_time} seconds\n"
            f"**Caught in:** {car.server_id if car.server_id else 'N/A'}\n"
            f"**Traded:** {car.trade_player}\n",
            ephemeral=True,
        )
        await log_action(f"{interaction.user} got info for {car} ({car.pk})", self.bot)

    @cars.command(name="delete")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def cars_delete(self, interaction: discord.Interaction, car_id: str):
        """
        Delete a car.

        Parameters
        ----------
        car_id: str
            The ID of the car you want to get information about.
        """
        try:
            carIdConverted = int(car_id, 16)
        except ValueError:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave is not valid.", ephemeral=True
            )
            return
        try:
            car = await CarInstance.get(id=carIdConverted)
        except DoesNotExist:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave does not exist.", ephemeral=True
            )
            return
        await car.delete()
        await interaction.response.send_message(
            f"{settings.collectible_name.title()} {car_id} deleted.", ephemeral=True
        )
        await log_action(f"{interaction.user} deleted {car} ({car.pk})", self.bot)

    @cars.command(name="transfer")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def cars_transfer(
        self, interaction: discord.Interaction, car_id: str, user: discord.User
    ):
        """
        Transfer a car to another user.

        Parameters
        ----------
        car_id: str
            The ID of the car you want to get information about.
        user: discord.User
            The user you want to transfer the car to.
        """
        try:
            carIdConverted = int(car_id, 16)
        except ValueError:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave is not valid.", ephemeral=True
            )
            return
        try:
            car = await CarInstance.get(id=carIdConverted).prefetch_related("player")
            original_player = car.player
        except DoesNotExist:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave does not exist.", ephemeral=True
            )
            return
        player, _ = await Player.get_or_create(discord_id=user.id)
        car.player = player
        await car.save()

        trade = await Trade.create(player1=original_player, player2=player)
        await TradeObject.create(trade=trade, carinstance=car, player=original_player)
        await interaction.response.send_message(
            f"Transfered {car} ({car.pk}) from {original_player} to {user}.",
            ephemeral=True,
        )
        await log_action(
            f"{interaction.user} transferred {car} ({car.pk}) from {original_player} to {user}",
            self.bot,
        )

    @cars.command(name="reset")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def cars_reset(
        self, interaction: discord.Interaction, user: discord.User, percentage: int | None = None
    ):
        """
        Reset a player's cars.

        Parameters
        ----------
        user: discord.User
            The user you want to reset the cars of.
        percentage: int | None
            The percentage of cars to delete, if not all. Used for sanctions.
        """
        player = await Player.get(discord_id=user.id)
        if not player:
            await interaction.response.send_message(
                "The user you gave does not exist.", ephemeral=True
            )
            return
        if percentage and not 0 < percentage < 100:
            await interaction.response.send_message(
                "The percentage must be between 1 and 99.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not percentage:
            text = f"Are you sure you want to delete {user}'s {settings.collectible_name}s?"
        else:
            text = (
                f"Are you sure you want to delete {percentage}% of "
                f"{user}'s {settings.collectible_name}s?"
            )
        view = ConfirmChoiceView(interaction)
        await interaction.followup.send(
            text,
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.value:
            return
        if percentage:
            cars = await CarInstance.filter(player=player)
            to_delete = random.sample(cars, int(len(cars) * (percentage / 100)))
            for car in to_delete:
                await car.delete()
            count = len(to_delete)
        else:
            count = await CarInstance.filter(player=player).delete()
        await interaction.followup.send(
            f"{count} {settings.collectible_name}s from {user} have been reset.", ephemeral=True
        )
        await log_action(
            f"{interaction.user} deleted {percentage or 100}% of {player}'s cars", self.bot
        )

    @cars.command(name="count")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def cars_count(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        car: CarTransform | None = None,
        limited: bool | None = None,
        event: EventTransform | None = None,
    ):
        """
        Count the number of cars that a player has or how many exist in total.

        Parameters
        ----------
        user: discord.User
            The user you want to count the cars of.
        car: Car
        limited: bool
        event: Event
        """
        if interaction.response.is_done():
            return
        filters = {}
        if car:
            filters["car"] = car
        if limited is not None:
            filters["limited"] = limited
        if event:
            filters["event"] = event
        if user:
            filters["player__discord_id"] = user.id
        await interaction.response.defer(ephemeral=True, thinking=True)
        cars = await CarInstance.filter(**filters).count()
        full_name = f"{car.full_name} " if car else ""
        plural = "s" if cars > 1 or cars == 0 else ""
        event_str = f"{event.name} " if event else ""
        limited_str = "limited " if limited else ""
        if user:
            await interaction.followup.send(
                f"{user} has {cars} {event_str}{limited_str}"
                f"{full_name}{settings.collectible_name}{plural}."
            )
        else:
            await interaction.followup.send(
                f"There are {cars} {event_str}{limited_str}"
                f"{full_name}{settings.collectible_name}{plural}."
            )

    @cars.command(name="create")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def cars_create(
        self,
        interaction: discord.Interaction,
        *,
        name: app_commands.Range[str, None, 48],
        cartype: CarTypeTransform,
        weight: int,
        horsepower: int,
        emoji_id: app_commands.Range[str, 17, 21],
        capacity_name: app_commands.Range[str, None, 64],
        capacity_description: app_commands.Range[str, None, 256],
        collection_image: discord.Attachment,
        image_credits: str,
        country: CountryTransform | None = None,
        rarity: float = 0.0,
        enabled: bool = False,
        tradeable: bool = False,
        spawn_image: discord.Attachment | None = None,
    ):
        """
        Shortcut command for creating carfigures. They are disabled by default.

        Parameters
        ----------
        name: str
            The name of the carfigure
        cartype: CarType
            The type of the carfigure
        country: Country | None
            The country of the carfigure
        weight: int
            The weight of the carfigure
        horsepower: int
            The horsepower of the carfigure
        emoji_id: str
            An emoji ID, the bot will check if it can access the custom emote
        capacity_name: str
            The name of the carfigure's capacity
        capacity_description: str
            The description of the carfigure's capacity
        collection_image: discord.Attachment
            Artwork used to show the carfigure in the collection
        image_credits: str
            The name of the person who created the artwork
        rarity: float
            Value defining the rarity of this carfigure, if enabled
        enabled: bool
            If true, the carfigure can spawn and will show up in global completion
        tradeable: bool
            If false, all instances are untradeable
        spawn_image: discord.Attachment
            Artwork used to spawn the carfigure, with a default
        """
        if cartype is None or interaction.response.is_done():  # country autocomplete failed
            return

        if not emoji_id.isnumeric():
            await interaction.response.send_message(
                "`emoji_id` is not a valid number.", ephemeral=True
            )
            return
        emoji = self.bot.get_emoji(int(emoji_id))
        if not emoji:
            await interaction.response.send_message(
                "The bot does not have access to the given emoji.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        default_path = Path("./carfigures/core/image_generator/src/default.png")
        missing_default = ""
        if not spawn_image and not default_path.exists():
            missing_default = (
                "**Warning:** The default spawn image is not set. This will result in errors when "
                f"attempting to spawn this {settings.collectible_name}. You can edit this on the "
                "web panel or add an image at `./carfigures/core/image_generator/src/default.png`.\n"
            )

        try:
            collection_image_path = await save_file(collection_image)
        except Exception as e:
            log.exception("Failed saving file when creating carfigure", exc_info=True)
            await interaction.followup.send(
                f"Failed saving the attached file: {collection_image.url}.\n"
                f"Partial error: {', '.join(str(x) for x in e.args)}\n"
                "The full error is in the bot logs."
            )
            return
        try:
            spawn_image_path = await save_file(spawn_image) if spawn_image else default_path
        except Exception as e:
            log.exception("Failed saving file when creating carfigure", exc_info=True)
            await interaction.followup.send(
                f"Failed saving the attached file: {collection_image.url}.\n"
                f"Partial error: {', '.join(str(x) for x in e.args)}\n"
                "The full error is in the bot logs."
            )
            return

        try:
            car = await Car.create(
                full_name=name,
                cartype=cartype,
                country=country,
                weight=weight,
                horsepower=horsepower,
                rarity=rarity,
                enabled=enabled,
                tradeable=tradeable,
                emoji_id=emoji_id,
                spawn_image="/" + str(spawn_image_path),
                collection_image="/" + str(collection_image_path),
                image_credits=image_credits,
                capacity_name=capacity_name,
                capacity_description=capacity_description,
            )
        except BaseORMException as e:
            log.exception("Failed creating carfigure with admin command", exc_info=True)
            await interaction.followup.send(
                f"Failed creating the {settings.collectible_name}.\n"
                f"Partial error: {', '.join(str(x) for x in e.args)}\n"
                "The full error is in the bot logs."
            )
        else:
            files = [await collection_image.to_file()]
            if spawn_image:
                files.append(await spawn_image.to_file())
            await self.bot.load_cache()
            await interaction.followup.send(
                f"Successfully created a {settings.collectible_name} with ID {car.pk}! "
                "The internal cache was reloaded.\n"
                f"{missing_default}\n"
                f"{name=} {settings.cartype_replacement}={cartype.name} {settings.country_replacement}={country.name if country else None} "
                f"{weight=} {horsepower=} {rarity=} {enabled=} {tradeable=} emoji={emoji}",
                files=files,
            )

    @logs.command(name="catchlogs")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def logs_add(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ):
        """
        Add or remove a user from catch logs.

        Parameters
        ----------
        user: discord.User
            The user you want to add or remove to the logs.
        """
        if user.id in self.bot.catch_log:
            self.bot.catch_log.remove(user.id)
            await interaction.response.send_message(
                f"{user} removed from catch logs.", ephemeral=True
            )
        else:
            self.bot.catch_log.add(user.id)
            await interaction.response.send_message(f"{user} added to catch logs.", ephemeral=True)

    @logs.command(name="commandlogs")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def commandlogs_add(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ):
        """
        Add or remove a user from command logs.

        Parameters
        ----------
        user: discord.User
            The user you want to add or remove to the logs.
        """
        if user.id in self.bot.command_log:
            self.bot.command_log.remove(user.id)
            await interaction.response.send_message(
                f"{user} removed from command logs.", ephemeral=True
            )
        else:
            self.bot.command_log.add(user.id)
            await interaction.response.send_message(
                f"{user} added to command logs.", ephemeral=True
            )

    @history.command(name="user")
    @app_commands.checks.has_any_role(*settings.root_role_ids, *settings.superuser_role_ids)
    @app_commands.choices(
        sorting=[
            app_commands.Choice(name="Most Recent", value="-date"),
            app_commands.Choice(name="Oldest", value="date"),
        ]
    )
    async def history_user(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        user: discord.User,
        sorting: app_commands.Choice[str],
        user2: Optional[discord.User] = None,
    ):
        """
        Show the history of a user.

        Parameters
        ----------
        user: discord.User
            The user you want to check the history of.
        sorting: str
            The sorting method you want to use.
        user2: discord.User | None
            The second user you want to check the history of.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        if user2:
            history = (
                await Trade.filter(
                    (Q(player1__discord_id=user.id) & Q(player2__discord_id=user2.id))
                    | (Q(player1__discord_id=user2.id) & Q(player2__discord_id=user.id))
                )
                .order_by(sorting.value)
                .prefetch_related("player1", "player2")
            )

            if not history:
                await interaction.followup.send("No history found.", ephemeral=True)
                return

            source = TradeViewFormat(
                history, f"{user.display_name} and {user2.display_name}", self.bot
            )
        else:
            history = (
                await Trade.filter(Q(player1__discord_id=user.id) | Q(player2__discord_id=user.id))
                .order_by(sorting.value)
                .prefetch_related("player1", "player2")
            )

            if not history:
                await interaction.followup.send("No history found.", ephemeral=True)
                return

            source = TradeViewFormat(history, user.display_name, self.bot)

        pages = Pages(source=source, interaction=interaction)
        await pages.start(ephemeral=True)

    @history.command(name="car")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    @app_commands.choices(
        sorting=[
            app_commands.Choice(name="Most Recent", value="-date"),
            app_commands.Choice(name="Oldest", value="date"),
        ]
    )
    async def history_car(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        carid: str,
        sorting: app_commands.Choice[str],
    ):
        """
        Show the history of a car.

        Parameters
        ----------
        carid: str
            The ID of the car you want to check the history of.
        sorting: str
            The sorting method you want to use.
        """

        try:
            pk = int(carid, 16)
        except ValueError:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave is not valid.", ephemeral=True
            )
            return

        car = await CarInstance.get(id=pk)
        if not car:
            await interaction.response.send_message(
                f"The {settings.collectible_name} ID you gave does not exist.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        history = await TradeObject.filter(carinstance__id=pk).prefetch_related(
            "trade", "carinstance__player"
        )
        if not history:
            await interaction.followup.send("No history found.", ephemeral=True)
            return
        trades = (
            await Trade.filter(id__in=[x.trade_id for x in history])
            .order_by(sorting.value)
            .prefetch_related("player1", "player2")
        )
        source = TradeViewFormat(trades, f"{settings.collectible_name} {car}", self.bot)
        pages = Pages(source=source, interaction=interaction)
        await pages.start(ephemeral=True)

    @history.command(name="trade")
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def trade_info(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        tradeid: str,
    ):
        """
        Show the contents of a certain trade.

        Parameters
        ----------
        tradeid: str
            The ID of the trade you want to check the history of.
        """
        try:
            pk = int(tradeid, 16)
        except ValueError:
            await interaction.response.send_message(
                "The trade ID you gave is not valid.", ephemeral=True
            )
            return
        trade = await Trade.get(id=pk).prefetch_related("player1", "player2")
        if not trade:
            await interaction.response.send_message(
                "The trade ID you gave does not exist.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title=f"Trade {trade.pk:0X}",
            description=f"Trade ID: {trade.pk:0X}",
            timestamp=trade.date,
        )
        embed.set_footer(text="Trade date: ")
        fill_trade_embed_fields(
            embed,
            self.bot,
            await TradingUser.from_trade_model(trade, trade.player1, self.bot),
            await TradingUser.from_trade_model(trade, trade.player2, self.bot),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @info.command()
    async def guild(
        self,
        interaction: discord.Interaction,
        guild_id: str,
        days: int = 7,
    ):
        """
        Show information about the server provided

        Parameters
        ----------
        guild: discord.Guild | None
            The guild you want to get information about.
        guild_id: str | None
            The ID of the guild you want to get information about.
        days: int
            The amount of days to look back for the amount of cars caught.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = self.bot.get_guild(int(guild_id))

        if not guild:
            try:
                guild = await self.bot.fetch_guild(int(guild_id))  # type: ignore
            except ValueError:
                await interaction.followup.send(
                    "The guild ID you gave is not valid.", ephemeral=True
                )
                return
            except discord.NotFound:
                await interaction.followup.send(
                    "The given guild ID could not be found.", ephemeral=True
                )
                return

        if config := await GuildConfig.get_or_none(guild_id=guild.id):
            spawn_enabled = config.enabled and config.guild_id
        else:
            spawn_enabled = False

        total_server_cars = await CarInstance.filter(
            catch_date__gte=datetime.datetime.now() - datetime.timedelta(days=days),
            server_id=guild.id,
        ).prefetch_related("player")
        if guild.owner_id:
            owner = await self.bot.fetch_user(guild.owner_id)
            embed = discord.Embed(
                title=f"{guild.name} ({guild.id})",
                description=f"Owner: {owner} ({guild.owner_id})",
                color=settings.default_embed_color,
            )
        else:
            embed = discord.Embed(
                title=f"{guild.name} ({guild.id})",
                color=settings.default_embed_color,
            )
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Spawn Enabled", value=spawn_enabled)
        embed.add_field(name="Created at", value=format_dt(guild.created_at, style="R"))
        embed.add_field(
            name=f"{settings.collectible_name.title()}s Caught ({days} days)",
            value=len(total_server_cars),
        )
        embed.add_field(
            name=f"Amount of Users who caught {settings.collectible_name}s ({days} days)",
            value=len(set([x.player.discord_id for x in total_server_cars])),
        )

        if guild icon:
        embed.set_thumbnail(url=guild.icon.url)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @info.command()
    async def user(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        days: int = 7,
    ):
        """
        Show information about the user provided

        Parameters
        ----------
        user: discord.User | None
            The user you want to get information about.
        days: int
            The amount of days to look back for the amount of cars caught.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        player = await Player.get_or_none(discord_id=user.id)
        if not player:
            await interaction.followup.send("The user you gave does not exist.", ephemeral=True)
            return
        total_user_cars = await CarInstance.filter(
            catch_date__gte=datetime.datetime.now() - datetime.timedelta(days=days),
            player=player,
        )
        embed = discord.Embed(
            title=f"{user} ({user.id})",
            description=(
                f"Privacy Policy: {PRIVATE_POLICY_MAP[player.privacy_policy]}\n"
                f"Donation Policy: {DONATION_POLICY_MAP[player.donation_policy]}"
            ),
            color=settings.default_embed_color,
        )
        embed.add_field(name=f"{settings.collectible_name.title()}s Caught ({days} days)", value=len(total_user_cars))
        embed.add_field(
            name=f"{settings.collectible_name.title()}s Caught (Unique - ({days} days))",
            value=len(set(total_user_cars)),
        )
        embed.add_field(
            name=f"Total Servers with {settings.collectible_name}s caught ({days} days))",
            value=len(set([x.server_id for x in total_user_cars])),
        )
        embed.add_field(
            name=f"Total {settings.collectible_name.title()}s Caught",
            value=await CarInstance.filter(player__discord_id=user.id).count(),
        )
        embed.add_field(
            name=f"Total Unique {settings.collectible_name.title()}s Caught",
            value=len(set([x.carfigure for x in total_user_cars])),
        )
        embed.add_field(
            name=f"Total Servers with {settings.collectible_name.title()}s Caught",
            value=len(set([x.server_id for x in total_user_cars])),
        )
        embed.set_thumbnail(url=user.display_avatar)  # type: ignore
        await interaction.followup.send(embed=embed, ephemeral=True)
