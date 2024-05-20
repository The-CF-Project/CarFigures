from typing import TYPE_CHECKING

from carfigures.packages.carfigures.cog import CarFiguresSpawner

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    cog = CarFiguresSpawner(bot)
    await bot.add_cog(cog)
    await cog.load_cache()
