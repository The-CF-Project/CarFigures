from typing import TYPE_CHECKING

from carfigures.packages.cars.cog import Cars

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    await bot.add_cog(Cars(bot))
