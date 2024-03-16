from typing import TYPE_CHECKING

from carfigures.packages.players.cog import Player

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    await bot.add_cog(Player(bot))