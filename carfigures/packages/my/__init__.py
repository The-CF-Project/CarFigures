from typing import TYPE_CHECKING

from carfigures.packages.my.cog import My

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    await bot.add_cog(My(bot))
