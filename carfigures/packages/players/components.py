import discord
import random
from tortoise.expressions import Q
from io import BytesIO
from carfigures.core.models import (
    CarInstance,
    Car,
    Trade,
    TradeObject,
    Player as PlayerModel,
    cars as carfigures,
)
from carfigures.settings import settings


async def _get_10_cars_emojis(self) -> list[discord.Emoji]:
    """
    Return a list of up to 10 Discord emojis representing cars.
    """
    cars: list[Car] = random.choices(
        [x for x in carfigures.values() if x.enabled], k=min(10, len(carfigures))
    )
    emotes: list[discord.Emoji] = []
    for car in cars:
        if emoji := self.bot.get_emoji(car.emoji_id):
            emotes.append(emoji)
    return emotes


async def get_items_csv(player: PlayerModel) -> BytesIO:
    """
    Get a CSV file with all items of the player.
    """
    cars = await CarInstance.filter(player=player).prefetch_related("car", "trade_player", "event")
    txt = (
        f"id,hex id,{settings.collectible_name},catch date,trade_player"
        ",event,limited,horsepower,horsepower bonus,kg,kg_bonus\n"
    )
    for car in cars:
        txt += (
            f"{car.id},{car.id:0X},{car.car.full_name},{car.catch_date},"  # type: ignore
            f"{car.trade_player.discord_id if car.trade_player else 'None'},{car.event},"
            f"{car.limited},{car.horsepower},{car.horsepower_bonus},{car.weight},{car.weight_bonus}\n"
        )
    return BytesIO(txt.encode("utf-8"))


async def get_trades_csv(player: PlayerModel) -> BytesIO:
    """
    Get a CSV file with all trades of the player.
    """
    trade_history = (
        await Trade.filter(Q(player1=player) | Q(player2=player))
        .order_by("date")
        .prefetch_related("player1", "player2")
    )
    txt = "id,date,player1,player2,player1 received,player2 received\n"
    for trade in trade_history:
        player1_items = await TradeObject.filter(
            trade=trade, player=trade.player1
        ).prefetch_related("carinstance")
        player2_items = await TradeObject.filter(
            trade=trade, player=trade.player2
        ).prefetch_related("carinstance")
        txt += (
            f"{trade.id},{trade.date},{trade.player1.discord_id},{trade.player2.discord_id},"
            f"{','.join([i.carinstance.to_string() for i in player2_items])},"  # type: ignore
            f"{','.join([i.carinstance.to_string() for i in player1_items])}\n"  # type: ignore
        )
    return BytesIO(txt.encode("utf-8"))
