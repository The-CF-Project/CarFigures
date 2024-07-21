from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord

    from ballsdex.core.bot import BallsDexBot
    from ballsdex.core.models import BallInstance, Player
    from ballsdex.core.models import Trade as Battle


@dataclass(slots=True)
class BattlingUser:
    user: "discord.User | discord.Member"
    player: "Player"
    proposal: list["BallInstance"] = field(default_factory=list)
    locked: bool = False
    cancelled: bool = False
    accepted: bool = False

    @classmethod
    async def from_battle_model(cls, battle: "Battle", player: "Player", bot: "BallsDexBot"):
        proposal = await battle.tradeobjects.filter(player=player).prefetch_related("ballinstance")
        user = await bot.fetch_user(player.discord_id)
        return cls(user, player, [x.ballinstance for x in proposal])
