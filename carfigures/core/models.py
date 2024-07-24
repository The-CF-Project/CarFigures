from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from enum import IntEnum
from io import BytesIO
from typing import TYPE_CHECKING, Iterable, Tuple, Type

import discord
from discord.utils import format_dt
from fastapi_admin.models import AbstractAdmin
from tortoise import exceptions, fields, models, signals, timezone, validators
from tortoise.fields.data import IntField

from carfigures.core.image_generator.image_gen import draw_card, draw_banner
from carfigures.settings import settings

if TYPE_CHECKING:
    from tortoise.backends.base.client import BaseDBAsyncClient


cars: dict[int, Car] = {}
cartypes: dict[int, CarType] = {}
countries: dict[int, Country] = {}
exclusives: dict[int, Exclusive] = {}
events: dict[int, Event] = {}


async def lower_catch_names(
    model: Type[Car],
    instance: Car,
    created: bool,
    using_db: "BaseDBAsyncClient | None" = None,
    update_fields: Iterable[str] | None = None,
):
    if instance.catch_names:
        instance.catch_names = ";".join(
            [x.strip() for x in instance.catch_names.split(";")]
        ).lower()


class DiscordSnowflakeValidator(validators.Validator):
    def __call__(self, value: int):
        if not 17 <= len(str(value)) <= 19:
            raise exceptions.ValidationError(
                "Discord IDs are between 17 and 19 characters long"
            )


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
    spawn_channel = fields.BigIntField(
        description="Discord channel ID where cars will spawn", null=True
    )
    spawn_ping = fields.BigIntField(
        description="Discord role ID which the bot will ping when cars spawns",
        null=True,
    )
    enabled = fields.BooleanField(
        description="Whether the bot will spawn carfigures in this guild", default=True
    )


class CarType(models.Model):
    name = fields.CharField(max_length=64)
    image = fields.CharField(max_length=200, description="1428x2000 PNG image")

    def __str__(self):
        return self.name


class Country(models.Model):
    name = fields.CharField(max_length=64)
    image = fields.CharField(max_length=200, description="512x512 PNG image")

    def __str__(self):
        return self.name


class Exclusive(models.Model):
    name = fields.CharField(max_length=64)
    image = fields.CharField(max_length=200, description="1428x2000 PNG image")
    rebirth_required = fields.IntField(default=0)
    rarity = fields.FloatField(description="Value between 0 and 1.")
    emoji = fields.CharField(
        max_length=20,
        description="Either a unicode character or a discord emoji ID",
        null=True,
    )
    catch_phrase = fields.CharField(
        max_length=128,
        description="Sentence sent in bonus when someone catches a special card",
        null=True,
        default=None,
    )

    def __str__(self):
        return self.name


