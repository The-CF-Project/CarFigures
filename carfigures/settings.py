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
    alreadyCaughtMessage: str = ""
    catchButtonText: str = ""
    coolDownTime: int = 0
    minimumMembersRequired: int = 0

    superGuilds: list[int] = field(default_factory=list)
    superUsers: list[int] = field(default_factory=list)
    logChannel: int | None = None
    teamMembersAreOwners: bool = False
    co_owners: list[int] = field(default_factory=list)

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
    cartype: str = ""
    country: str = ""
    exclusive: str = ""
    horsepower: str = ""
    weight: str = ""
    hp: str = ""
    kg: str = ""
    cars: str = ""
    sudo: str = ""
    garageName: str = ""
    exhibitName: str = ""
    showName: str = ""
    infoName: str = ""
    lastName: str = ""
    giftName: str = ""
    garageDesc: str = ""
    exhibitDesc: str = ""
    showDesc: str = ""
    infoDesc: str = ""
    lastDesc: str = ""
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
    settings.defaultEmbedColor = int(config["settings"]["defaultEmbedColor"], 16)

    settings.requiredMessageRange = config["spawn-manager"]["requiredMessageRange"]
    settings.catchBonusRate = config["spawn-manager"]["catchBonusRate"]
    settings.alreadyCaughtMessage = config["spawn-manager"]["alreadyCaughtMessage"]
    settings.spawnMessages = config["spawn-manager"]["spawnMessages"]
    settings.catchButtonText = config["spawn-manager"]["catchButtonText"]
    settings.coolDownTime = config["spawn-manager"]["cooldownTime"]
    settings.minimumMembersRequired = config["spawn-manager"]["minimumMembersRequired"]

    settings.superGuilds = config["team"]["superGuilds"]
    settings.teamMembersAreOwners = config["team"]["teamMembersAreOwners"]
    settings.co_owners = config["team"]["co-owners"]
    settings.superUsers = config["team"]["superUsers"]
    settings.logChannel = config["team"]["logChannel"]

    settings.prometheusEnabled = config["prometheus"]["enabled"]
    settings.prometheusHost = config["prometheus"]["host"]
    settings.prometheusPort = config["prometheus"]["port"]

    appearance.collectiblePlural = config["appearance"]["interface"]["collectiblePlural"]
    appearance.collectibleSingular = config["appearance"]["interface"]["collectibleSingular"]
    appearance.cartype = config["appearance"]["interface"]["cartype"]
    appearance.country = config["appearance"]["interface"]["country"]
    appearance.exclusive = config["appearance"]["interface"]["exclusive"]
    appearance.horsepower = config["appearance"]["interface"]["horsepower"]
    appearance.weight = config["appearance"]["interface"]["weight"]
    appearance.hp = config["appearance"]["interface"]["hp"]
    appearance.kg = config["appearance"]["interface"]["kg"]

    appearance.cars = config["appearance"]["commands"]["names"]["cars"]
    appearance.sudo = config["appearance"]["commands"]["names"]["sudo"]
    appearance.garageName = config["appearance"]["commands"]["names"]["garage"]
    appearance.exhibitName = config["appearance"]["commands"]["names"]["exhibit"]
    appearance.showName = config["appearance"]["commands"]["names"]["show"]
    appearance.infoName = config["appearance"]["commands"]["names"]["info"]
    appearance.lastName = config["appearance"]["commands"]["names"]["last"]
    appearance.giftName = config["appearance"]["commands"]["names"]["gift"]
    appearance.garageDesc = config["appearance"]["commands"]["descs"]["garage"]
    appearance.exhibitDesc = config["appearance"]["commands"]["descs"]["exhibit"]
    appearance.showDesc = config["appearance"]["commands"]["descs"]["show"]
    appearance.infoDesc = config["appearance"]["commands"]["descs"]["info"]
    appearance.lastDesc = config["appearance"]["commands"]["descs"]["last"]
    appearance.giftDesc = config["appearance"]["commands"]["descs"]["gift"]

    information.repositoryLink = config["information"]["repositoryLink"]
    information.serverInvite = config["information"]["serverInvite"]
    information.termsOfService = config["information"]["termsOfService"]
    information.privacyPolicy = config["information"]["privacyPolicy"]
    information.developers = config["information"]["developers"]
    information.contributors = config["information"]["contributors"]

    log.info("Loaded the bot settings")
