from __future__ import annotations

import os
import asyncio
import inspect
import logging
import math
import types
from datetime import datetime
import time
from typing import TYPE_CHECKING, cast

import aiohttp
import discord
import discord.gateway
from cachetools import TTLCache
from discord import app_commands
from discord.app_commands.translator import (
    TranslationContextLocation,
    TranslationContextTypes,
    locale_str,
)
from discord.enums import Locale
from discord.ext import commands
from prometheus_client import Histogram
from rich import box, print
from rich.console import Console
from rich.table import Table

from carfigures.core.commands import Core
from carfigures.core.dev import Dev
from carfigures.core.metrics import PrometheusServer
from carfigures.core import models
from carfigures.settings import settings, appearance, information

if TYPE_CHECKING:
    from discord.ext.commands.bot import PrefixType

log = logging.getLogger("carfigures.core.bot")
http_counter = Histogram("discord_http_requests", "HTTP requests", ["key", "code"])

PACKAGES = [x for x in os.listdir("carfigures/packages") if x != "__pycache__"]


def owner_check(ctx: commands.Context[CarFiguresBot]):
    return ctx.bot.is_owner(ctx.author)


class Translator(app_commands.Translator):
    async def translate(
        self, string: locale_str, locale: Locale, context: TranslationContextTypes
    ) -> str | None:
        if context.location in (
            TranslationContextLocation.choice_name,
            TranslationContextLocation.other,
        ):
            return None
        return (
            string.message.replace("carfigure", appearance.collectible_singular)
            .replace("CarFigures", settings.bot_name)
            .replace("carfigures", appearance.collectible_plural)
        )


# observing the duration and status code of HTTP requests through aiohttp TraceConfig
async def on_request_start(
    session: aiohttp.ClientSession,
    trace_ctx: types.SimpleNamespace,
    params: aiohttp.TraceRequestStartParams,
):
    # register t1 before sending request
    trace_ctx.start = session.loop.time()


async def on_request_end(
    session: aiohttp.ClientSession,
    trace_ctx: types.SimpleNamespace,
    params: aiohttp.TraceRequestEndParams,
):
    time = session.loop.time() - trace_ctx.start

    # to categorize HTTP calls per path, we need to access the corresponding discord.http.Route
    # object, which is not available in the context of an aiohttp TraceConfig, therefore it's
    # obtained by accessing the locals() from the calling function HTTPConfig.request
    # "params.url.path" is not usable as it contains raw IDs and tokens, breaking categories
    frame = inspect.currentframe()
    _locals = frame.f_back.f_back.f_back.f_back.f_back.f_locals  # type: ignore
    if route := _locals.get("route"):
        route_key = route.key
    else:
        # calling function is HTTPConfig.static_login which has no Route object
        route_key = f"{params.response.method} {params.url.path}"

    http_counter.labels(route_key, params.response.status).observe(time)


class CommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction[CarFiguresBot], /) -> bool:
        # checking if the moment we receive this interaction isn't too late already
        # there is a 3 seconds limit for initial response, taking a little margin into account
        # https://discord.com/developers/docs/interactions/receiving-and-responding#responding-to-an-interaction
        delta = datetime.now(tz=interaction.created_at.tzinfo) - interaction.created_at
        if delta.total_seconds() >= 2.8:
            log.warning(
                f"Skipping interaction {interaction.id}, running {delta.total_seconds()}s late."
            )
            return False

        bot = interaction.client
        if not bot.is_ready():
            if interaction.type != discord.InteractionType.autocomplete:
                await interaction.response.send_message(
                    "The bot is currently starting, please wait for a few minutes... "
                    f"({round((len(bot.shards)/bot.shard_count)*100)}%)",
                    ephemeral=True,
                )
            return False  # wait for all shards to be connected
        return await bot.blacklist_check(interaction)


