from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Iterable, Tuple, Type
from enum import IntEnum

import discord
from discord.utils import format_dt
from tortoise import exceptions, fields, models, signals, timezone, validators
from tortoise.expressions import Q
from fastapi_admin.models import AbstractAdmin
from carfigures.core.utils import imagers
from carfigures.settings import appearance

if TYPE_CHECKING:
    from tortoise.backends.base.client import BaseDBAsyncClient


cars: dict[int, Car] = {}
cartypes: dict[int, CarType] = {}
countries: dict[int, Country] = {}
exclusives: dict[int, Exclusive] = {}
events: dict[int, Event] = {}
fontspacks: dict[int, FontsPack] = {}


async def lower_catch_names(
    model: Type[Car],
    instance: Car,
    created: bool,
    using_db: "BaseDBAsyncClient | None" = None,
    update_fields: Iterable[str] | None = None,
):
    if instance.catchNames:
        instance.catchNames = ";".join([x.strip() for x in instance.catchNames.split(";")]).lower()


class DiscordSnowflakeValidator(validators.Validator):
    def __call__(self, value: int):
        if not 17 <= len(str(value)) <= 19:
            raise exceptions.ValidationError("Discord IDs are between 17 and 19 characters long")


class Admin(AbstractAdmin):
    last_login = fields.DatetimeField(description="Last Login", default=datetime.now)
    avatar = fields.CharField(max_length=200, default="")
    intro = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pk}#{self.username}"


class GuildConfig(models.Model):
    guild_id = fields.BigIntField(
        description="Discord guild ID",
        unique=True,
        validators=[DiscordSnowflakeValidator()],
    )
    spawnChannel = fields.BigIntField(
        description="Discord channel ID where cars will spawn", null=True
    )
    spawnRole = fields.BigIntField(
        description="Discord role ID which the bot will ping when cars spawns",
        null=True,
    )
    enabled = fields.BooleanField(
        description="Whether the bot will spawn carfigures in this guild", default=True
    )


class FontsPack(models.Model):
    name = fields.CharField(max_length=64)
    title = fields.CharField(max_length=200)
    capacityn = fields.CharField(max_length=200)
    capacityd = fields.CharField(max_length=200)
    stats = fields.CharField(max_length=200)
    credits = fields.CharField(max_length=200)

    def __str__(self):
        return self.name


class CarType(models.Model):
    fontsPack_id: int

    name = fields.CharField(max_length=64)
    image = fields.CharField(max_length=200, description="1428x2000 PNG image")
    rebirthRequired = fields.IntField(default=0)
    fontsPack: fields.ForeignKeyRelation[FontsPack] = fields.ForeignKeyField(
        "models.FontsPack",
        description="The FontPack this exclusive uses",
        on_delete=fields.CASCADE,
    )

    @property
    def cachedFontsPack(self) -> FontsPack:
        return fontspacks.get(self.fontsPack_id, self.fontsPack)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = fields.CharField(max_length=64)
    image = fields.CharField(max_length=200, description="512x512 PNG image")

    def __str__(self):
        return self.name


class Exclusive(models.Model):
    fontsPack_id: int

    name = fields.CharField(max_length=64)
    image = fields.CharField(max_length=200, description="1428x2000 PNG image")
    fontsPack: fields.ForeignKeyRelation[FontsPack] = fields.ForeignKeyField(
        "models.FontsPack",
        description="The FontPack this exclusive uses",
        on_delete=fields.CASCADE,
    )
    rebirthRequired = fields.IntField(default=0)
    rarity = fields.FloatField(description="Value between 0 and 1.")
    emoji = fields.CharField(
        max_length=20,
        description="Either a unicode character or a discord emoji ID",
        null=True,
    )
    catchPhrase = fields.CharField(
        max_length=128,
        description="Sentence sent in bonus when someone catches a special card",
        null=True,
        default=None,
    )

    @property
    def cachedFontsPack(self) -> FontsPack:
        return fontspacks.get(self.fontsPack_id, self.fontsPack)

    def __str__(self):
        return self.name


