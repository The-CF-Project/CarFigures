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

    botToken: str = ""
    botName: str = ""
    gatewayUrl: str | None = None
    shardCount: int | None = None
    prefix: str = ""
    maxFavorites: int = 50
    defaultEmbedColor: int = 0

    spawnMessages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    requiredMessageRange: list[int] = field(default_factory=list)
    catchBonusRate: list[int] = field(default_factory=list)
    wrongNameMessages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    catchButtonMessages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    coolDownTime: int = 0
    minimumMembersRequired: int = 0

    superGuilds: list[int] = field(default_factory=list)
    superUsers: list[int] = field(default_factory=list)
    logChannel: int | None = None
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

    collectibleSingular: str = ""
    collectiblePlural: str = ""
    album: str = ""
    country: str = ""
    exclusive: str = ""
    horsepower: str = ""
    weight: str = ""
    hp: str = ""
    kg: str = ""
    cars: str = ""
    sudo: str = ""
    garageName: str = ""
    garageDesc: str = ""
    exhibitName: str = ""
    exhibitDesc: str = ""
    showName: str = ""
    showDesc: str = ""
    infoName: str = ""
    infoDesc: str = ""
    giftName: str = ""
    giftDesc: str = ""


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

    repositoryLink: str = ""
    serverInvite: str = ""
    termsOfService: str = ""
    privacyPolicy: str = ""

    developers: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)


settings = Settings()
appearance = Appearance()
information = Information()


def read_settings(path: "Path"):
    with open(path, "rb") as f:
        config = tomllib.load(f)

    settings.botToken = config["settings"]["botToken"]
    settings.botName = config["settings"]["botName"]
    settings.prefix = config["settings"]["prefix"]
    settings.gatewayUrl = config["settings"].get("gatewayUrl", None)
    settings.shardCount = config["settings"].get("shardCount", None)

    settings.defaultEmbedColor = int(config["settings"]["defaultEmbedColor"], 16)

    settings.requiredMessageRange = config["spawn-manager"]["requiredMessageRange"]
    settings.catchBonusRate = config["spawn-manager"]["catchBonusRate"]
    settings.wrongNameMessages = config["spawn-manager"]["wrongNameMessages"]
    settings.catchButtonMessages = config["spawn-manager"]["catchButtonMessages"]
    settings.spawnMessages = config["spawn-manager"]["spawnMessages"]
    settings.coolDownTime = config["spawn-manager"]["cooldownTime"]
    settings.minimumMembersRequired = config["spawn-manager"]["minimumMembersRequired"]

    settings.superGuilds = config["team"]["superGuilds"]
    settings.roots = config["team"]["roots"]
    settings.superUsers = config["team"]["superUsers"]
    settings.logChannel = config["team"]["logChannel"]

    settings.prometheusEnabled = config["prometheus"]["enabled"]
    settings.prometheusHost = config["prometheus"]["host"]
    settings.prometheusPort = config["prometheus"]["port"]

    appearance.collectiblePlural = config["appearance"]["interface"]["collectible"]["plural"]
    appearance.collectibleSingular = config["appearance"]["interface"]["collectible"]["singular"]
    appearance.album = config["appearance"]["interface"]["album"]
    appearance.country = config["appearance"]["interface"]["country"]
    appearance.exclusive = config["appearance"]["interface"]["exclusive"]
    appearance.horsepower = config["appearance"]["interface"]["horsepower"]["name"]
    appearance.weight = config["appearance"]["interface"]["weight"]["name"]
    appearance.hp = config["appearance"]["interface"]["horsepower"]["unit"]
    appearance.kg = config["appearance"]["interface"]["weight"]["unit"]

    appearance.cars = config["appearance"]["commands"]["cars"]
    appearance.sudo = config["appearance"]["commands"]["sudo"]
    appearance.garageName = config["appearance"]["commands"]["garage"]["name"]
    appearance.garageDesc = config["appearance"]["commands"]["garage"]["desc"]
    appearance.exhibitName = config["appearance"]["commands"]["exhibit"]["name"]
    appearance.exhibitDesc = config["appearance"]["commands"]["exhibit"]["desc"]
    appearance.showName = config["appearance"]["commands"]["show"]["name"]
    appearance.showDesc = config["appearance"]["commands"]["show"]["desc"]
    appearance.infoName = config["appearance"]["commands"]["info"]["name"]
    appearance.infoDesc = config["appearance"]["commands"]["info"]["desc"]
    appearance.giftName = config["appearance"]["commands"]["gift"]["name"]
    appearance.giftDesc = config["appearance"]["commands"]["gift"]["desc"]

    information.repositoryLink = config["information"]["repositoryLink"]
    information.serverInvite = config["information"]["serverInvite"]
    information.termsOfService = config["information"]["termsOfService"]
    information.privacyPolicy = config["information"]["privacyPolicy"]
    information.developers = config["information"]["developers"]
    information.contributors = config["information"]["contributors"]

    log.info("Loaded the bot settings")