class CarFiguresBot(commands.AutoShardedBot):
    """
    CarFigures Discord bot
    """

    def __init__(self, command_prefix: PrefixType[CarFiguresBot], dev: bool = False, **options):
        # An explanation for the used intents
        # guilds: needed for basically anything, the bot needs to know what guilds it has
        # and accordingly enable automatic spawning in the enabled ones
        # guild_messages: spawning is based on messages sent, content is not necessary
        # emojis_and_stickers: DB holds emoji IDs for the cars which are fetched from 3 servers
        intents = discord.Intents(
            guilds=True,
            guild_messages=True,
            emojis_and_stickers=True,
            message_content=True,
        )

        if settings.prometheusEnabled:
            trace = aiohttp.TraceConfig()
            trace.on_request_start.append(on_request_start)
            trace.on_request_end.append(on_request_end)
            options["http_trace"] = trace

        super().__init__(command_prefix, intents=intents, tree_cls=CommandTree, **options)

        self.dev = dev
        self.prometheus_server: PrometheusServer | None = None

        self.tree.error(self.on_application_command_error)
        self.add_check(owner_check)  # Only owners are able to use text commands

        self._shutdown = 0
        self.blacklisted_users: set[int] = set()
        self.blacklisted_servers: set[int] = set()
        self.locked_cars = TTLCache(maxsize=99999, ttl=60 * 30)
        self.application_emojis: dict[int, discord.Emoji] = {}

        self.owner_ids: set

    async def start_prometheus_server(self):
        self.prometheus_server = PrometheusServer(
            self, settings.prometheusHost, settings.prometheusPort
        )
        await self.prometheus_server.run()

    def assign_ids_to_app_groups(
        self,
        group: app_commands.Group,
        synced_commands: list[app_commands.AppCommandGroup],
    ):
        for synced_command in synced_commands:
            bot_command = group.get_command(synced_command.name)
            if not bot_command:
                continue
            bot_command.extras["mention"] = synced_command.mention
            if isinstance(bot_command, app_commands.Group) and bot_command.commands:
                self.assign_ids_to_app_groups(
                    bot_command,
                    cast(list[app_commands.AppCommandGroup], synced_command.options),
                )

    def assign_ids_to_app_commands(self, synced_commands: list[app_commands.AppCommand]):
        for synced_command in synced_commands:
            bot_command = self.tree.get_command(synced_command.name, type=synced_command.type)
            if not bot_command:
                continue
            bot_command.extras["mention"] = synced_command.mention
            if isinstance(bot_command, app_commands.Group) and bot_command.commands:
                self.assign_ids_to_app_groups(
                    bot_command,
                    cast(list[app_commands.AppCommandGroup], synced_command.options),
                )
    def get_emoji(self, id: int) -> discord.Emoji | None:
        return self.application_emojis.get(id) or super().get_emoji(id)
    
    async def reload_cache(self):
        table = Table(box=box.SIMPLE)
        table.add_column("Model", style="cyan")
        table.add_column("Count", justify="right", style="green")

        self.application_emojis.clear()
        for emoji in await self.fetch_application_emojis():
            self.application_emojis[emoji.id] = emoji

        self.blacklisted_users = set()
        for blacklisted_user in await models.BlacklistedUser.all().only("discord_id"):
            self.blacklisted_users.add(blacklisted_user.discord_id)
        table.add_row("Blacklisted users", str(len(self.blacklisted_users)))

        self.blacklisted_servers = set()
        for blacklisted_server in await models.BlacklistedGuild.all().only("discord_id"):
            self.blacklisted_servers.add(blacklisted_server.discord_id)
        table.add_row("Blacklisted guilds", str(len(self.blacklisted_servers)))

        models.cars.clear()
        for car in await models.Car.all():
            models.cars[car.pk] = car
        table.add_row(appearance.collectible_plural.title(), str(len(models.cars)))

        models.cartypes.clear()
        for cartype in await models.CarType.all():
            models.cartypes[cartype.pk] = cartype
        table.add_row(f"{appearance.album}s", str(len(models.cartypes)))

        models.countries.clear()
        for country in await models.Country.all():
            models.countries[country.pk] = country
        table.add_row(f"{appearance.country}s", str(len(models.countries)))

        models.events.clear()
        for event in await models.Event.all():
            models.events[event.pk] = event
        table.add_row("Events", str(len(models.events)))

        models.exclusives.clear()
        for exclusive in await models.Exclusive.all():
            models.exclusives[exclusive.pk] = exclusive
        table.add_row(f"{appearance.exclusive}s", str(len(models.exclusives)))

        models.fontspacks.clear()
        for fontspack in await models.FontsPack.all():
            models.fontspacks[fontspack.pk] = fontspack
        table.add_row("FontsPacks", str(len(models.fontspacks)))
        log.info("Cache loaded, summary displayed below")
        console = Console()
        console.print(table)

    async def gateway_healthy(self) -> bool:
        """Check whether or not the gateway proxy is ready and healthy."""
        if settings.gatewayUrl is None:
            raise RuntimeError("This is only available on the production bot instance.")

        try:
            base_url = str(discord.gateway.DiscordWebSocket.DEFAULT_GATEWAY).replace(
                "ws://", "http://"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/health", timeout=10) as resp:
                    return resp.status == 200
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            return False

    async def setup_hook(self) -> None:
        await self.tree.set_translator(Translator())
        log.info("Starting up with %s shards...", self.shard_count)
        if settings.gatewayUrl is None:
            return

        while True:
            response = await self.gateway_healthy()
            if response is True:
                log.info("Gateway proxy is ready!")
                break

            log.warning("Gateway proxy is not ready yet, waiting 30 more seconds...")
            await asyncio.sleep(30)

    async def on_ready(self):
        if self.cogs != {}:
            return  # bot is reconnecting, no need to setup again

        assert self.user
        log.info(f"Successfully logged in as {self.user} ({self.user.id})!")

        # set bot owners
        assert self.application
        self.owner_ids.add(self.application.owner.id)
        if settings.roots:
            self.owner_ids.update(settings.roots)
        if len(self.owner_ids) > 1:
            log.info(f"{len(self.owner_ids)} users are set as bot owners.")
        else:
            log.info(
                f"{await self.fetch_user(next(iter(self.owner_ids)))} is the owner of this bot."
            )

        await self.reload_cache()
        if self.blacklisted_users:
            log.info(f"{len(self.blacklisted_users)} blacklisted users.")

        log.info("Loading packages...")
        await self.add_cog(Core(self))
        if self.dev:
            await self.add_cog(Dev())

        loaded_packages = []
        for package in PACKAGES:
            try:
                await self.load_extension("carfigures.packages." + package)
            except Exception:
                log.error(f"Failed to load package {package}", exc_info=True)
            else:
                loaded_packages.append(package)
        if loaded_packages:
            log.info(f"Packages loaded: {', '.join(loaded_packages)}")
        else:
            log.info("No package loaded.")

        synced_commands = await self.tree.sync()
        if synced_commands:
            log.info(f"Synced {len(synced_commands)} commands.")
            try:
                self.assign_ids_to_app_commands(synced_commands)
            except Exception:
                log.error("Failed to assign IDs to app commands", exc_info=True)
        else:
            log.info("No command to sync.")

        if "superuser" in PACKAGES:
            for guild_id in settings.superguilds:
                guild = self.get_guild(guild_id)
                if not guild:
                    continue
                synced_commands = await self.tree.sync(guild=guild)
                log.info(
                    f"Synced {len(synced_commands)} {appearance.sudo} commands for guild {guild.id}."
                )

        if settings.prometheusEnabled:
            try:
                await self.start_prometheus_server()
            except Exception:
                log.exception("Failed to start Prometheus server, stats will be unavailable.")

        print(
            f"\n    [bold][red]{settings.bot_name} bot[/red] [green]"
            "is now operational![/green][/bold]\n"
        )

    async def blacklist_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.blacklisted_users:
            if interaction.type != discord.InteractionType.autocomplete:
                await interaction.response.send_message(
                    "You are blacklisted from the bot."
                    "\nYou can appeal this blacklist in our support server: {}".format(
                        information.server_invite
                    ),
                    ephemeral=True,
                )
            return False
        if interaction.guild_id and interaction.guild_id in self.blacklisted_servers:
            if interaction.type != discord.InteractionType.autocomplete:
                await interaction.response.send_message(
                    "This server is blacklisted from the bot."
                    "\nYou can appeal this blacklist in our support server: {}".format(
                        information.server_invite
                    ),
                    ephemeral=True,
                )
            return False
        return True

    async def on_command_error(
        self, context: commands.Context, exception: commands.errors.CommandError
    ):
        if isinstance(
            exception,
            (commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand),
        ):
            return

        assert context.command
        if isinstance(exception, (commands.ConversionError, commands.UserInputError)):
            # in case we need to know what happened
            log.debug("Silenced command exception", exc_info=exception)
            await context.send_help(context.command)
            return

        if isinstance(exception, commands.MissingRequiredAttachment):
            await context.send("An attachment is missing.")
            return

        if isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, discord.Forbidden):
                await context.send("The bot does not have the permission to do something.")
                # log to know where permissions are lacking
                log.warning(
                    f"Missing permissions for text command {context.command.qualified_name}",
                    exc_info=exception.original,
                )
                return

            log.error(
                f"Error in text command {context.command.qualified_name}",
                exc_info=exception.original,
            )
            await context.send(
                "An error occurred when running the command. Contact support if this persists."
            )
            return

        await context.send(
            "An error occurred when running the command. Contact support if this persists."
        )
        log.error(f"Unknown error in text command {context.command.qualified_name}", exc_info=exception)

    async def on_application_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        async def send(content: str):
            if interaction.response.is_done():
                await interaction.followup.send(content, ephemeral=True)
            else:
                await interaction.response.send_message(content, ephemeral=True)

        if isinstance(error, app_commands.CheckFailure):
            if isinstance(error, app_commands.CommandOnCooldown):
                await send(
                    "This command is on cooldown. Please retry "
                    f"<t:{math.ceil(time.time() + error.retry_after)}:R>."
                )
                return
            await send("You are not allowed to use that command.")
            return

        if isinstance(error, app_commands.TransformerError):
            await send("One of the arguments provided cannot be parsed.")
            log.debug("Failed running converter.", exc_info=error)
            return

        if isinstance(error, app_commands.CommandInvokeError):
            assert interaction.command

            if isinstance(error.original, discord.Forbidden):
                await send("The bot does not have the permission to do something.")
                # log to know where permissions are lacking
                log.warning(
                    f"Missing permissions for app command {interaction.command.qualified_name}",
                    exc_info=error.original,
                )
                return

            if isinstance(error.original, discord.InteractionResponded):
                # most likely an interaction received twice (happens sometimes),
                # or two instances are running on the same token.
                log.warning(
                    f"Tried invoking command {interaction.command.qualified_name}, but the "
                    "interaction was already responded to.",
                    exc_info=error.original,
                )
                # still including traceback because it may be a programming error

            log.error(
                f"Error in slash command {interaction.command.qualified_name}",
                exc_info=error.original,
            )
            await send(
                "An error occurred when running the command. Contact support if this persists."
            )
            return

        await send("An error occurred when running the command. Contact support if this persists.")
        log.error("Unknown error in interaction", exc_info=error)

    async def on_error(self, event_method: str, /, *args, **kwargs):
        formatted_args = ", ".join(args)
        formatted_kwargs = " ".join(f"{x}={y}" for x, y in kwargs.items())
        log.error(
            f"Error in event {event_method}. Args: {formatted_args}. Kwargs: {formatted_kwargs}",
            exc_info=True,
        )
        self.tree.interaction_check