class Event(models.Model):
    fontsPack_id: int

    name = fields.CharField(
        max_length=64,
        description="The name of the event",
    )
    description = fields.CharField(
        max_length=400,
        description="The description of the event",
    )
    catchPhrase = fields.CharField(
        max_length=128,
        description="Sentence sent in bonus when someone catches a special card",
        null=True,
        default=None,
    )
    fontsPack: fields.ForeignKeyRelation[FontsPack] = fields.ForeignKeyField(
        "models.FontsPack",
        description="The FontPack this exclusive uses",
        on_delete=fields.CASCADE,
    )
    banner = fields.CharField(max_length=200, description="1920x1080 PNG image", null=True)
    startDate = fields.DatetimeField()
    endDate = fields.DatetimeField()
    rarity = fields.FloatField(
        description="Value between 0 and 1, chances of using this special background."
    )
    card = fields.CharField(max_length=200, description="1428x2000 PNG image", null=True)
    emoji = fields.CharField(
        max_length=20,
        description="Either a unicode character or a discord emoji ID",
        null=True,
    )
    tradeable = fields.BooleanField(default=True)
    hidden = fields.BooleanField(default=False, description="Hides the event from player commands")

    @property
    def cachedFontsPack(self) -> FontsPack:
        return fontspacks.get(self.fontsPack_id, self.fontsPack)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["-startDate"]

    def draw_banner(self) -> BytesIO:
        image = imagers.drawBanner(self)
        buffer = BytesIO()
        image.save(buffer, format="png")
        buffer.seek(0)
        image.close()
        return buffer

    async def prepare_for_message(
        self, interaction: discord.Interaction
    ) -> Tuple[str, discord.File]:
        # message content
        content = f"**Event Info:**\n**Event:** {self.name}\n**Description:** {self.description}"
        # draw image
        with ThreadPoolExecutor() as pool:
            buffer = await interaction.client.loop.run_in_executor(pool, self.draw_banner)

        return content, discord.File(buffer, "banner.png")


class Car(models.Model):
    cartype_id: int
    country_id: int

    fullName = fields.CharField(max_length=48, unique=True)
    shortName = fields.CharField(max_length=20, null=True, default=None)
    catchNames = fields.TextField(
        null=True,
        default=None,
        description="Additional possible names for catching this car, separated by semicolons",
    )
    cartype: fields.ForeignKeyRelation[CarType] = fields.ForeignKeyField(
        "models.CarType",
        description="The CarType of this Car",
        on_delete=fields.CASCADE,
    )
    country: fields.ForeignKeyRelation[Country] | None = fields.ForeignKeyField(
        "models.Country",
        description="The Country of this car",
        on_delete=fields.SET_NULL,
        null=True,
    )
    weight = fields.IntField(description="Car weight stat")
    horsepower = fields.IntField(description="Car horsepower stat")
    rarity = fields.FloatField(description="Rarity of this car")
    enabled = fields.BooleanField(default=True)
    tradeable = fields.BooleanField(default=True)
    emoji = fields.BigIntField(
        description="Emoji ID for this car", validators=[DiscordSnowflakeValidator()]
    )
    spawnPicture = fields.CharField(
        max_length=200,
        description="Image used when a new car spawns in the wild",
    )
    collectionPicture = fields.CharField(
        max_length=200,
        description="Image used when displaying cars",
    )
    optionalCard = fields.CharField(max_length=200, description="1428x2000 PNG image", null=True)
    fontsMetaData = fields.JSONField(description="Effect of this capacity", default={})
    carCredits = fields.CharField(
        max_length=64,
        description="Author of the collection artwork",
    )
    capacityName = fields.CharField(
        max_length=64,
        description="Name of the carfigure's capacity",
    )
    capacityDescription = fields.CharField(
        max_length=256,
        description="Description of the carfigure's capacity",
    )
    capacity_logic = fields.JSONField(description="Effect of this capacity", default={})
    createdAt = fields.DatetimeField(auto_now_add=True, null=True)

    instances: fields.BackwardFKRelation[CarInstance]

    def __str__(self) -> str:
        return self.fullName

    @property
    def cachedCartype(self) -> CarType:
        return cartypes.get(self.cartype_id, self.cartype)

    @property
    def cachedCountry(self) -> Country | None:
        return countries.get(self.country_id, self.country)


Car.register_listener(signals.Signals.pre_save, lower_catch_names)