class Event(models.Model):
    name = fields.CharField(
        max_length=64,
        description="The name of the event",
    )
    description = fields.CharField(
        max_length=400,
        description="The description of the event",
    )
    catch_phrase = fields.CharField(
        max_length=128,
        description="Sentence sent in bonus when someone catches a special card",
        null=True,
        default=None,
    )
    banner = fields.CharField(
        max_length=200, description="1920x1080 PNG image", null=True
    )
    start_date = fields.DatetimeField()
    end_date = fields.DatetimeField()
    rarity = fields.FloatField(
        description="Value between 0 and 1, chances of using this special background."
    )
    card = fields.CharField(
        max_length=200, description="1428x2000 PNG image", null=True
    )
    emoji = fields.CharField(
        max_length=20,
        description="Either a unicode character or a discord emoji ID",
        null=True,
    )
    tradeable = fields.BooleanField(default=True)
    hidden = fields.BooleanField(
        default=False, description="Hides the event from player commands"
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["-start_date"]

    def draw_banner(self) -> BytesIO:
        image = draw_banner(self)
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
            buffer = await interaction.client.loop.run_in_executor(
                pool, self.draw_banner
            )

        return content, discord.File(buffer, "banner.png")


class Car(models.Model):
    cartype_id: int
    country_id: int

    full_name = fields.CharField(max_length=48, unique=True)
    short_name = fields.CharField(max_length=20, null=True, default=None)
    catch_names = fields.TextField(
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
    emoji_id = fields.BigIntField(
        description="Emoji ID for this car", validators=[DiscordSnowflakeValidator()]
    )
    spawn_picture = fields.CharField(
        max_length=200, description="Image used when a new car spawns in the wild"
    )
    collection_picture = fields.CharField(
        max_length=200, description="Image used when displaying cars"
    )
    car_suggester = fields.CharField(max_length=64, description="Suggester of the car")
    image_credits = fields.CharField(
        max_length=64, description="Author of the collection artwork"
    )
    capacity_name = fields.CharField(
        max_length=64, description="Name of the carfigure's capacity"
    )
    capacity_description = fields.CharField(
        max_length=256, description="Description of the carfigure's capacity"
    )
    capacity_logic = fields.JSONField(description="Effect of this capacity", default={})
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    instances: fields.BackwardFKRelation[CarInstance]

    def __str__(self) -> str:
        return self.full_name

    @property
    def cached_cartype(self) -> CarType:
        return cartypes.get(self.cartype_id, self.cartype)

    @property
    def cached_country(self) -> Country | None:
        return countries.get(self.country_id, self.country)


Car.register_listener(signals.Signals.pre_save, lower_catch_names)


class CarInstance(models.Model):
    car_id: int
    event_id: int
    exclusive_id: int
    trade_player_id: int

    car: fields.ForeignKeyRelation[Car] = fields.ForeignKeyField("models.Car")
    player: fields.ForeignKeyRelation[Player] = fields.ForeignKeyRelation(
        "models.Player", related_name="cars"
    )  # type: ignore
    catch_date = fields.DatetimeField(auto_now_add=True)
    spawned_time = fields.DatetimeField(null=True)
    server_id = fields.BigIntField(
        description="Discord server ID where this car was caught", null=True
    )
    limited = fields.BooleanField(default=False)
    exclusive: fields.ForeignKeyRelation[Exclusive] | None = fields.ForeignKeyField(
        "models.Exclusive", null=True, default=None, on_delete=fields.SET_NULL
    )
    event: fields.ForeignKeyRelation[Event] | None = fields.ForeignKeyField(
        "models.Event", null=True, default=None, on_delete=fields.SET_NULL
    )
    weight_bonus = fields.IntField(default=0)
    horsepower_bonus = fields.IntField(default=0)
    trade_player: fields.ForeignKeyRelation[Player] | None = fields.ForeignKeyField(
        "models.Player", null=True, default=None, on_delete=fields.SET_NULL
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
    def is_tradeable(self) -> bool:
        return (
            self.tradeable
            and self.carfigure.tradeable
            and getattr(self.eventcard, "tradeable", True)
        )

    @property
    def horsepower(self) -> int:
        bonus = int(self.carfigure.horsepower * self.horsepower_bonus * 0.01)
        return self.carfigure.horsepower + bonus

    @property
    def weight(self) -> int:
        bonus = int(self.carfigure.weight * self.weight_bonus * 0.01)
        return self.carfigure.weight + bonus

    @property
    def exclusive_card(self) -> str | None:
        if self.exclusivecard:
            return self.exclusivecard.card or self.carfigure.collection_picture

    @property
    def event_card(self) -> str | None:
        if self.eventcard:
            return self.eventcard.card or self.carfigure.collection_picture

    @property
    def carfigure(self) -> Car:
        return cars.get(self.car_id, self.car)
    
    @property
    def exclusivecard(self) -> Exclusive | None:
        return exclusives.get(self.exclusive_id, self.exclusive)

    @property
    def eventcard(self) -> Event | None:
        return events.get(self.event_id, self.event)

    def __str__(self) -> str:
        return self.to_string()

    def to_string(
        self, bot: discord.Client | None = None, is_trade: bool = False
    ) -> str:
        emotes = ""
        if bot and self.pk in bot.locked_cars and not is_trade:  # type: ignore
            emotes += "🔒"
        if self.favorite:
            emotes += "❤️"
        if self.limited:
            emotes += self.exclusive_emoji(bot)
        if emotes:
            emotes += " "
        if self.eventcard:
            emotes += self.event_emoji(bot)
        full_name = (
            self.carfigure.full_name
            if isinstance(self.carfigure, Car)
            else f"<Car {self.car_id}>"
        )
        return f"{emotes}#{self.pk:0X} {full_name}"

    def exclusive_emoji(
        self, bot: discord.Client | None, use_custom_emoji: bool = True
    ) -> str:
        if self.exclusivecard:
            if not use_custom_emoji:
                return "⚡ "
            exclusive_emoji = ""
            try:
                emoji_id = int(self.exclusivecard.emoji)
                exclusive_emoji = bot.get_emoji(emoji_id) if bot else "⚡ "
            except ValueError:
                exclusive_emoji = self.exclusivecard.emoji
            except TypeError:
                return ""
            if exclusive_emoji:
                return f"{exclusive_emoji} "
        return ""

    def event_emoji(
        self, bot: discord.Client | None, use_custom_emoji: bool = True
    ) -> str:
        if self.eventcard:
            if not use_custom_emoji:
                return "⚡ "
            event_emoji = ""
            try:
                emoji_id = int(self.eventcard.emoji)
                event_emoji = bot.get_emoji(emoji_id) if bot else "⚡ "
            except ValueError:
                event_emoji = self.eventcard.emoji
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
        text = self.to_string(bot, is_trade=is_trade)
        if not short:
            text += f" HP:{self.horsepower_bonus:+d}% KG:{self.weight_bonus:+d}%"
        if include_emoji:
            if not bot:
                raise TypeError(
                    "You need to provide the bot argument when using with include_emoji=True"
                )
            if isinstance(self.carfigure, Car):
                emoji = bot.get_emoji(self.carfigure.emoji_id)
                if emoji:
                    text = f"{emoji} {text}"
        return text

    def draw_card(self) -> BytesIO:
        image = draw_card(self)
        buffer = BytesIO()
        image.save(buffer, format="png")
        buffer.seek(0)
        image.close()
        return buffer

    async def prepare_for_message(
        self, interaction: discord.Interaction
    ) -> Tuple[str, discord.File]:
        # message content
        trade_content = ""
        await self.fetch_related("trade_player", "event")
        if self.trade_player:
            original_player = None
            # we want to avoid calling fetch_player if possible
            # (heavily rate-limited call)
            if interaction.guild:
                try:
                    original_player = await interaction.guild.fetch_member(
                        int(self.trade_player.discord_id)
                    )
                except discord.NotFound:
                    pass
            elif original_player is None:  # try again if not found in guild
                try:
                    original_player = await interaction.client.fetch_user(
                        int(self.trade_player.discord_id)
                    )
                except discord.NotFound:
                    pass

            original_player_name = (
                original_player.name
                if original_player
                else f"player with ID {self.trade_player.discord_id}"
            )
            trade_content = f"Obtained by trade with {original_player_name}.\n"
        content = (
            f"ID: `#{self.pk:0X}`\n"
            f"Caught on {format_dt(self.catch_date)} ({format_dt(self.catch_date, style='R')}).\n"
            f"{trade_content}\n"
            f"{settings.hp_replacement}: {self.horsepower} ({self.horsepower_bonus:+d}%)\n"
            f"{settings.kg_replacement}: {self.weight} ({self.weight_bonus:+d}%)"
        )

        # draw image
        with ThreadPoolExecutor() as pool:
            buffer = await interaction.client.loop.run_in_executor(pool, self.draw_card)

        return content, discord.File(buffer, "card.png")

    async def lock_for_trade(self):
        self.locked = timezone.now()
        await self.save(update_fields=("locked",))

    async def unlock(self):
        self.locked = None  # type: ignore
        await self.save(update_fields=("locked",))

    async def is_locked(self):
        await self.refresh_from_db(fields=("locked",))
        self.locked
        return (
            self.locked is not None
            and (self.locked + timedelta(minutes=30)) > timezone.now()
        )


class DonationPolicy(IntEnum):
    ALWAYS_ACCEPT = 1
    REQUEST_APPROVAL = 2
    ALWAYS_DENY = 3


class PrivacyPolicy(IntEnum):
    ALLOW = 1
    DENY = 2
    SAME_SERVER = 3


class Player(models.Model):
    discord_id = fields.BigIntField(
        description="Discord user ID",
        unique=True,
        validators=[DiscordSnowflakeValidator()],
    )
    donation_policy = fields.IntEnumField(
        DonationPolicy,
        description="How you want to handle donations",
        default=DonationPolicy.ALWAYS_ACCEPT,
    )
    privacy_policy = fields.IntEnumField(
        PrivacyPolicy,
        description="How you want to handle privacy",
        default=PrivacyPolicy.ALLOW,
    )
    cars: fields.BackwardFKRelation[CarInstance]
    rebirths = IntField(default=0)

    def __str__(self) -> str:
        return str(self.discord_id)


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
        "models.Player", related_name="trades"
    )
    player2: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player", related_name="trades2"
    )
    date = fields.DatetimeField(auto_now_add=True)
    tradeobjects: fields.ReverseRelation[TradeObject]

    def __str__(self) -> str:
        return str(self.pk)


class TradeObject(models.Model):
    trade_id: int

    trade: fields.ForeignKeyRelation[Trade] = fields.ForeignKeyField(
        "models.Trade", related_name="tradeobjects"
    )
    carinstance: fields.ForeignKeyRelation[CarInstance] = fields.ForeignKeyField(
        "models.CarInstance", related_name="tradeobjects"
    )
    player: fields.ForeignKeyRelation[Player] = fields.ForeignKeyField(
        "models.Player", related_name="tradeobjects"
    )

    def __str__(self) -> str:
        return str(self.pk)
