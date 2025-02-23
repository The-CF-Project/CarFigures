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
    botToken: str
        Discord token for the bot to connect
    gatewayUrl: str | None
        The URL of the Discord gateway that this instance of the bot should connect to and use.
    shardCount: int | None
        The number of shards to use for this bot instance.
        Must be equal to the one set in the gateway proxy if used.
    prefix: str
        Prefix for text commands, mostly unused. Defaults to "b."
    botName: str
        Usually "CarFigures", can be replaced when possible
    superguilds: list[int]
        List of guilds where the /sudo command must be registered
    roots: list[int]
        List of roles that have full access to the admin commands
    supers: list[int]
        List of roles that have partial access to the admin commands (only blacklist and guilds)
    """

    bot_token: str = ""
    bot_name: str = ""
    gatewayUrl: str | None = None
    shardCount: int | None = None
    prefix: str = ""
    max_favorites: int = 50
    default_embed_color: int = 0

    spawn_messages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    required_message_range: list[int] = field(default_factory=list)
    catch_bonus_rate: list[int] = field(default_factory=list)
    wrong_name_messages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    catch_button_messages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    cooldown_time: int = 0
    minimum_members_required: int = 0

    superguilds: list[int] = field(default_factory=list)
    superusers: list[int] = field(default_factory=list)
    log_channel: int | None = None
    roots: list[int] = field(default_factory=list)

    # metrics and prometheus
    prometheusEnabled: bool = False
    prometheusHost: str = "0.0.0.0"
    prometheusPort: int = 15260


@dataclass
class Appearance:
    """
    Global appearance settings

    Attributes
    ----------
    collectibleSingular: str
        Usually "carfigure", can be replaced when possible
    collectiblePlural: str
        Usually "carfigures", can be replaced when possible
    cartype: str
    """

    collectible_singular: str = ""
    collectible_plural: str = ""
    album: str = ""
    country: str = ""
    exclusive: str = ""
    horsepower: str = ""
    weight: str = ""
    hp: str = ""
    kg: str = ""
    cars: str = ""
    sudo: str = ""
    garage_name: str = ""
    garage_desc: str = ""
    exhibit_name: str = ""
    exhibit_desc: str = ""
    show_name: str = ""
    show_desc: str = ""
    info_name: str = ""
    info_desc: str = ""
    gift_name: str = ""
    gift_desc: str = ""


@dataclass
class Information:
    """
    Global bot Information

    Attributes
    ----------
    repository_link: str
        Used in the /info bot command
    discord_invite: str
        Used in the /info bot command
    terms_of_service: str
        Used in the /info bot command
    privacy_policy: str
        Used in the /info bot command
    """

    repository_link: str = ""
    server_invite: str = ""
    terms_of_service: str = ""
    privacy_policy: str = ""

    developers: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)


settings = Settings()
appearance = Appearance()
information = Information()


def read_settings(path: "Path"):
    with open(path, "rb") as f:
        config = tomllib.load(f)

    settings.bot_token = config["settings"]["botToken"]
    settings.bot_name = config["settings"]["botName"]
    settings.prefix = config["settings"]["prefix"]
    settings.gatewayUrl = config["settings"].get("gatewayUrl", None)
    settings.shardCount = config["settings"].get("shardCount", None)
    settings.default_embed_color = int(config["settings"]["defaultEmbedColor"], 16)

    settings.required_message_range = config["spawn-manager"]["requiredMessageRange"]
    settings.catch_bonus_rate = config["spawn-manager"]["catchBonusRate"]
    settings.wrong_name_messages = config["spawn-manager"]["wrongNameMessages"]
    settings.catch_button_messages = config["spawn-manager"]["catchButtonMessages"]
    settings.spawn_messages = config["spawn-manager"]["spawnMessages"]
    settings.cooldown_time = config["spawn-manager"]["cooldownTime"]
    settings.minimum_members_required = config["spawn-manager"]["minimumMembersRequired"]

    settings.superguilds = config["team"]["superGuilds"]
    settings.roots = config["team"]["roots"]
    settings.superusers = config["team"]["superUsers"]
    settings.log_channel = config["team"]["logChannel"]

    settings.prometheusEnabled = config["prometheus"]["enabled"]
    settings.prometheusHost = config["prometheus"]["host"]
    settings.prometheusPort = config["prometheus"]["port"]

    appearance.collectible_plural = config["appearance"]["interface"]["collectible"]["plural"]
    appearance.collectible_singular = config["appearance"]["interface"]["collectible"]["singular"]
    appearance.album = config["appearance"]["interface"]["album"]
    appearance.country = config["appearance"]["interface"]["country"]
    appearance.exclusive = config["appearance"]["interface"]["exclusive"]
    appearance.horsepower = config["appearance"]["interface"]["horsepower"]["name"]
    appearance.weight = config["appearance"]["interface"]["weight"]["name"]
    appearance.hp = config["appearance"]["interface"]["horsepower"]["unit"]
    appearance.kg = config["appearance"]["interface"]["weight"]["unit"]

    appearance.cars = config["appearance"]["commands"]["cars"]
    appearance.sudo = config["appearance"]["commands"]["sudo"]
    appearance.garage_name = config["appearance"]["commands"]["garage"]["name"]
    appearance.garage_desc = config["appearance"]["commands"]["garage"]["desc"]
    appearance.exhibit_name = config["appearance"]["commands"]["exhibit"]["name"]
    appearance.exhibit_desc = config["appearance"]["commands"]["exhibit"]["desc"]
    appearance.show_name = config["appearance"]["commands"]["show"]["name"]
    appearance.show_desc = config["appearance"]["commands"]["show"]["desc"]
    appearance.info_name = config["appearance"]["commands"]["info"]["name"]
    appearance.info_desc = config["appearance"]["commands"]["info"]["desc"]
    appearance.gift_name = config["appearance"]["commands"]["gift"]["name"]
    appearance.gift_desc = config["appearance"]["commands"]["gift"]["desc"]

    information.repository_link = config["information"]["repositoryLink"]
    information.server_invite = config["information"]["serverInvite"]
    information.terms_of_service = config["information"]["termsOfService"]
    information.privacy_policy = config["information"]["privacyPolicy"]
    information.developers = config["information"]["developers"]
    information.contributors = config["information"]["contributors"]

    log.info("Loaded the bot settings")