class CarInstance(models.Model):
    car_id: int
    event_id: int
    exclusive_id: int
    trade_player_id: int

    car: fields.ForeignKeyRelation[Car] = fields.ForeignKeyField("models.Car")
    player: fields.ForeignKeyRelation[Player] = fields.ForeignKeyRelation(
        "models.Player",
        related_name="cars",
    )  # type: ignore
    catchDate = fields.DatetimeField(auto_now_add=True)
    spawnedTime = fields.DatetimeField(null=True)
    server = fields.BigIntField(
        description="Discord server ID where this car was caught", null=True
    )
    exclusive: fields.ForeignKeyRelation[Exclusive] | None = fields.ForeignKeyField(
        "models.Exclusive",
        null=True,
        default=None,
        on_delete=fields.SET_NULL,
    )
    event: fields.ForeignKeyRelation[Event] | None = fields.ForeignKeyField(
        "models.Event",
        null=True,
        default=None,
        on_delete=fields.SET_NULL,
    )
    weightBonus = fields.IntField(default=0)
    horsepowerBonus = fields.IntField(default=0)
    trade_player: fields.ForeignKeyRelation[Player] | None = fields.ForeignKeyField(
        "models.Player",
        null=True,
        default=None,
        on_delete=fields.SET_NULL,
    )
    favorite = fields.BooleanField(default=False)
    tradeable = fields.BooleanField(default=True)
    locked: fields.Field[datetime] = fields.DatetimeField(
        description="If the instance was locked for a trade and when",
        null=True,
        default=None,
    )
    extra_data = fields.JSONField(default={})

    class Meta:
        unique_together = ("player", "id")

    @property
    def isTradeable(self) -> bool:
        return (
            self.tradeable
            and self.carfigure.tradeable
            and getattr(self.eventCard, "tradeable", True)
        )

    @property
    def horsepower(self) -> int:
        bonus = int(self.carfigure.horsepower * self.horsepowerBonus * 0.01)
        return self.carfigure.horsepower + bonus

    @property
    def weight(self) -> int:
        bonus = int(self.carfigure.weight * self.weightBonus * 0.01)
        return self.carfigure.weight + bonus

    @property
    def carfigure(self) -> Car:
        return cars.get(self.car_id, self.car)

    @property
    def exclusiveCard(self) -> Exclusive | None:
        return exclusives.get(self.exclusive_id, self.exclusive)

    @property
    def eventCard(self) -> Event | None:
        return events.get(self.event_id, self.event)

    def __str__(self) -> str:
        return self.toString()

    def toString(self, bot: discord.Client | None = None, is_trade: bool = False) -> str:
        emotes = ""
        if bot and self.pk in bot.locked_cars and not is_trade:  # type: ignore
            emotes += "🔒"
        if self.favorite:
            emotes += "❤️"
        if self.exclusiveCard:
            emotes += self.exclusiveEmoji(bot)
        if emotes:
            emotes += " "
        if self.eventCard:
            emotes += self.eventEmoji(bot)
        full_name = (
            self.carfigure.fullName if isinstance(self.carfigure, Car) else f"<Car {self.car_id}>"
        )
        return f"{emotes}#{self.pk:0X} {full_name}"

    def exclusiveEmoji(self, bot: discord.Client | None, use_custom_emoji: bool = True) -> str:
        if self.exclusiveCard:
            if not use_custom_emoji:
                return "⚡ "
            exclusive_emoji = ""
            try:
                emoji_id = int(self.exclusiveCard.emoji)
                exclusive_emoji = bot.get_emoji(emoji_id) if bot else "⚡ "
            except ValueError:
                exclusive_emoji = self.exclusiveCard.emoji
            except TypeError:
                return ""
            if exclusive_emoji:
                return f"{exclusive_emoji} "
        return ""

    def eventEmoji(self, bot: discord.Client | None, use_custom_emoji: bool = True) -> str:
        if self.eventCard:
            if not use_custom_emoji:
                return "⚡ "
            event_emoji = ""
            try:
                emoji_id = int(self.eventCard.emoji)
                event_emoji = bot.get_emoji(emoji_id) if bot else "⚡ "
            except ValueError:
                event_emoji = self.eventCard.emoji
            except TypeError:
                return ""
            if event_emoji:
                return f"{event_emoji} "
        return ""

    def description(
        self,
        *,
        short: bool = False,
        include_emoji: bool = False,
        bot: discord.Client | None = None,
        is_trade: bool = False,
    ) -> str:
        text = self.toString(bot, is_trade=is_trade)
        if not short:
            text += f" {appearance.hp}:{self.horsepowerBonus:+d}% {appearance.kg}:{self.weightBonus:+d}%"
        if include_emoji:
            if not bot:
                raise TypeError(
                    "You need to provide the bot argument when using with include_emoji=True"
                )
            if isinstance(self.carfigure, Car):
                emoji = bot.get_emoji(self.carfigure.emoji)
                if emoji:
                    text = f"{emoji} {text}"
        return text

    def drawCard(self) -> BytesIO:
        image = imagers.drawCard(self)
        buffer = BytesIO()
        image.save(buffer, format="png")
        buffer.seek(0)
        image.close()
        return buffer

    async def prepareForMessage(
        self, interaction: discord.Interaction
    ) -> Tuple[str, discord.File]:
        # message content
        trade_content = ""
        await self.fetch_related("trade_player", "event")
        if self.trade_player:
            originalPlayer = None
            # we want to avoid calling fetch_player if possible
            # (heavily rate-limited call)
            if interaction.guild:
                try:
                    originalPlayer = await interaction.guild.fetch_member(
                        int(self.trade_player.discord_id)
                    )
                except discord.NotFound:
                    pass
            elif originalPlayer is None:  # try again if not found in guild
                try:
                    originalPlayer = await interaction.client.fetch_user(
                        int(self.trade_player.discord_id)
                    )
                except discord.NotFound:
                    pass

            originalPlayerName = (
                originalPlayer.name
                if originalPlayer
                else f"player with ID {self.trade_player.discord_id}"
            )
            trade_content = f"Obtained by trade with {originalPlayerName}.\n"
        content = (
            f"ID: `#{self.pk:0X}`\n"
            f"Caught on {format_dt(self.catchDate)} ({format_dt(self.catchDate, style='R')}).\n"
            f"{trade_content}\n"
            f"{appearance.hp}: {self.horsepower} ({self.horsepowerBonus:+d}%)\n"
            f"{appearance.kg}: {self.weight} ({self.weightBonus:+d}%)"
        )

        # draw image
        with ThreadPoolExecutor() as pool:
            buffer = await interaction.client.loop.run_in_executor(pool, self.drawCard)

        return content, discord.File(buffer, "card.png")

    async def lockForTrade(self):
        self.locked = timezone.now()
        await self.save(update_fields=("locked",))

    async def unlock(self):
        self.locked = None  # type: ignore
        await self.save(update_fields=("locked",))

    async def isLocked(self):
        await self.refresh_from_db(fields=("locked",))
        self.locked
        return self.locked is not None and (self.locked + timedelta(minutes=30)) > timezone.now()


