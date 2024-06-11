import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import tomllib

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("carfigures.settings")


@dataclass
class Settings:
    """
    Global bot settings

    Attributes
    ----------
    bot_token: str
        Discord token for the bot to connect
    gateway_url: str | None
        The URL of the Discord gateway that this instance of the bot should connect to and use.
    shard_count: int | None
        The number of shards to use for this bot instance.
        Must be equal to the one set in the gateway proxy if used.
    prefix: str
        Prefix for text commands, mostly unused. Defaults to "b."
    collectible_name: str
        Usually "carfigure", can be replaced when possible
    bot_name: str
        Usually "CarFigures", can be replaced when possible
    players_group_cog_name: str
        Set the name of the base command of the "players" cog, /cars by default
    superuser_group_cog_name: str
        Set the name of the base command of the "admin" cog, /admin by default
    info_description: str
        Used in the /info bot command
    repository_link: str
        Used in the /info bot command
    discord_invite: str
        Used in the /info bot command
    terms_of_service: str
        Used in the /info bot command
    privacy_policy: str
        Used in the /info bot command
    top_gg: str
        Used in the /info bot
    superuser_guild_ids: list[int]
        List of guilds where the /super command must be registered
    root_role_ids: list[int]
        List of roles that have full access to the admin commands
    superuser_role_ids: list[int]
        List of roles that have partial access to the admin commands (only blacklist and guilds)
    """

    bot_token: str = ""
    gateway_url: str | None = None
    shard_count: int | None = None
    prefix: str = ""
    spawnalert: bool = False
    version: str = ""

    collectible_name: str = ""
    bot_name: str = ""
    players_group_cog_name: str = ""
    superuser_group_cog_name: str = ""
    cartype_replacement: str = ""
    country_replacement: str = ""
    horsepower_replacement: str = ""
    weight_replacement: str = ""
    hp_replacement: str = ""
    kg_replacement: str = ""
    default_embed_color: str = ""
    max_favorites: int = 50

    # /info bot
    info_description: str = ""
    repository_link: str = ""
    discord_invite: str = ""
    terms_of_service: str = ""
    privacy_policy: str = ""
    top_gg: str = ""

    # credits
    developers: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)
    testers: list[str] = field(default_factory=list)

    # /sudo
    superuser_guild_ids: list[int] = field(default_factory=list)
    root_role_ids: list[int] = field(default_factory=list)
    superuser_role_ids: list[int] = field(default_factory=list)

    log_channel: int | None = None

    team_owners: bool = False
    co_owners: list[int] = field(default_factory=list)

    # metrics and prometheus
    prometheus_enabled: bool = False
    prometheus_host: str = "0.0.0.0"
    prometheus_port: int = 15260

    # commands
    command_names: dict = field(default_factory=dict)
    command_descs: dict = field(default_factory=dict)


settings = Settings()


def read_settings(path: "Path"):
    with open(path, "rb") as f:
        config = tomllib.load(f)

    settings.bot_token = config["settings"]["bot_token"]
    # settings.gateway_url = config["settings"].get("gateway_url", None)
    # shard_count = config["settings"].get("shard_count")
    # settings.shard_count = int(shard_count) if shard_count else None
    settings.prefix = config["settings"]["text_prefix"]
    settings.spawnalert = config["settings"]["spawnalert"]
    settings.version = config["settings"]["version"]
    settings.default_embed_color = int(config["settings"]["default_embed_color"], 16)

    settings.collectible_name = config["appearance"]["bot"]["collectible_name"]
    settings.bot_name = config["appearance"]["bot"]["bot_name"]
    settings.players_group_cog_name = config["appearance"]["bot"]["players_group_cog_name"]
    settings.superuser_group_cog_name = config["appearance"]["bot"]["superuser_group_cog_name"]

    settings.cartype_replacement = config["appearance"]["interface"]["cartype"]
    settings.country_replacement = config["appearance"]["interface"]["country"]
    settings.horsepower_replacement = config["appearance"]["interface"]["horsepower"]
    settings.weight_replacement = config["appearance"]["interface"]["weight"]
    settings.hp_replacement = config["appearance"]["interface"]["hp"]
    settings.kg_replacement = config["appearance"]["interface"]["kg"]

    #settings.info_description = config["info"]["info_description"]
    settings.repository_link = config["info"]["links"]["repository_link"]
    settings.discord_invite = config["info"]["links"]["discord_invite"]
    settings.terms_of_service = config["info"]["links"]["terms_of_service"]
    settings.privacy_policy = config["info"]["links"]["privacy_policy"]
    settings.top_gg = config["info"]["links"]["top_gg"]

    settings.developers = config["info"]["credits"]["developers"]
    settings.contributors = config["info"]["credits"]["contributors"]
    settings.testers = config["info"]["credits"]["testers"]

    settings.superuser_guild_ids = config["superuser"]["guild_ids"]
    settings.root_role_ids = config["superuser"]["root_role_ids"]
    settings.superuser_role_ids = config["superuser"]["superuser_role_ids"]
    settings.log_channel = config["superuser"]["log_channel"]

    settings.team_owners = config["owners"]["team_members_are_owners"]
    settings.co_owners = config["owners"]["co_owners"]

    settings.prometheus_enabled = config["prometheus"]["enabled"]
    settings.prometheus_host = config["prometheus"]["host"]
    settings.prometheus_port = config["prometheus"]["port"]

    settings.command_names = config["appearance"]["commands"]["names"]
    settings.command_descs = config["appearance"]["commands"]["descs"]

    log.info("Loaded the bot settings")

