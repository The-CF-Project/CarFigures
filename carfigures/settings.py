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
    bot_name: str = ""
    gateway_url: str | None = None
    shard_count: int | None = None
    prefix: str = ""
    spawnalert: bool = False
    minimal_profile: bool = False
    max_favorites: int = 50
    default_embed_color: int = 0

    collectible_singular: str = ""
    collectible_plural: str = ""
    cartype_replacement: str = ""
    country_replacement: str = ""
    horsepower_replacement: str = ""
    weight_replacement: str = ""
    hp_replacement: str = ""
    kg_replacement: str = ""

    cars_group: str = ""
    sudo_group: str = ""
    info_group: str = ""
    my_group: str = ""
    trade_group: str = ""

    garage_name: str = ""
    exhibit_name: str = ""
    show_name: str = ""
    info_name: str = ""
    last_name: str = ""
    favorite_name: str = ""
    give_name: str = ""
    count_name: str = ""
    rarity_name: str = ""
    compare_name: str = ""

    garage_desc: str = ""
    exhibit_desc: str = ""
    show_desc: str = ""
    info_desc: str = ""
    last_desc: str = ""
    favorite_desc: str = ""
    give_desc: str = ""
    count_desc: str = ""
    rarity_desc: str = ""
    compare_desc: str = ""

    # /info status
    repository_link: str = ""
    discord_invite: str = ""
    terms_of_service: str = ""
    privacy_policy: str = ""
    top_gg: str = ""

    # /info about
    info_description: str = ""
    info_history: str = ""
    developers: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)

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


settings = Settings()


def read_settings(path: "Path"):
    with open(path, "rb") as f:
        config = tomllib.load(f)

    settings.bot_token = config["settings"]["bot_token"]
    settings.bot_name = config["settings"]["bot_name"]
    settings.prefix = config["settings"]["text_prefix"]
    settings.minimal_profile = config["settings"]["minimal_profile"]
    settings.spawnalert = config["settings"]["spawnalert"]
    settings.default_embed_color = int(config["settings"]["default_embed_color"], 16)

    settings.collectible_singular = config["appearance"]["collectible_singular"]
    settings.collectible_plural = config["appearance"]["collectible_plural"]
    settings.cartype_replacement = config["appearance"]["cartype"]
    settings.country_replacement = config["appearance"]["country"]
    settings.horsepower_replacement = config["appearance"]["horsepower"]
    settings.weight_replacement = config["appearance"]["weight"]
    settings.hp_replacement = config["appearance"]["hp"]
    settings.kg_replacement = config["appearance"]["kg"]

    settings.cars_group = config["commands"]["groups"]["cars"]
    settings.sudo_group = config["commands"]["groups"]["sudo"]
    settings.info_group = config["commands"]["groups"]["info"]
    settings.my_group = config["commands"]["groups"]["my"]
    settings.trade_group = config["commands"]["groups"]["trade"]

    settings.garage_name = config["commands"]["names"]["garage"]
    settings.exhibit_name = config["commands"]["names"]["exhibit"]
    settings.show_name = config["commands"]["names"]["show"]
    settings.info_name = config["commands"]["names"]["info"]
    settings.last_name = config["commands"]["names"]["last"]
    settings.favorite_name = config["commands"]["names"]["favorite"]
    settings.give_name = config["commands"]["names"]["give"]
    settings.count_name = config["commands"]["names"]["count"]
    settings.rarity_name = config["commands"]["names"]["rarity"]
    settings.compare_name = config["commands"]["names"]["compare"]

    settings.garage_desc = config["commands"]["descs"]["garage"]
    settings.exhibit_desc = config["commands"]["descs"]["exhibit"]
    settings.show_desc = config["commands"]["descs"]["show"]
    settings.info_desc = config["commands"]["descs"]["info"]
    settings.last_desc = config["commands"]["descs"]["last"]
    settings.favorite_desc = config["commands"]["descs"]["favorite"]
    settings.give_desc = config["commands"]["descs"]["give"]
    settings.count_desc = config["commands"]["descs"]["count"]
    settings.rarity_desc = config["commands"]["descs"]["rarity"]
    settings.compare_desc = config["commands"]["descs"]["compare"]

    settings.repository_link = config["info"]["links"]["repository_link"]
    settings.discord_invite = config["info"]["links"]["discord_invite"]
    settings.terms_of_service = config["info"]["links"]["terms_of_service"]
    settings.privacy_policy = config["info"]["links"]["privacy_policy"]
    settings.top_gg = config["info"]["links"]["top_gg"]

    settings.info_description = config["info"]["about"]["description"]
    settings.info_history = config["info"]["about"]["history"]
    settings.developers = config["info"]["about"]["developers"]
    settings.contributors = config["info"]["about"]["contributors"]

    settings.superuser_guild_ids = config["superuser"]["guild_ids"]
    settings.root_role_ids = config["superuser"]["root_role_ids"]
    settings.superuser_role_ids = config["superuser"]["superuser_role_ids"]
    settings.log_channel = config["superuser"]["log_channel"]

    settings.team_owners = config["owners"]["team_members_are_owners"]
    settings.co_owners = config["owners"]["co_owners"]

    settings.prometheus_enabled = config["prometheus"]["enabled"]
    settings.prometheus_host = config["prometheus"]["host"]
    settings.prometheus_port = config["prometheus"]["port"]

    log.info("Loaded the bot settings")
