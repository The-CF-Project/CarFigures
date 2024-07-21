from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord

    from carfigures.core.bot import CarFiguresBot
    from carfigures.core.models import CarInstance, Player
    from carfigures.core.models import Trade as Battle


@dataclass(slots=True)
class BattlingUser:
    user: "discord.User | discord.Member"
    player: "Player"
    proposal: list["CarInstance"] = field(default_factory=list)
    locked: bool = False
    cancelled: bool = False
    accepted: bool = False

    @classmethod
    async def from_battle_model(cls, battle: "Battle", player: "Player", bot: "CarFiguresBot"):
        proposal = await battle.tradeobjects.filter(player=player).prefetch_related("carinstance")
        user = await bot.fetch_user(player.discord_id)
        return cls(user, player, [x.carinstance for x in proposal])
