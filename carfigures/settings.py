import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import yaml

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
        List of roles that have full access to the /super command
    superuser_role_ids: list[int]
        List of roles that have partial access to the /super command (only blacklist and guilds)
    """

    bot_token: str = ""
    gateway_url: str | None = None
    shard_count: int | None = None
    prefix: str = ""

    collectible_name: str = ""
    bot_name: str = ""
    players_group_cog_name: str = ""
    max_favorites: int = 50

    # /info bot
    info_description: str = ""
    repository_link: str = ""
    discord_invite: str = ""
    terms_of_service: str = ""
    privacy_policy: str = ""
    top_gg: str = ""

    # /super
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
    content = yaml.load(path.read_text(), yaml.Loader)

    settings.bot_token = content["discord-token"]
    settings.gateway_url = content.get("gateway-url")
    settings.shard_count = content.get("shard-count")
    settings.prefix = content["text-prefix"]
    settings.team_owners = content.get("owners", {}).get("team-members-are-owners", False)
    settings.co_owners = content.get("owners", {}).get("co-owners", [])

    settings.collectible_name = content["collectible-name"]
    settings.bot_name = content["bot-name"]
    settings.players_group_cog_name = content["players-group-cog-name"]
    settings.max_favorites = content.get("max-favorites", 50)

    settings.about_description = content["info"]["description"]
    settings.repository_link = content["info"]["repository-link"]
    settings.discord_invite = content["info"]["discord-invite"]
    settings.terms_of_service = content["info"]["terms-of-service"]
    settings.privacy_policy = content["info"]["privacy-policy"]
    settings.top_gg = content["info"]["top.gg"] or []

    settings.superuser_guild_ids = content["superuser-command"]["guild-ids"] or []
    settings.root_role_ids = content["superuser-command"]["root-role-ids"] or []
    settings.superuser_role_ids = content["superuser-command"]["superuser-role-ids"] or []

    settings.log_channel = content.get("log-channel", None)

    settings.prometheus_enabled = content["prometheus"]["enabled"]
    settings.prometheus_host = content["prometheus"]["host"]
    settings.prometheus_port = content["prometheus"]["port"]
    log.info("Settings loaded.")


def write_default_settings(path: "Path"):
    path.write_text(
        """# yaml-language-server: $schema=json-config-ref.json

# paste the bot token after regenerating it here
discord-token: YOUR DISCORD TOKEN HERE

# prefix for old-style text commands, mostly unused
text-prefix: c.

# define the elements given with the /info status command
info:

  # define the beginning of the description of /info status
  # the other parts is automatically generated
  description: >
    Collect carfigures on Discord, exchange them and battle with friends!

  # override this if you have a fork
  repository-link: https://codeberg.org/Lucrative/CarFigures

  # valid invite for a Discord server
  discord-invite: https://discord.gg/PVFyN34ykA  # CarFigures official server

  terms-of-service: https://gist.github.com/GamingadlerHD/ab167753d4a479fbf0535750891d4412
  privacy-policy: https://gist.github.com/GamingadlerHD/31d6601feef544b3f3a35560b42e5496
  top.gg: https://top.gg/bot/1073275888466145370

# INTEGRATION IS STILL BEING FULLY MADE
# override the name "carfigure" in the bot
collectible-name: carfigure

# INTEGRATION IS STILL BEING FULLY MADE
# override the name "CarFigures" in the bot
bot-name: CarFigures

# players group cog command name
# this is /cars by default, but you can change it for /animals or /rocks for example
players-group-cog-name: cars

# enables the /sudo command
superuser-command:

  # all items here are list of IDs. example on how to write IDs in a list:
  # guild-ids:
  #   - 1049118743101452329
  #   - 1078701108500897923

  # list of guild IDs where /sudo should be registered
  guild-ids:
      - YOUR SERVER ID HERE

  # list of role IDs having full access to /sudo
  root-role-ids:
      - YOUR ROLE ID HERE

  # list of role IDs having partial access to /sudo
  superuser-role-ids:
      - ADMIN ROLE ID HERE

# log channel for moderation actions
log-channel: LOGS CHANNEL ID HERE

# manage bot ownership
owners:
  # if enabled and the application is under a team, all team members will be considered as owners
  team-members-are-owners: false

  # a list of IDs that must be considered owners in addition to the application/team owner
  co-owners:
    - YOUR DISCORD ID HERE

# prometheus metrics collection, leave disabled if you don't know what this is
prometheus:
  enabled: false
  host: "0.0.0.0"
  port: 15260
  """  # noqa: W291
    )


def update_settings(path: "Path"):
    content = path.read_text()

    add_owners = True
    add_config_ref = "# yaml-language-server: $schema=json-config-ref.json" not in content

    for line in content.splitlines():
        if line.startswith("owners:"):
            add_owners = False

    if add_owners:
        content += """
# manage bot ownership
owners:
  # if enabled and the application is under a team, all team members will be considered as owners
  team-members-are-owners: false

  # a list of IDs that must be considered owners in addition to the application/team owner
  co-owners:
"""
    if add_config_ref:
        if "# yaml-language-server: $schema=config-ref.json" in content:
            # old file name replacement
            content = content.replace("$schema=config-ref.json", "$schema=json-config-ref.json")
        else:
            content = "# yaml-language-server: $schema=json-config-ref.json\n" + content

    if any((add_owners, add_config_ref)):
        path.write_text(content)
