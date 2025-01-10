import asyncio
import logging
import random
from collections import deque, namedtuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import cast
from carfigures.settings import settings


import discord

from carfigures.packages.carfigures.carfigure import CarFigure

log = logging.getLogger("carfigures.packages.carfigures")
CachedMessage = namedtuple("CachedMessage", ["content", "author_id"])


@dataclass
class SpawnCooldown:
    """
    Represents the spawn internal system per guild. Contains the counters that will determine
    if a carfigure should be spawned next or not.

    Attributes
    ----------
    time: datetime
        Time when the object was initialized. Block spawning when it's been less than two minutes
    amount: float
        A number starting at 0, incrementing with the messages until reaching `chance`. At this
        point, a car will be spawned next.
    chance: int
        The number `amount` has to reach for spawn. Determined randomly.
    lock: asyncio.Lock
        Used to rate-limit messages and ignore fast spam
    message_cache: ~collections.deque[CachedMessage]
        A list of recent messages used to reduce the spawn chance when too few different chatters
        are present. Limited to the 100 most recent messages in the guild.
    """

    time: datetime
    # initialize partially started, to reduce the dead time after starting the bot
    scaledMessageCount: float = field(
        default_factory=lambda: float(settings.requiredMessageRange[0] // 2)
    )
    cachedMessagesSet: set[str] = field(default_factory=set)
    chance: int = field(default_factory=lambda: random.randint(*settings.requiredMessageRange))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    messageCache: deque[CachedMessage] = field(default_factory=lambda: deque(maxlen=100))
    uniqueAuthors: set[int] = field(default_factory=set)

    def reset(self, time: datetime):
        self.scaledMessageCount = 1.0
        self.chance = random.randint(*settings.requiredMessageRange)
        try:
            self.lock.release()
        except RuntimeError:  # lock is not acquired
            pass
        self.time = time

    async def increase(self, message: discord.Message) -> bool:
        # this is a deque, not a list
        # its property is that, once the max length is reached (100 for us),
        # the oldest element is removed, thus we only have the last 100 messages in memory
        self.messageCache.append(
            CachedMessage(content=message.content, author_id=message.author.id)
        )

        if self.lock.locked():
            return False

        async with self.lock:
            messageMultiplier = 1
            if message.content.lower() in [m.content.lower() for m in self.messageCache]:
                messageMultiplier /= 2
            if (
                message.guild.member_count < settings.minimumMembersRequired
                or message.guild.member_count > 1000
            ):  # type: ignore
                messageMultiplier /= 2
            if len(message.content) < 5:
                messageMultiplier /= 2
            if (datetime.now(timezone.utc) - message.author.created_at).days < 7:
                messageMultiplier /= 2
            if len(self.uniqueAuthors) < 4 or (
                len(list(filter(lambda x: x.author_id == message.author.id, self.messageCache)))
                / self.message_cache.maxlen  # type: ignore
                > 0.4
            ):
                messageMultiplier /= 2
            self.scaledMessageCount += messageMultiplier
            await asyncio.sleep(10)
        return True


@dataclass
class SpawnManager:
    cooldowns: dict[int, SpawnCooldown] = field(default_factory=dict)
    cache: dict[int, int] = field(default_factory=dict)

    async def handleMessage(self, message: discord.Message):
        guild = message.guild
        if not guild:
            return

        cooldown = self.cooldowns.get(guild.id, None)
        if not cooldown:
            cooldown = SpawnCooldown(message.created_at)
            self.cooldowns[guild.id] = cooldown

        deltaTime = (message.created_at - cooldown.time).total_seconds()
        # change how the threshold varies according to the member count, while nuking farm servers
        if not guild.member_count:
            return
        elif guild.member_count < 100:
            multiplier = 0.8
        elif guild.member_count < 1000:
            multiplier = 0.5
        else:
            multiplier = 0.2
        chance = cooldown.chance - multiplier * (deltaTime // 60)

        # manager cannot be increased more than once per 5 seconds
        if not await cooldown.increase(message):
            return

        # normal increase, need to reach goal
        if cooldown.scaledMessageCount <= chance:
            return

        # at this point, the goal is reached
        if deltaTime < settings.coolDownTime:
            # wait for at least 10 minutes before spawning
            return

        # spawn carfigure
        cooldown.reset(message.created_at)
        await self.spawnCarfigure(
            guild
        ) if guild.member_count > settings.minimumMembersRequired else log.warning(
            f"{guild.name} ({guild.id}) is trying to farm."
        )

    async def spawnCarfigure(self, guild: discord.Guild):
        channel = guild.get_channel(self.cache[guild.id])
        if not channel:
            log.warning(f"Lost channel {self.cache[guild.id]} for guild {guild.name}.")
            del self.cache[guild.id]
            return
        if not channel.permissions_for(guild.me).send_messages:
            log.warning(
                f"Lost permissions to send messages in {channel.name} for guild {guild.name}."
            )
            return

        car = await CarFigure.getRandom()
        await car.spawn(cast(discord.TextChannel, channel))
