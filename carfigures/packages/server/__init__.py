from typing import TYPE_CHECKING

from carfigures.packages.server.cog import Server

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot


async def setup(bot: "CarFiguresBot"):
    await bot.add_cog(Server(bot))
