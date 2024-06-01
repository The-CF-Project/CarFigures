from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord

    from carfigures.core.bot import CarFiguresBot
    from carfigures.core.models import CarInstance, Player, Trade


@dataclass(slots=True)
class TradingUser:
    user: "discord.User | discord.Member"
    player: "Player"
    proposal: list["CarInstance"] = field(default_factory=list)
    locked: bool = False
    cancelled: bool = False
    accepted: bool = False

    @classmethod
    async def from_trade_model(cls, trade: "Trade", player: "Player", bot: "CarFiguresBot"):
        proposal = await trade.tradeobjects.filter(player=player).prefetch_related("carinstance")
        user = await bot.fetch_user(player.discord_id)
        return cls(user, player, [x.carinstance for x in proposal])