class DonationPolicy(IntEnum):
    alwaysAccept = 1
    requestApproval = 2
    alwaysDeny = 3
    friendsOnly = 4


class PrivacyPolicy(IntEnum):
    openInv = 1
    closedInv = 2
    friendsOnly = 3


class Player(models.Model):
    discord_id = fields.BigIntField(
        description="Discord user ID",
        unique=True,
        validators=[DiscordSnowflakeValidator()],
    )
    donationPolicy = fields.IntEnumField(
        DonationPolicy,
        description="How you want to handle donations",
        default=DonationPolicy.alwaysAccept,
    )
    privacyPolicy = fields.IntEnumField(
        PrivacyPolicy,
        description="How you want to handle privacy",
        default=PrivacyPolicy.openInv,
    )
    bolts = fields.IntField(default=0)
    friends: fields.BackwardFKRelation[Friendship]
    cars: fields.BackwardFKRelation[CarInstance]
    rebirths = fields.IntField(default=0)

    def __str__(self) -> str:
        return str(self.discord_id)

    async def is_friend(self, other_player: "Player") -> bool:
        return await Friendship.filter(
            (Q(player1=self) & Q(player2=other_player))
            | (Q(player1=other_player) & Q(player2=self))
        ).exists()


class Friendship(models.Model):
    id: int
    friender: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player", related_name="player1", source_field="friender"
    )
    friended: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player", related_name="player2", source_field="friended"
    )
    bestie = fields.BooleanField(default=False)
    since = fields.DatetimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.pk)


class FriendshipRequest(models.Model):
    id: int
    sender: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player", related_name="requestSender", source_field="sender"
    )
    receiver: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player", related_name="requestReceiver", source_field="receiver"
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.pk)


class BlacklistedUser(models.Model):
    discord_id = fields.BigIntField(
        description="Discord user ID",
        unique=True,
        validators=[DiscordSnowflakeValidator()],
    )
    reason = fields.TextField(null=True, default=None)
    date = fields.DatetimeField(null=True, default=None, auto_now_add=True)

    def __str__(self) -> str:
        return str(self.discord_id)


class BlacklistedGuild(models.Model):
    discord_id = fields.BigIntField(
        description="Discord Guild ID",
        unique=True,
        validators=[DiscordSnowflakeValidator()],
    )
    reason = fields.TextField(null=True, default=None)
    date = fields.DatetimeField(null=True, default=None, auto_now_add=True)

    def __str__(self) -> str:
        return str(self.discord_id)


class Trade(models.Model):
    id: int
    player1: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player",
        related_name="trades",
    )
    player2: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player",
        related_name="trades2",
    )
    date = fields.DatetimeField(auto_now_add=True)
    tradeobjects: fields.ReverseRelation[TradeObject]

    def __str__(self) -> str:
        return str(self.pk)


class TradeObject(models.Model):
    trade_id: int

    trade: fields.ForeignKeyRelation[Trade] = fields.ForeignKeyField(
        "models.Trade",
        related_name="tradeobjects",
    )
    carinstance: fields.ForeignKeyRelation[CarInstance] = fields.ForeignKeyField(
        "models.CarInstance",
        related_name="tradeobjects",
    )
    player: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player",
        related_name="tradeobjects",
    )

    def __str__(self) -> str:
        return str(self.pk)
