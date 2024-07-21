from typing import TYPE_CHECKING

from carfigures.packages.battle.cog import Battle

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    await bot.add_cog(Battle(bot))
