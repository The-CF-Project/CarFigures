import argparse
import asyncio
import functools
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path
from signal import SIGTERM
from queue import Queue

import discord
from discord.utils import _ColourFormatter
import yarl
from aerich import Command
from discord.ext.commands import when_mentioned_or
from rich import print
from tortoise import Tortoise

from carfigures import botVersion
from carfigures.core.bot import CarFiguresBot
from carfigures.settings import read_settings, settings

discord.voice_client.VoiceClient.warn_nacl = False  # disable PyNACL warning
log = logging.getLogger("carfigures")

TORTOISE_ORM = {
    "connections": {"default": os.environ.get("CARFIGURESBOT_DB_URL")},
    "apps": {
        "models": {
            "models": ["carfigures.core.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}


class CLIFlags(argparse.Namespace):
    version: bool
    config_file: Path
    reset_settings: bool
    disable_rich: bool
    debug: bool
    dev: bool


def parse_cli_flags(arguments: list[str]) -> CLIFlags:
    parser = argparse.ArgumentParser(
        prog="CarFigures bot", description="Collect and exchange carfigures on Discord"
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Set the path to the configuration file",
        default=Path("./config.toml"),
    )
    parser.add_argument("--disable-rich", action="store_true", help="Disable rich log format")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    parser.add_argument("--dev", action="store_true", help="Enable developer mode")
    args = parser.parse_args(arguments, namespace=CLIFlags())
    return args


def print_welcome():
    print("[green]{0:-^50}[/green]".format(f" {settings.bot_name} "))
    print("[blue]{0:^50}[/blue]".format("Based on The CF Project, Made by Array_YE"))
    print("")
    print(
        " [red]{0:<20}[/red] [yellow]{1:>10}[/yellow]".format(
            "Discord.py version:", discord.__version__
        )
    )
    print(" [red]{0:<20}[/red] [yellow]{1:>10}[/yellow]".format("CF Version:", botVersion))
    print("")


def patch_gateway(proxy_url: str):
    """This monkeypatches discord.py in order to be able to use a custom gateway URL.

    Parameters
    ----------
    proxy_url : str
        The URL of the gateway proxy to use.
    """

    class ProductionHTTPClient(discord.http.HTTPClient):  # type: ignore
        async def get_gateway(self, **_):
            return f"{proxy_url}?encoding=json&v=10"

        async def get_bot_gateway(self, **_):
            try:
                data = await self.request(
                    discord.http.Route("GET", "/gateway/bot")  # type: ignore
                )
            except discord.HTTPException as exc:
                raise discord.GatewayNotFound() from exc
            return data["shards"], f"{proxy_url}?encoding=json&v=10"

    class ProductionDiscordWebSocket(discord.gateway.DiscordWebSocket):  # type: ignore
        def is_ratelimited(self):
            return False

        async def debug_send(self, data, /):
            self._dispatch("socket_raw_send", data)
            await self.socket.send_str(data)

        async def send(self, data, /):
            await self.socket.send_str(data)

    class ProductionReconnectWebSocket(Exception):
        def __init__(self, shard_id: int | None, *, resume: bool = False):
            self.shard_id: int | None = shard_id
            self.resume: bool = False
            self.op: str = "IDENTIFY"

    def is_ws_ratelimited(self):
        return False

    async def before_identify_hook(self, shard_id: int | None, *, initial: bool = False):
        pass

    discord.http.HTTPClient.get_gateway = ProductionHTTPClient.get_gateway  # type: ignore
    discord.http.HTTPClient.get_bot_gateway = ProductionHTTPClient.get_bot_gateway  # type: ignore
    discord.gateway.DiscordWebSocket._keep_alive = None  # type: ignore
    discord.gateway.DiscordWebSocket.is_ratelimited = (  # type: ignore
        ProductionDiscordWebSocket.is_ratelimited
    )
    discord.gateway.DiscordWebSocket.debug_send = (  # type: ignore
        ProductionDiscordWebSocket.debug_send
    )
    discord.gateway.DiscordWebSocket.send = ProductionDiscordWebSocket.send  # type: ignore
    discord.gateway.DiscordWebSocket.DEFAULT_GATEWAY = yarl.URL(proxy_url)  # type: ignore
    discord.gateway.ReconnectWebSocket.__init__ = (  # type: ignore
        ProductionReconnectWebSocket.__init__
    )
    CarFiguresBot.is_ws_ratelimited = is_ws_ratelimited
    CarFiguresBot.before_identify_hook = before_identify_hook


def init_logger(disable_rich: bool = False, debug: bool = False) -> logging.handlers.QueueListener:
    formatter = logging.Formatter(
        "[{asctime}] {levelname} {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )
    rich_formatter = _ColourFormatter()

    # handlers
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    stream_handler.setFormatter(formatter if disable_rich else rich_formatter)

    # file handler
    file_handler = logging.handlers.RotatingFileHandler(
        "carfigures.log", maxBytes=8**7, backupCount=8
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    queue = Queue(-1)
    queue_handler = logging.handlers.QueueHandler(queue)

    root = logging.getLogger()
    root.addHandler(queue_handler)
    root.setLevel(logging.INFO)
    log.setLevel(logging.DEBUG if debug else logging.INFO)

    queue_listener = logging.handlers.QueueListener(queue, stream_handler, file_handler)
    queue_listener.start()

    logging.getLogger("aiohttp").setLevel(logging.WARNING)  # don't log each prometheus call

    return queue_listener


async def shutdown_handler(bot: CarFiguresBot, signal_type: str | None = None):
    if signal_type:
        log.info(f"Received {signal_type}, stopping the bot...")
    else:
        log.info("Shutting down the bot...")
    try:
        await asyncio.wait_for(bot.close(), timeout=10)
    finally:
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in pending]
        try:
            await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=5)
        except asyncio.TimeoutError:
            log.error(
                f"Timed out cancelling tasks. {len([t for t in pending if not t.cancelled])}/"
                f"{len(pending)} tasks are still pending!"
            )
        sys.exit(0 if signal_type else 1)


def global_exception_handler(bot: CarFiguresBot, loop: asyncio.AbstractEventLoop, context: dict):
    """
    Logs unhandled exceptions in other tasks
    """
    exc = context.get("exception")
    # These will get handled later when it *also* kills loop.run_forever
    if exc is not None and isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return
    log.critical(
        "Caught unhandled exception in %s:\n%s",
        context.get("future", "event loop"),
        context["message"],
        exc_info=exc,
    )


def bot_exception_handler(bot: CarFiguresBot, bot_task: asyncio.Future):
    """
    This is set as a done callback for the bot

    Must be used with functools.partial

    If the main bot.run dies for some reason,
    we don't want to swallow the exception and hang.
    """
    try:
        bot_task.result()
    except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
        pass  # Handled by the global_exception_handler, or cancellation
    except Exception as exc:
        log.critical("The main bot task didn't handle an exception and has crashed", exc_info=exc)
        log.warning("Attempting to die as gracefully as possible...")
        asyncio.create_task(shutdown_handler(bot))


class RemoveWSBehindMsg(logging.Filter):
    """Filter used when gateway proxy is set, the "behind" message is meaningless in this case."""

    def __init__(self):
        super().__init__(name="discord.gateway")

    def filter(self, record):
        if record.levelname == "WARNING" and "Can't keep up" in record.msg:
            return False

        return True


async def init_tortoise(db_url: str):
    log.debug(f"Database URL: {db_url}")
    await Tortoise.init(config=TORTOISE_ORM)

    # migrations
    command = Command(TORTOISE_ORM, app="models")
    await command.init()
    migrations = await command.upgrade()
    if migrations:
        log.info(f"Ran {len(migrations)} migrations: {', '.join(migrations)}")


def main():
    bot = None
    server = None
    cli_flags = parse_cli_flags(sys.argv[1:])

    try:
        read_settings(cli_flags.config_file)
    except FileNotFoundError:
        print(
            "[red]The config file [blue]{cli_flags.config_file}[/blue] could not be found.[/red]"
        )
        print("[yellow]Make sure to follow the configuration guide in the wiki.[/yellow]")
        sys.exit(1)

    print_welcome()
    queue_listener: logging.handlers.QueueListener | None = None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        queue_listener = init_logger(cli_flags.disable_rich, cli_flags.debug)

        token = settings.bot_token
        if not token:
            log.error("Token not found!")
            print("[red]You must provide a token inside the config.toml file.[/red]")
            time.sleep(1)
            sys.exit(0)

        db_url = os.environ.get("CARFIGURESBOT_DB_URL", None)
        if not db_url:
            log.error("Database URL not found!")
            print("[red]You must provide a DB URL with the CARFIGURESBOT_DB_URL env var.[/red]")
            time.sleep(1)
            sys.exit(0)

        if settings.gatewayUrl is not None:
            log.info("Using custom gateway URL: %s", settings.gatewayUrl)
            patch_gateway(settings.gatewayUrl)
            logging.getLogger("discord.gateway").addFilter(RemoveWSBehindMsg())

        prefix = settings.prefix

        try:
            loop.run_until_complete(init_tortoise(db_url))
        except Exception:
            log.exception("Failed to connect to database.")
            return  # will exit with code 1
        log.info("Tortoise ORM and database ready.")

        bot = CarFiguresBot(
            command_prefix=when_mentioned_or(prefix),
            dev=cli_flags.dev,  # type: ignore
            shard_count=settings.shardCount,
        )

        exc_handler = functools.partial(global_exception_handler, bot)
        loop.set_exception_handler(exc_handler)
        loop.add_signal_handler(
            SIGTERM, lambda: loop.create_task(shutdown_handler(bot, "SIGTERM"))
        )

        log.info("Initialized bot, connecting to Discord...")
        future = loop.create_task(bot.start(token))
        bot_exc_handler = functools.partial(bot_exception_handler, bot)
        future.add_done_callback(bot_exc_handler)

        loop.run_forever()
    except KeyboardInterrupt:
        if bot is not None:
            loop.run_until_complete(shutdown_handler(bot, "Ctrl+C"))
    except Exception:
        log.critical("Unhandled exception.", exc_info=True)
        if bot is not None:
            loop.run_until_complete(shutdown_handler(bot))
    finally:
        if queue_listener:
            queue_listener.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
        if server is not None:
            loop.run_until_complete(server.stop())
        if Tortoise._inited:
            loop.run_until_complete(Tortoise.close_connections())
        asyncio.set_event_loop(None)
        loop.stop()
        loop.close()
        sys.exit(bot._shutdown if bot else 1)


if __name__ == "__main__":
    main()
