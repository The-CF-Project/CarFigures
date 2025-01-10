import datetime
import logging
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from tortoise.exceptions import BaseORMException, DoesNotExist
from tortoise.expressions import Q

from carfigures.core import models
from carfigures.core.utils import buttons, paginators, transformers
from carfigures.core.bot import CarFiguresBot
from carfigures.packages.trade.display import TradeViewFormat, fill_trade_embed_fields
from carfigures.packages.trade.trade_user import TradingUser
from carfigures.settings import settings, appearance

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot
    from carfigures.packages.carfigures.cog import CarFiguresSpawner

log = logging.getLogger("carfigures.packages.superuser.cog")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")


async def log_action(message: str, bot: CarFiguresBot):
    if settings.logChannel:
        channel = bot.get_channel(settings.logChannel)
        if not channel:
            log.warning(f"Channel {settings.logChannel} not found")
            return
        if not isinstance(channel, discord.TextChannel):
            log.warning(f"Channel {channel.name} is not a text channel")  # type: ignore
            return
        await channel.send(message)


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


@app_commands.guilds(*settings.superGuilds)
@app_commands.checks.has_any_role(*settings.superUsers)
@app_commands.default_permissions(administrator=True)
class SuperUser(commands.GroupCog, group_name=appearance.sudo):
    """
    Bot admin commands.
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot
        self.cars.parent = self.__cog_app_commands_group__

    cars = app_commands.Group(name=appearance.cars, description="s management")
    player = app_commands.Group(name="player", description="Player commands")

    @app_commands.command()
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
                "You must provide `state` for custom activities. `name` is unused.",
                ephemeral=True,
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
        cars_queryset = models.Car.all().order_by("rarity")
        if not include_disabled:
            cars_queryset = cars_queryset.filter(rarity__gt=0, enabled=True)
        sorted_cars = await cars_queryset

        if chunked:
            indexes: dict[float, list[models.Car]] = defaultdict(list)
            for car in sorted_cars:
                indexes[car.rarity].append(car)
            i = 1
            for chunk in indexes.values():
                for car in chunk:
                    text += f"{i}. {car.fullName}\n"
                i += len(chunk)
        else:
            for i, car in enumerate(sorted_cars, start=1):
                text += f"{i}. {car.fullName}\n"

        source = paginators.TextPageSource(text, prefix="```md\n", suffix="```")
        pages = paginators.Pages(source=source, interaction=interaction, compact=True)
        pages.remove_item(pages.stop_pages)
        await pages.start(ephemeral=True)

    @app_commands.command()
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
            ID of the server you want to inspect, if not given inspect the current server.
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

        spawnManager = cast(
            "CarFiguresSpawner", self.bot.get_cog("CarFiguresSpawner")
        ).spawnManager
        cooldown = spawnManager.cooldowns.get(guild.id)
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
        # change how the threshold varies according to the member count
        # while nuking farm servers
        if guild.member_count < 100:
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
        if any(len(x.content) < 5 for x in cooldown.messageCache):
            penalties.append("Some cached messages are less than 5 characters long")

        authors_set = set(x.author_id for x in cooldown.messageCache)
        low_chatters = len(authors_set) < 4
        # check if one author has more than 40% of messages in cache
        major_chatter = any(
            (
                len(list(filter(lambda x: x.author_id == author, cooldown.messageCache)))
                / cooldown.messageCache.maxlen  # type: ignore
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
            f"Message cache length: **{len(cooldown.messageCache)}**\n\n"
            f"Time-based multiplier: **x{multiplier}** *({range} members)*\n"
            "*This affects how much the number of points to reach reduces over time*\n"
            f"Penalty multiplier: **x{penality_multiplier}**\n"
            "*This affects how much a message sent increases the number of points*\n\n"
            f"__Current count: **{cooldown.scaledMessageCount}/{chance}**__\n\n"
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
                    f"The user does not own any server with {settings.botName}.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"The user does not own any server with {settings.botName}.\n"
                    ":warning: *The bot cannot be aware of the member's presence in servers, "
                    "it is only aware of server ownerships.*",
                    ephemeral=True,
                )
            return

        entries: list[tuple[str, str]] = []
        for guild in guilds:
            if config := await models.GuildConfig.get_or_none(guild_id=guild.id):
                spawn_enabled = config.enabled and config.guild_id
            else:
                spawn_enabled = False

            field_name = f"`{guild.id}`"
            field_value = ""

            # highlight suspicious server names
            if any(x in guild.name.lower() for x in ("farm", "grind", "spam")):
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

        source = paginators.FieldPageSource(entries, per_page=25, inline=True)
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

        pages = paginators.Pages(source=source, interaction=interaction, compact=True)
        pages.add_item(
            buttons.Button(
                style=discord.ButtonStyle.link,
                label="View profile",
                url=f"discord://-/users/{user.id}",
                emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
            )
        )
        await pages.start(ephemeral=True)

    @app_commands.command()
    @app_commands.choices(
        entity=[
            app_commands.Choice(name="User", value="user"),
            app_commands.Choice(name="Server", value="server"),
        ],
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(name="Info", value="info"),
        ],
    )
    async def blacklist(
        self,
        interaction: discord.Interaction,
        entity: app_commands.Choice[str],
        action: app_commands.Choice[str],
        id: app_commands.Range[str, 17, 21],
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

        final_reason = f"{reason}\nBy: {interaction.user} ({interaction.user.id})"
        match entity.value:
            case "user":
                try:
                    user = await self.bot.fetch_user(int(id))  # type: ignore
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
                match action.value:
                    case "add":
                        if await models.BlacklistedUser.filter(discord_id=user.id).exists():
                            await interaction.response.send_message(
                                f"{user.display_name} was already blacklisted.", ephemeral=True
                            )
                            return
                        else:
                            await models.BlacklistedUser.create(
                                discord_id=user.id, reason=final_reason
                            )
                            self.bot.blacklistedUsers.add(user.id)
                        await interaction.response.send_message(
                            f"{user.display_name} is now blacklisted.", ephemeral=True
                        )

                        await log_action(
                            f"{interaction.user} blacklisted {user} ({user.id})"
                            f" for the following reason: {reason}",
                            self.bot,
                        )
                    case "remove":
                        if not await models.BlacklistedUser.get_or_none(discord_id=user.id):
                            await interaction.response.send_message(
                                f"{user.display_name} isn't blacklisted.", ephemeral=True
                            )
                            return
                        else:
                            await models.BlacklistedUser.filter(discord_id=user.id).delete()
                            self.bot.blacklistedUsers.remove(user.id)
                            await interaction.response.send_message(
                                f"{user.display_name} is now removed from blacklist.",
                                ephemeral=True,
                            )
                            await log_action(
                                f"{interaction.user} removed blacklist from {user.display_name} ({user.id})"
                                f" for the following reason: {reason}",
                                self.bot,
                            )
                    case "info":
                        if not await models.BlacklistedUser.get_or_none(discord_id=user.id):
                            await interaction.response.send_message(
                                f"{user.display_name} isn't blacklisted.", ephemeral=True
                            )
                            return

                        blacklisted = await models.BlacklistedUser.get(discord_id=user.id)
                        if blacklisted.date:
                            await interaction.response.send_message(
                                f"`{user.display_name}` (`{user.id}`) was blacklisted on {format_dt(blacklisted.date)}"
                                f"({format_dt(blacklisted.date, style='R')}) for the following reason:\n"
                                f"{blacklisted.reason}",
                                ephemeral=True,
                            )
                            return
                        else:
                            await interaction.response.send_message(
                                f"`{user.display_name}` (`{user.id}`) is currently blacklisted (date unknown)"
                                " for the following reason:\n"
                                f"{blacklisted.reason}",
                                ephemeral=True,
                            )
                            return

            case "server":
                try:
                    server = await self.bot.fetch_guild(int(id))
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
                match action.value:
                    case "add":
                        if await models.BlacklistedGuild.filter(discord_id=server.id).exists():
                            await interaction.response.send_message(
                                f"{server.name} was already blacklisted.", ephemeral=True
                            )
                        else:
                            self.bot.blacklistedServers.add(server.id)
                            await models.BlacklistedGuild.create(guild_id=server.id)
                            await interaction.response.send_message(
                                f"{server.name} is now blacklisted.", ephemeral=True
                            )
                            await log_action(
                                f"{interaction.user} blacklisted the guild {server.name}({server.id}) "
                                f"for the following reason: {reason}",
                                self.bot,
                            )
                    case "remove":
                        if not await models.BlacklistedGuild.get_or_none(discord_id=server.id):
                            await interaction.response.send_message(
                                f"{server.name} isn't blacklisted.", ephemeral=True
                            )
                        else:
                            await models.BlacklistedGuild.filter(guild_id=server.id).delete()
                            self.bot.blacklistedServers.remove(server.id)
                            await interaction.response.send_message(
                                f"{server.name} is now removed from blacklist.", ephemeral=True
                            )
                            await log_action(
                                f"{interaction.user} removed blacklist for guild {server.name} ({server.id})",
                                self.bot,
                            )
                    case "info":
                        if not await models.BlacklistedGuild.get_or_none(discord_id=server.id):
                            await interaction.response.send_message(
                                "That guild isn't blacklisted.", ephemeral=True
                            )
                            return

                        blacklisted = await models.BlacklistedGuild.get(discord_id=server.id)
                        if blacklisted.date:
                            await interaction.response.send_message(
                                f"`{server.name}` (`{server.id}`) was blacklisted on {format_dt(blacklisted.date)}"
                                f"({format_dt(blacklisted.date, style='R')}) for the following reason:\n"
                                f"{blacklisted.reason}",
                                ephemeral=True,
                            )

                        else:
                            await interaction.response.send_message(
                                f"`{server.name}` (`{server.id}`) is currently blacklisted (date unknown)"
                                " for the following reason:\n"
                                f"{blacklisted.reason}",
                                ephemeral=True,
                            )

    @app_commands.command()
    @app_commands.choices(
        entity=[
            app_commands.Choice(name="User", value="user"),
            app_commands.Choice(name="Trade", value="trade"),
            app_commands.Choice(name=appearance.collectibleSingular.title(), value="car"),
        ],
        sorting=[
            app_commands.Choice(name="Most Recent", value="-date"),
            app_commands.Choice(name="Oldest", value="date"),
        ],
    )
    async def history(
        self,
        interaction: discord.Interaction["CarFiguresBot"],
        entity: app_commands.Choice[str],
        sorting: app_commands.Choice[str],
        id: str,
    ):
        """
        Show the history of a user.

        Parameters
        ----------
        user: discord.User
            The user you want to check the history of.
        sorting: str
            The sorting method you want to use.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        match entity.value:
            case "user":
                try:
                    user = await self.bot.fetch_user(int(id))  # type: ignore
                except ValueError:
                    await interaction.followup.send(
                        "The user ID you gave is not valid.", ephemeral=True
                    )
                    return
                except discord.NotFound:
                    await interaction.followup.send(
                        "The given user ID could not be found.", ephemeral=True
                    )
                    return

                history = (
                    await models.Trade.filter(
                        Q(player1__discord_id=user.id) | Q(player2__discord_id=user.id)
                    )
                    .order_by(sorting.value)
                    .prefetch_related("player1", "player2")
                )

                if not history:
                    await interaction.followup.send("No history found.", ephemeral=True)
                    return

                pages = paginators.Pages(
                    source=TradeViewFormat(history, user.display_name, self.bot),
                    interaction=interaction,
                )
                await pages.start(ephemeral=True)
            case "car":
                try:
                    pk = int(id, 16)
                except ValueError:
                    await interaction.followup.send(
                        f"The {appearance.collectibleSingular} ID you gave is not valid.",
                        ephemeral=True,
                    )
                    return

                car = await models.CarInstance.get_or_none(id=pk)
                if not car:
                    await interaction.followup.send(
                        f"The {appearance.collectibleSingular} ID you gave does not exist.",
                        ephemeral=True,
                    )
                    return
                history = await models.TradeObject.filter(carinstance__id=pk).prefetch_related(
                    "trade", "carinstance__player"
                )
                if not history:
                    await interaction.followup.send("No history found.", ephemeral=True)
                    return
                trades = (
                    await models.Trade.filter(id__in=[x.trade_id for x in history])
                    .order_by(sorting.value)
                    .prefetch_related("player1", "player2")
                )
                pages = paginators.Pages(
                    source=TradeViewFormat(
                        trades, f"{appearance.collectibleSingular} {car}", self.bot
                    ),
                    interaction=interaction,
                )
                await pages.start(ephemeral=True)
            case "trade":
                try:
                    pk = int(id, 16)
                except ValueError:
                    await interaction.followup.send(
                        "The trade ID you gave is not valid.", ephemeral=True
                    )
                    return
                trade = await models.Trade.get_or_none(id=pk).prefetch_related(
                    "player1", "player2"
                )
                if not trade:
                    await interaction.followup.send(
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
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.choices(
        entity=[
            app_commands.Choice(name="User", value="user"),
            app_commands.Choice(name="Server", value="server"),
            app_commands.Choice(name="Instance", value="instance"),
        ]
    )
    async def info(
        self,
        interaction: discord.Interaction,
        entity: app_commands.Choice[str],
        id: str,
        days: int = 7,
    ):
        """
        Show information about the server provided

        Parameters
        ----------
        entity: str
            The type of entity you want to get information about.
        id: str
            The ID of the entity you want to get information about.
        days: int
            The amount of days to look back for the amount of cars caught. (not used when not selecting user/server as entity)
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        match entity.value:
            case "user":
                try:
                    user = await self.bot.fetch_user(int(id))  # type: ignore
                except ValueError:
                    await interaction.followup.send(
                        "The user ID you gave is not valid.", ephemeral=True
                    )
                    return
                except discord.NotFound:
                    await interaction.followup.send(
                        "The given user ID could not be found.", ephemeral=True
                    )
                    return

                player = await models.Player.get_or_none(discord_id=user.id)
                if not player:
                    await interaction.followup.send(
                        "The user you gave does not exist.", ephemeral=True
                    )
                    return
                total_user_cars = await models.CarInstance.filter(
                    catchDate__gte=datetime.datetime.now() - datetime.timedelta(days=days),
                    player=player,
                )
                embed = discord.Embed(
                    title=f"Information on {user} | {user.id}",
                    description=(
                        f"**Ⅲ Player Settings**\n"
                        f"\u200b **⋄ Privacy Policy:** {player.privacyPolicy.name}\n"
                        f"\u200b **⋄ Donation Policy:** {player.donationPolicy.name}\n\n"
                        f"**Ⅲ Player Info\n**"
                        f"\u200b **⋄ {appearance.collectiblePlural.title()} Collected in {days} days/in Total:** "
                        f"{len(total_user_cars)} | {await player.cars.all().count()}\n"
                        f"\u200b **⋄ Servers with {appearance.collectiblePlural.title()} caught in {days} days/in Total:**"
                        f"{set([x.server for x in total_user_cars])}/{len(set([x.server for x in total_user_cars]))}\n"
                        # f"\u200b **⋄ "
                        f"\u200b **⋄ Rebirths Done:** {player.rebirths}\n"
                    ),
                    color=settings.defaultEmbedColor,
                )
                embed.set_thumbnail(url=user.display_avatar.url)  # type: ignore
                await interaction.followup.send(embed=embed, ephemeral=True)

            case "server":
                try:
                    guild = await self.bot.fetch_guild(int(id))  # type: ignore
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

                if config := await models.GuildConfig.get_or_none(guild_id=guild.id):
                    spawn_enabled = config.enabled and config.guild_id
                else:
                    spawn_enabled = False

                total_server_cars = await models.CarInstance.filter(
                    catchDate__gte=datetime.datetime.now() - datetime.timedelta(days=days),
                    server=guild.id,
                ).prefetch_related("player")
                if guild.owner_id:
                    owner = await self.bot.fetch_user(guild.owner_id)
                    embed = discord.Embed(
                        title=f"{guild.name} ({guild.id})",
                        description=f"Owner: {owner} ({guild.owner_id})",
                        color=settings.defaultEmbedColor,
                    )
                else:
                    embed = discord.Embed(
                        title=f"{guild.name} ({guild.id})",
                        color=settings.defaultEmbedColor,
                    )
                embed.add_field(name="Members", value=guild.member_count)
                embed.add_field(name="Spawn Enabled", value=spawn_enabled)
                embed.add_field(name="Created at", value=format_dt(guild.created_at, style="R"))
                embed.add_field(
                    name=f"{appearance.collectiblePlural.title()} Caught ({days} days)",
                    value=len(total_server_cars),
                )
                embed.add_field(
                    name=f"Amount of Users who caught {appearance.collectiblePlural} ({days} days)",
                    value=len(set([x.player.discord_id for x in total_server_cars])),
                )

                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)

                await interaction.followup.send(embed=embed, ephemeral=True)
            case "instance":
                assert self.bot.user
                try:
                    pk = int(id, 16)
                except ValueError:
                    await interaction.followup.send(
                        f"The {appearance.collectibleSingular} ID you gave is not valid.",
                        ephemeral=True,
                    )
                    return
                car = await models.CarInstance.get_or_none(id=pk).prefetch_related(
                    "player", "trade_player", "event"
                )
                if not car:
                    await interaction.followup.send(
                        f"The {appearance.collectibleSingular} ID you gave does not exist.",
                        ephemeral=True,
                    )
                    return
                spawned_time = format_dt(car.spawnedTime, style="R") if car.spawnedTime else "N/A"
                catch_time = (
                    (car.catchDate - car.spawnedTime).total_seconds()
                    if car.catchDate and car.spawnedTime
                    else "N/A"
                )
                embed = discord.Embed(
                    title="{}",
                    description=f"**{appearance.collectibleSingular.title()} ID:** {car.pk}\n"
                    f"**Player:** {car.player}\n"
                    f"**Name:** {car.carfigure}\n"
                    f"**{appearance.horsepower} bonus:** {car.horsepowerBonus}\n"
                    f"**{appearance.weight} bonus:** {car.weightBonus}\n"
                    f"**{appearance.exclusive}:** {car.exclusive.name if car.exclusive else None}\n"
                    f"**Event:** {car.event.name if car.event else None}\n"
                    f"**Caught at:** {format_dt(car.catchDate, style='R')}\n"
                    f"**Spawned at:** {spawned_time}\n"
                    f"**Catch time:** {catch_time} seconds\n"
                    f"**Caught in:** {car.server if car.server else 'N/A'}\n"
                    f"**Traded:** {car.trade_player}\n",
                    color=settings.defaultEmbedColor,
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                await interaction.followup.send(embed=embed, ephemeral=True)
                await log_action(f"{interaction.user} got info for {car} ({car.pk})", self.bot)

    @cars.command()
    async def give(
        self,
        interaction: discord.Interaction,
        car: transformers.CarTransform,
        user: discord.User,
        amount: app_commands.Range[int, 1, 100],
        event: transformers.EventTransform | None = None,
        exclusive: transformers.ExclusiveTransform | None = None,
        weightbonus: int | None = None,
        horsepowerbonus: int | None = None,
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
            Omit this to make it random.
        horsepower_bonus: int | None
            Omit this to make it random.
        """
        # the transformers triggered a response, meaning user tried an incorrect input
        if interaction.response.is_done():
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        player, _ = await models.Player.get_or_create(discord_id=user.id)
        hpBonus = horsepowerbonus or random.randint(*settings.catchBonusRate)
        kgBonus = weightbonus or random.randint(*settings.catchBonusRate)
        for _ in range(amount):
            await models.CarInstance.create(
                car=car,
                player=player,
                horsepowerBonus=hpBonus,
                weightBonus=kgBonus,
                event=event,
                exclusive=exclusive,
            )
        await interaction.followup.send(
            f"`{amount}` `{car.fullName + 's' if amount > 1 else car.fullName}` was successfully given to `{user}`.\n"
            f"Event: `{event.name if event else None}` "
            f"• {appearance.exclusive}: `{exclusive.name if exclusive else None}` "
            f"• `{appearance.hp}`:`{hpBonus:+d}` • "
            f"{appearance.kg}:`{kgBonus:+d}`"
        )
        await log_action(
            f"{interaction.user} gave {amount} "
            f"{car.fullName + 's' if amount > 1 else car.fullName} to {user}. "
            f"Event={event.name if event else None} "
            f"• {appearance.exclusive}: `{exclusive.name if exclusive else None}` "
            f"{appearance.hp}={hpBonus:+d} "
            f"{appearance.kg}={kgBonus:+d}",
            self.bot,
        )

    @cars.command()
    async def delete(self, interaction: discord.Interaction, car_id: str):
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
                f"The {appearance.collectibleSingular} ID you gave is not valid.",
                ephemeral=True,
            )
            return
        try:
            car = await models.CarInstance.get(id=carIdConverted)
        except DoesNotExist:
            await interaction.response.send_message(
                f"The {appearance.collectibleSingular} ID you gave does not exist.",
                ephemeral=True,
            )
            return
        await car.delete()
        await interaction.response.send_message(
            f"{appearance.collectibleSingular.title()} {car_id} deleted.", ephemeral=True
        )
        await log_action(f"{interaction.user} deleted {car} ({car.pk})", self.bot)

    @cars.command()
    async def transfer(self, interaction: discord.Interaction, car_id: str, user: discord.User):
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
                f"The {appearance.collectibleSingular} ID you gave is not valid.",
                ephemeral=True,
            )
            return
        try:
            car = await models.CarInstance.get(id=carIdConverted).prefetch_related("player")
            original_player = car.player
        except DoesNotExist:
            await interaction.response.send_message(
                f"The {appearance.collectibleSingular} ID you gave does not exist.",
                ephemeral=True,
            )
            return
        player, _ = await models.Player.get_or_create(discord_id=user.id)
        car.player = player
        await car.save()

        await interaction.response.send_message(
            f"Transfered {car} ({car.pk}) from {original_player} to {user}.",
            ephemeral=True,
        )
        await log_action(
            f"{interaction.user} transferred {car} ({car.pk}) from {original_player} to {user}",
            self.bot,
        )

    @cars.command()
    async def reset(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        percentage: int | None = None,
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
        player = await models.Player.get(discord_id=user.id)
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
            text = f"Are you sure you want to delete {user}'s {appearance.collectiblePlural}?"
        else:
            text = (
                f"Are you sure you want to delete {percentage}% of "
                f"{user}'s {appearance.collectiblePlural}?"
            )
        view = buttons.ConfirmChoiceView(interaction)
        await interaction.followup.send(
            text,
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.value:
            return
        if percentage:
            cars = await models.CarInstance.filter(player=player)
            to_delete = random.sample(cars, int(len(cars) * (percentage / 100)))
            for car in to_delete:
                await car.delete()
            count = len(to_delete)
        else:
            count = await models.CarInstance.filter(player=player).delete()
        await interaction.followup.send(
            f"{count} {appearance.collectiblePlural} from {user} have been reset.",
            ephemeral=True,
        )
        await log_action(
            f"{interaction.user} deleted {percentage or 100}% of {player}'s cars",
            self.bot,
        )

    @cars.command()
    async def count(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        car: transformers.CarTransform | None = None,
        exclusive: transformers.ExclusiveTransform | None = None,
        event: transformers.EventTransform | None = None,
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
        if exclusive is not None:
            filters["exclusive"] = exclusive
        if event:
            filters["event"] = event
        if user:
            filters["player__discord_id"] = user.id
        await interaction.response.defer(ephemeral=True, thinking=True)
        cars = await models.CarInstance.filter(**filters).count()
        full_name = f"{car.fullName} " if car else f"{appearance.collectiblePlural}"
        event_str = f"{event.name} " if event else ""
        exclusive_str = f"{exclusive.name} " if exclusive else ""
        if user:
            await interaction.followup.send(
                f"{user} has {cars} {event_str}{exclusive_str} {full_name}."
            )
        else:
            await interaction.followup.send(
                f"There are {cars} {event_str}{exclusive_str} {full_name}."
            )

    @cars.command()
    async def create(
        self,
        interaction: discord.Interaction,
        *,
        fullname: app_commands.Range[str, None, 48],
        cartype: transformers.CarTypeTransform,
        weight: int,
        horsepower: int,
        emoji_id: app_commands.Range[str, 17, 21],
        capacityname: app_commands.Range[str, None, 64],
        capacitydescription: app_commands.Range[str, None, 256],
        collectionpicture: discord.Attachment,
        carcredits: str,
        rarity: float = 0.0,
        enabled: bool = False,
        tradeable: bool = False,
        spawnpicture: discord.Attachment | None = None,
        country: transformers.CountryTransform | None = None,
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
        emojiId: str
            An emoji ID, the bot will check if it can access the custom emote
        capacityName: str
            The name of the carfigure's capacity
        capacitydescription: str
            The description of the carfigure's capacity
        collectionpicture: discord.Attachment
            Artwork used to show the carfigure in the collection
        carcredits: str
            The name of the person who created the artwork
        rarity: float
            Value defining the rarity of this carfigure, if enabled
        enabled: bool
            If true, the carfigure can spawn and will show up in global completion
        tradeable: bool
            If false, all instances are untradeable
        spawnpicture: discord.Attachment
            Artwork used to spawn the carfigure, with a default
        """
        if cartype is None or interaction.response.is_done():  # country autocomplete failed
            return

        if not emoji_id.isnumeric():
            await interaction.response.send_message(
                "`emojiId` is not a valid number.", ephemeral=True
            )
            return
        emoji = self.bot.get_emoji(int(emoji_id))
        if not emoji:
            await interaction.response.send_message(
                "The bot does not have access to the given emoji.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        default_path = Path("./static/uploads/default.png")

        try:
            collection_image_path = await save_file(collectionpicture)
        except Exception as e:
            log.exception("Failed saving file when creating carfigure", exc_info=True)
            await interaction.followup.send(
                f"Failed saving the attached file: {collectionpicture.url}.\n"
                f"Partial error: {', '.join(str(x) for x in e.args)}\n"
                "The full error is in the bot logs."
            )
            return
        try:
            spawn_image_path = await save_file(spawnpicture) if spawnpicture else default_path
        except Exception as e:
            log.exception("Failed saving file when creating carfigure", exc_info=True)
            await interaction.followup.send(
                f"Failed saving the attached file: {collectionpicture.url}.\n"
                f"Partial error: {', '.join(str(x) for x in e.args)}\n"
                "The full error is in the bot logs."
            )
            return

        try:
            car = await models.Car.create(
                fullName=fullname,
                cartype=cartype,
                country=country,
                weight=weight,
                horsepower=horsepower,
                rarity=rarity,
                enabled=enabled,
                tradeable=tradeable,
                emoji=emoji_id,
                spawnPicture="/" + str(spawn_image_path),
                collectionPicture="/" + str(collection_image_path),
                carCredits=carcredits,
                capacityName=capacityname,
                capacityDescription=capacitydescription,
            )
        except BaseORMException as e:
            log.exception("Failed creating carfigure with admin command", exc_info=True)
            await interaction.followup.send(
                f"Failed creating the {appearance.collectibleSingular}.\n"
                f"Partial error: {', '.join(str(x) for x in e.args)}\n"
                "The full error is in the bot logs."
            )
        else:
            message = (
                f"Successfully created a {appearance.collectibleSingular} with ID {car.pk}! "
                "The internal cache was reloaded.\n"
                f"{fullname=} {appearance.cartype}={cartype.name} "
                f"{appearance.country}={country.name if country else None} "
                f"{weight=} {horsepower=} {rarity=} {enabled=} {tradeable=} emoji={emoji}"
            )
            if not spawnpicture and not default_path.exists():
                message += (
                    "**Warning:** The default spawn image is not set. This will result in errors when "
                    f"attempting to spawn this {appearance.collectibleSingular}. You can edit this on the "
                    "web panel or add an image at static/uploads called default.png.\n"
                )
            files = [await collectionpicture.to_file()]
            if spawnpicture:
                files.append(await spawnpicture.to_file())
            await self.bot.reloadCache()
            await interaction.followup.send(
                message,
                files=files,
            )

    @player.command()
    @app_commands.choices(
        action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="remove", value="remove"),
        ]
    )
    async def rebirth(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        action: app_commands.Choice[str],
        amount: app_commands.Range[int, 1, 100],
    ):
        """
        Add an amount of rebirths to a user.

        Parameters
        ----------
        user: discord.User
            The user you want to add the rebirths to.
        amount: int
            The amount of rebirths you want to add to the user.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        player, _ = await models.Player.get_or_create(discord_id=user.id)
        if amount > player.rebirths and action.value == "remove":
            await interaction.followup.send(
                "You cannot remove more rebirths than the amount of "
                "rebirths the user currently has."
            )
            return

        if action.value == "add":
            player.rebirths += amount
        else:
            player.rebirths -= amount

        await player.save()
        plural = "s" if amount > 1 else ""
        word = "added" if action.value == "add" else "removed"

        await interaction.followup.send(
            f"Successfully {word} {amount} rebirth{plural} to {user.name}."
        )
        await log_action(
            f"{interaction.user} {word} {amount} rebirth{plural} to {user.name}.",
            self.bot,
        )
