import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import tomllib

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("carfigures.settings")


@dataclass
class Settings:
    bot_token: str = ""
    bot_name: str = ""
    gateway_url: str | None = None
    shard_count: int | None = None
    prefix: str = ""
    spawnalert: bool = False
    minimal_profile: bool = False
    max_favorites: int = 50
    default_embed_color: int = 0
    team_members: list[str] = field(default_factory=list)
    team_owners: bool = False
    co_owners: list[int] = field(default_factory=list)
    prometheus_enabled: bool = False
    prometheus_host: str = "0.0.0.0"
    prometheus_port: int = 15260


@dataclass
class Appearance:
    collectible_singular: str = ""
    collectible_plural: str = ""
    cartype: str = ""
    country: str = ""
    horsepower: str = ""
    weight: str = ""
    hp: str = ""
    kg: str = ""


@dataclass
class CommandConf:
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
    gift_name: str = ""
    count_name: str = ""
    rarity_name: str = ""
    compare_name: str = ""

    garage_desc: str = ""
    exhibit_desc: str = ""
    show_desc: str = ""
    info_desc: str = ""
    last_desc: str = ""
    favorite_desc: str = ""
    gift_desc: str = ""
    count_desc: str = ""
    rarity_desc: str = ""
    compare_desc: str = ""


@dataclass
class Information:
    repository_link: str = ""
    discord_invite: str = ""
    terms_of_service: str = ""
    privacy_policy: str = ""
    top_gg: str = ""


@dataclass
class SuperUser:
    guilds: list[int] = field(default_factory=list)
    roots: list[int] = field(default_factory=list)
    supers: list[int] = field(default_factory=list)
    log_channel: int | None = None


settings = Settings()
appearance = Appearance()
commandconfig = CommandConf()
information = Information()
superuser = SuperUser()


def read_settings(path: "Path"):
    with open(path, "rb") as f:
        config = tomllib.load(f)

    settings.bot_token = config["settings"]["bot_token"]
    settings.bot_name = config["settings"]["bot_name"]
    settings.prefix = config["settings"]["text_prefix"]
    settings.minimal_profile = config["settings"]["minimal_profile"]
    settings.spawnalert = config["settings"]["spawnalert"]
    settings.default_embed_color = int(config["settings"]["default_embed_color"], 16)
    settings.team_members = config["team"]["members"]
    
    appearance.collectible_singular = config["appearance"]["collectible_singular"]
    appearance.collectible_plural = config["appearance"]["collectible_plural"]
    appearance.cartype = config["appearance"]["cartype"]
    appearance.country = config["appearance"]["country"]
    appearance.horsepower = config["appearance"]["horsepower"]
    appearance.weight = config["appearance"]["weight"]
    appearance.hp = config["appearance"]["hp"]
    appearance.kg = config["appearance"]["kg"]

    commandconfig.cars_group = config["commands"]["groups"]["cars"]
    commandconfig.sudo_group = config["commands"]["groups"]["sudo"]
    commandconfig.info_group = config["commands"]["groups"]["info"]
    commandconfig.my_group = config["commands"]["groups"]["my"]
    commandconfig.trade_group = config["commands"]["groups"]["trade"]

    commandconfig.garage_name = config["commands"]["names"]["garage"]
    commandconfig.exhibit_name = config["commands"]["names"]["exhibit"]
    commandconfig.show_name = config["commands"]["names"]["show"]
    commandconfig.info_name = config["commands"]["names"]["info"]
    commandconfig.last_name = config["commands"]["names"]["last"]
    commandconfig.favorite_name = config["commands"]["names"]["favorite"]
    commandconfig.gift_name = config["commands"]["names"]["gift"]
    commandconfig.count_name = config["commands"]["names"]["count"]
    commandconfig.rarity_name = config["commands"]["names"]["rarity"]
    commandconfig.compare_name = config["commands"]["names"]["compare"]

    commandconfig.garage_desc = config["commands"]["descs"]["garage"]
    commandconfig.exhibit_desc = config["commands"]["descs"]["exhibit"]
    commandconfig.show_desc = config["commands"]["descs"]["show"]
    commandconfig.info_desc = config["commands"]["descs"]["info"]
    commandconfig.last_desc = config["commands"]["descs"]["last"]
    commandconfig.favorite_desc = config["commands"]["descs"]["favorite"]
    commandconfig.gift_desc = config["commands"]["descs"]["gift"]
    commandconfig.count_desc = config["commands"]["descs"]["count"]
    commandconfig.rarity_desc = config["commands"]["descs"]["rarity"]
    commandconfig.compare_desc = config["commands"]["descs"]["compare"]

    information.repository_link = config["links"]["repository_link"]
    information.discord_invite = config["links"]["discord_invite"]
    information.terms_of_service = config["links"]["terms_of_service"]
    information.privacy_policy = config["links"]["privacy_policy"]
    information.top_gg = config["links"]["top_gg"]

    superuser.guilds = config["superuser"]["guild_ids"]
    superuser.roots = config["superuser"]["root_role_ids"]
    superuser.supers = config["superuser"]["superuser_role_ids"]
    superuser.log_channel = config["superuser"]["log_channel"]

    settings.team_owners = config["team"]["team_members_are_owners"]
    settings.co_owners = config["team"]["co_owners"]

    settings.prometheus_enabled = config["prometheus"]["enabled"]
    settings.prometheus_host = config["prometheus"]["host"]
    settings.prometheus_port = config["prometheus"]["port"]

    log.info("Loaded the bot settings")
