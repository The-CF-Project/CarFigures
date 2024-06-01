import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from configparser import ConfigParser

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


settings = Settings()


def read_settings(path: "Path"):
    config = ConfigParser()
    config.read(path)

    settings.bot_token = config.get('settings', 'bot_token')
    gateway = config.get('settings', 'gateway_url', fallback=None)
    if gateway == '':
        settings.gateway_url = None
    else:
        settings.gateway_url = config.get('settings', 'gateway_url', fallback=None)
    shard = config.get('settings', 'shard_count')
    if shard == '':  # Check for empty string
        settings.shard_count = None
    else:
        settings.shard_count = config.getint('settings', 'shard_count', fallback=1)
    settings.prefix = config.get('settings', 'text_prefix')
    settings.max_favorites = config.getint('settings', 'max-favorites')
    settings.spawnalert = config.getboolean('settings', 'spawnalert', fallback=True)
    settings.version = config.get('settings', 'version')

    settings.team_owners = config.getboolean('owners', 'team-members-are-owners', fallback=False)
    settings.co_owners = [owner.strip() for owner in config.get('owners', 'co-owners', fallback=[]).split(',')]

    settings.collectible_name = config.get('appearance', 'collectible-name')
    settings.bot_name = config.get('appearance', 'bot-name')
    settings.players_group_cog_name = config.get('appearance', 'players-group-cog-name')
    settings.superuser_group_cog_name = config.get('appearance', 'superuser-group-cog-name')
    settings.cartype_replacement = config.get('appearance', 'cartype')
    settings.country_replacement = config.get('appearance', 'country')
    settings.horsepower_replacement = config.get('appearance', 'horsepower')
    settings.weight_replacement = config.get('appearance', 'weight')
    settings.hp_replacement = config.get('appearance', 'hp')
    settings.kg_replacement = config.get('appearance', 'kg')
    settings.default_embed_color = int(config.get('appearance', 'default-embed-color'), 16)

    settings.repository_link = config.get('info', 'repository-link')
    settings.discord_invite = config.get('info', 'discord-invite')
    settings.terms_of_service = config.get('info', 'terms-of-service')
    settings.privacy_policy = config.get('info', 'privacy_policy')
    settings.top_gg = config.get('info', 'top.gg', fallback=None)

    # Get Credits Information
    settings.developers = config.get('credits', 'developers').split(',')
    settings.contributors = config.get('credits', 'contributors').split(',')
    settings.testers = config.get('credits', 'testers').split(',')

    # Superuser Command Section
    settings.superuser_guild_ids = [int(guild_id.strip()) for guild_id in config.get('superuser-command', 'guild-ids', fallback=[]).split(',')]
    settings.root_role_ids = [int(role_id.strip()) for role_id in config.get('superuser-command', 'root-role-ids', fallback=[]).split(',')]
    settings.superuser_role_ids = [int(role_id.strip()) for role_id in config.get('superuser-command', 'superuser-role-ids', fallback=[]).split(',')]

    # Handle optional settings with potential None values
    try:
        settings.log_channel = config.getint('superuser-command', 'log-channel')
    except ValueError:
        settings.log_channel = None  # Handle potential invalid log_channel value

    # Prometheus Section (assuming all settings are strings)
    settings.prometheus_enabled = config.get('prometheus', 'enabled')
    settings.prometheus_host = config.get('prometheus', 'host')
    settings.prometheus_port = config.get('prometheus', 'port')


