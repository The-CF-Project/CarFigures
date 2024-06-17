import logging
from typing import TYPE_CHECKING

from discord import app_commands

from carfigures.packages.superuser.cog import SuperUser
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.packages.superuser")


def command_count(cog: SuperUser) -> int:
    total = 0
    for command in cog.walk_app_commands():
        total += len(command.name) + len(command.description)
        if isinstance(command, app_commands.Group):
            continue
        for param in command.parameters:
            total += len(param.name) + len(param.description)
            for choice in param.choices:
                total += len(choice.name) + (
                    int(choice.value)
                    if isinstance(choice.value, int | float)
                    else len(choice.value)
                )
    return total


def strip_descriptions(cog: SuperUser):
    for command in cog.walk_app_commands():
        command.description = "."
        if isinstance(command, app_commands.Group):
            continue
        for param in command.parameters:
            param._Parameter__parent.description = "."  # type: ignore


async def setup(bot: "CarFiguresBot"):
    n = SuperUser(bot)
    if command_count(n) > 3900:
        strip_descriptions(n)
        group_name = settings.group_cog_names["superuser"]
        log.warning(f"/{group_name} command too long, stripping descriptions")
    await bot.add_cog(n)
