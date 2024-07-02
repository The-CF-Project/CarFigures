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

    bot_token: str = "YOUR_DISCORD_BOT_TOKEN"
    bot_name: str = "CarFigures"
    gateway_url: str | None = None
    shard_count: int | None = None
    prefix: str = "!"
    spawnalert: bool = False
    max_favorites: int = 50
    default_embed_color: int = 0xFF5733
    profiles_emojis: bool = False

    collectible_name: str = "carfigure"
    cartype_replacement: str = "CarType"
    country_replacement: str = "Country"
    horsepower_replacement: str = "Horsepower"
    weight_replacement: str = "Weight"
    hp_replacement: str = "HP"
    kg_replacement: str = "KG"

    cars_group_name: str = "cars"
    sudo_group_name: str = "sudo"
    info_group_name: str = "info"
    trade_group_name: str = "trade"
    server_group_name: str = "server"
    player_group_name: str = "player"

    garage_command_name: str = "garage"
    exhibit_command_name: str = "exhibit"
    show_command_name: str = "show"
    info_command_name: str = "info"
    last_command_name: str = "last"
    favorite_command_name: str = "favorite"
    give_command_name: str = "give"
    count_command_name: str = "count"
    rarity_command_name: str = "rarity"
    compare_command_name: str = "compare"

    garage_command_desc: str = "Show your garage!"
    exhibit_command_desc: str = "Show your showroom in the bot."
    show_command_desc: str = "Display info from your carfigures collection."
    info_command_desc: str = "Display info from a specific carfigure."
    last_command_desc: str = "Display info of your or another user's last caught carfigure."
    favorite_command_desc: str = "Set favorite carfigures."
    give_command_desc: str = "Give a carfigure to a user."
    count_command_desc: str = "Count how many carfigures you have."
    rarity_command_desc: str = "Show the rarity list of the bot."
    compare_command_desc: str = "Compare two carfigures."

    # /info status
    repository_link: str = "https://github.com/The-CF-Project/CarFigures"
    discord_invite: str = "https://discord.gg/PVFyN34ykA"
    terms_of_service: str = "https://github.com/The-CF-Project/CarFigures/blob/stable/assets/TERMS_OF_SERVICE.md"
    privacy_policy: str = "https://github.com/The-CF-Project/CarFigures/blob/stable/assets/PRIVACY_POLICY.md"
    top_gg: str = "https://github.com/The-CF-Project/CarFigures/blob/stable"
    bot_contributors: list[str] = field(default_factory=list)

    # /info about
    bot_description: str = """
    CarFigures (CF) was born out of frustration with the BallsDex team's decisions. Initially, I had no particular liking for the idea; it was more about a response to dissatisfaction. The BallsDex team wasn't keen on implementing features that many of us wanted. I knew that merely complaining wouldn't lead to any change, as hundreds of others had already done so to no avail.

    Determined to make a difference, I decided to take matters into my own hands. By forking BallsDex and applying my own changes and preferences, CarFigures came into existence.

    CarFigures aims to address the community's frustrations and provide an alternative base to use and build their bots on. It's a project driven by a desire for improvement and a commitment to providing a better user experience.
    """
    bot_history: str = ""

    # /sudo
    superuser_guild_ids: list[int] = field(default_factory=list)
    root_role_ids: list[int] = field(default_factory=list)
    superuser_role_ids: list[int] = field(default_factory=list)
    log_channel: int = 1144639514296459316

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

    settings.bot_token = config["bot_token"]
    settings.bot_name = config.get("bot_name", settings.bot_name)
    settings.bot_description = config.get("info", {}).get("bot_description", settings.bot_description)
    settings.bot_history = config.get("info", {}).get("bot_history", settings.bot_history)
    settings.bot_contributors = config.get("info", {}).get("contributors", settings.bot_contributors)
    settings.prefix = config.get("prefix", settings.prefix)
    settings.spawnalert = config.get("spawnalert", settings.spawnalert)
    settings.default_embed_color = int(config.get("default_embed_color", hex(settings.default_embed_color)), 16)
    settings.profiles_emojis = config.get("profiles_emojis", settings.profiles_emojis)

    settings.collectible_name = config.get("appearance", {}).get("collectible_name", settings.collectible_name)
    settings.cartype_replacement = config.get("appearance", {}).get("cartype_name", settings.cartype_replacement)
    settings.country_replacement = config.get("appearance", {}).get("country_name", settings.country_replacement)
    settings.horsepower_replacement = config.get("appearance", {}).get("horsepower_name", settings.horsepower_replacement)
    settings.weight_replacement = config.get("appearance", {}).get("weight_name", settings.weight_replacement)
    settings.hp_replacement = config.get("appearance", {}).get("hp_replacement", settings.hp_replacement)
    settings.kg_replacement = config.get("appearance", {}).get("kg_replacement", settings.kg_replacement)

    settings.cars_group_name = config.get("commands", {}).get("cars_group_name", settings.cars_group_name)
    settings.sudo_group_name = config.get("commands", {}).get("sudo_group_name", settings.sudo_group_name)
    settings.info_group_name = config.get("commands", {}).get("info_group_name", settings.info_group_name)
    settings.trade_group_name = config.get("commands", {}).get("trade_group_name", settings.trade_group_name)
    settings.server_group_name = config.get("commands", {}).get("server_group_name", settings.server_group_name)
    settings.player_group_name = config.get("commands", {}).get("player_group_name", settings.player_group_name)

    settings.garage_command_name = config.get("commands", {}).get("garage_command_name", settings.garage_command_name)
    settings.exhibit_command_name = config.get("commands", {}).get("exhibit_command_name", settings.exhibit_command_name)
    settings.show_command_name = config.get("commands", {}).get("show_command_name", settings.show_command_name)
    settings.info_command_name = config.get("commands", {}).get("info_command_name", settings.info_command_name)
    settings.last_command_name = config.get("commands", {}).get("last_command_name", settings.last_command_name)
    settings.favorite_command_name = config.get("commands", {}).get("favorite_command_name", settings.favorite_command_name)
    settings.give_command_name = config.get("commands", {}).get("give_command_name", settings.give_command_name)
    settings.count_command_name = config.get("commands", {}).get("count_command_name", settings.count_command_name)
    settings.rarity_command_name = config.get("comments", {}).get("rarity_command_name", settings.rarity_command_name)
    settings.compare_command_name = config.get("commands", {}).get("compare_command_name", settings.compare_command_name)

    settings.garage_command_desc = config.get("commands", {}).get("garage_command_desc", settings.garage_command_desc)
    settings.exhibit_command_desc = config.get("commands", {}).get("exhibit_command_desc", settings.exhibit_command_desc)
    settings.show_command_desc = config.get("commands", {}).get("show_command_desc", settings.show_command_desc)
    settings.info_command_desc = config.get("commands", {}).get("info_command_desc", settings.info_command_desc)
    settings.last_command_desc = config.get("commands", {}).get("last_command_name", settings.last_command_desc)
    settings.favorite_command_desc = config.get("commands", {}).get("favorite_command_desc", settings.favorite_command_desc)
    settings.give_command_desc = config.get("commands", {}).get("give_command_desc", settings.give_command_desc)
    settings.count_command_desc = config.get("commands", {}).get("count_command_desc", settings.count_command_desc)
    settings.rarity_command_desc = config.get("commands", {}).get("rarity_command_desc", settings.rarity_command_desc)
    settings.compare_command_desc = config.get("commands", {}).get("compare_command_desc", settings.compare_command_desc)

    settings.repository_link = config.get("links", {}).get("repository_link", settings.repository_link)
    settings.discord_invite = config.get("links", {}).get("discord_invite", settings.discord_invite)
    settings.terms_of_service = config.get("links", {}).get("terms_of_service", settings.repository_link)
    settings.privacy_policy = config.get("links", {}).get("privacy_policy", settings.privacy_policy)
    settings.top_gg = config.get("links", {}).get("top_gg", settings.top_gg)

    settings.superuser_guild_ids = config.get("superuser", {}).get("guild_ids", [])
    settings.root_role_ids = config.get("superuser", {}).get("root_role_ids", [])
    settings.superuser_role_ids = config.get("superuser", {}).get("superuser_role_ids", [])
    settings.log_channel = config.get("superuser", {}).get("log_channel", settings.log_channel)

    settings.team_owners = config.get("team_members_are_owners", settings.team_owners)
    settings.co_owners = config.get("co_owners", settings.co_owners)

    settings.prometheus_enabled = config.get("prometheus", {}).get("enabled", settings.prometheus_enabled)
    settings.prometheus_host = config.get("prometheus", {}).get("host", settings.prometheus_host)
    settings.prometheus_port = config.get("prometheus", {}).get("port", settings.prometheus_port)

    log.info("Loaded the bot settings")

