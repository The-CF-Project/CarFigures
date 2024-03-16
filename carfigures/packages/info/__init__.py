from typing import TYPE_CHECKING

from carfigures.packages.info.cog import Info

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    await bot.add_cog(Info(bot))
