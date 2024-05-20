import logging
import time
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING, Generic, Iterable, TypeVar

import discord
from discord import app_commands
from discord.interactions import Interaction
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q, RawSQL
from tortoise.models import Model
from tortoise.timezone import now as tortoise_now

from carfigures.core.models import (
    Car,
    CarInstance,
    Country,
    CarType,
    Event,
    cars,
    countries,
    cartypes,
)
from carfigures.settings import settings

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

log = logging.getLogger("carfigures.core.utils.transformers")
T = TypeVar("T", bound=Model)

__all__ = (
    "CarTransform",
    "CarInstanceTransform",
    "EventTransform",
    "CarTypeTransform",
    "CountryTransform",
)


class TradeCommandType(Enum):
    """
    If a command is using `CarInstanceTransformer` for trading purposes, it should define this
    enum to filter out values.
    """

    PICK = 0
    REMOVE = 1


class ValidationError(Exception):
    """
    Raised when an autocomplete result is forbidden and should raise a user message.
    """

    def __init__(self, message: str):
        self.message = message


class ModelTransformer(app_commands.Transformer, Generic[T]):
    """
    Base abstract class for autocompletion from on Tortoise models

    Attributes
    ----------
    name: str
        Name to qualify the object being listed
    model: T
        The Tortoise model associated to the class derivation
    """

    name: str
    model: T

    def key(self, model: T) -> str:
        """
        Return a string used for searching while sending autocompletion suggestions.
        """
        raise NotImplementedError()

    async def validate(self, interaction: discord.Interaction["CarFiguresBot"], item: T):
        """
        A function to validate the fetched item before calling back the command.

        Raises
        ------
        ValidationError
            Raised if the item does not pass validation with the message to be displayed
        """
        pass

    async def get_from_pk(self, value: int) -> T:
        """
        Return a Tortoise model instance from a primary key.

        Raises
        ------
        KeyError | tortoise.exceptions.DoesNotExist
            Entry does not exist
        """
        return await self.model.get(pk=value)

    async def get_options(
        self, interaction: discord.Interaction["CarFiguresBot"], value: str
    ) -> list[app_commands.Choice[int]]:
        """
        Generate the list of options for autocompletion
        """
        raise NotImplementedError()

    async def autocomplete(
        self, interaction: Interaction["CarFiguresBot"], value: str
    ) -> list[app_commands.Choice[int]]:
        t1 = time.time()
        choices: list[app_commands.Choice[int]] = []
        for option in await self.get_options(interaction, value):
            choices.append(option)
        t2 = time.time()
        log.debug(
            f"{self.name.title()} autocompletion took "
            f"{round((t2-t1)*1000)}ms, {len(choices)} results"
        )
        return choices

    async def transform(self, interaction: Interaction["CarFiguresBot"], value: str) -> T | None:
        if not value:
            await interaction.response.send_message(
                "You need to use the autocomplete function for the economy selection."
            )
            return None
        try:
            instance = await self.get_from_pk(int(value))
            await self.validate(interaction, instance)
        except (DoesNotExist, KeyError, ValueError):
            await interaction.response.send_message(
                f"The {self.name} could not be found. Make sure to use the autocomplete "
                "function on this command.",
                ephemeral=True,
            )
            return None
        except ValidationError as e:
            await interaction.response.send_message(e.message, ephemeral=True)
            return None
        else:
            return instance


class CarInstanceTransformer(ModelTransformer[CarInstance]):
    name = settings.collectible_name.lower()
    model = CarInstance  # type: ignore

    async def get_from_pk(self, value: int) -> CarInstance:
        return await self.model.get(pk=value).prefetch_related("player")

    async def validate(self, interaction: discord.Interaction["CarFiguresBot"], item: CarInstance):
        # checking if the car does belong to user, and a custom ID wasn't forced
        if item.player.discord_id != interaction.user.id:
            raise ValidationError(f"That {settings.collectible_name} doesn't belong to you.")

    async def get_options(
        self, interaction: Interaction["CarFiguresBot"], value: str
    ) -> list[app_commands.Choice[int]]:
        cars_queryset = CarInstance.filter(player__discord_id=interaction.user.id)

        if (event := getattr(interaction.namespace, "event", None)) and event.isdigit():
            cars_queryset = cars_queryset.filter(event_id=int(event))
        if (limited := getattr(interaction.namespace, "limited", None)) and limited is not None:
            cars_queryset = cars_queryset.filter(limited=limited)

        if interaction.command and (trade_type := interaction.command.extras.get("trade", None)):
            if trade_type == TradeCommandType.PICK:
                cars_queryset = cars_queryset.filter(
                    Q(
                        Q(locked__isnull=True)
                        | Q(locked__lt=tortoise_now() + timedelta(minutes=30))
                    )
                )
            else:
                cars_queryset = cars_queryset.filter(
                    locked__isnull=False, locked__gt=tortoise_now() - timedelta(minutes=30)
                )
        cars_queryset = (
            cars_queryset.select_related("car")
            .annotate(
                searchable=RawSQL(
                    "to_hex(carinstance.car_id) || carinstance__car.full_name || "
                    "carinstance__car.catch_names"
                )
            )
            .filter(searchable__icontains=value)
            .limit(25)
        )

        choices: list[app_commands.Choice] = [
            app_commands.Choice(name=x.description(bot=interaction.client), value=str(x.pk))
            for x in await cars_queryset
        ]
        return choices


class TTLModelTransformer(ModelTransformer[T]):
    """
    Base class for simple Tortoise model autocompletion with TTL cache.

    This is used in most cases except for CarInstance which requires special handling depending
    on the interaction passed.

    Attributes
    ----------
    ttl: float
        Delay in seconds for `items` to live until refreshed with `load_items`, defaults to 300
    """

    ttl: float = 300

    def __init__(self):
        self.items: dict[int, T] = {}
        self.search_map: dict[T, str] = {}
        self.last_refresh: float = 0
        log.debug(f"Inited transformer for {self.name}")

    async def load_items(self) -> Iterable[T]:
        """
        Query values to fill `items` with.
        """
        return await self.model.all()

    async def maybe_refresh(self):
        t = time.time()
        if t - self.last_refresh > self.ttl:
            self.items = {x.pk: x for x in await self.load_items()}
            self.last_refresh = t
            self.search_map = {x: self.key(x).lower() for x in self.items.values()}

    async def get_options(
        self, interaction: Interaction["CarFiguresBot"], value: str
    ) -> list[app_commands.Choice[str]]:
        await self.maybe_refresh()

        i = 0
        choices: list[app_commands.Choice] = []
        for item in self.items.values():
            if value.lower() in self.search_map[item]:
                choices.append(app_commands.Choice(name=self.key(item), value=str(item.pk)))
                i += 1
                if i == 25:
                    break
        return choices


class CarTransformer(TTLModelTransformer[Car]):
    name = settings.collectible_name.lower()
    model = Car()

    def key(self, model: Car) -> str:
        return model.full_name

    async def load_items(self) -> Iterable[Car]:
        return cars.values()


class CarEnabledTransformer(CarTransformer):
    async def load_items(self) -> Iterable[Car]:
        return {k: v for k, v in cars.items() if v.enabled}.values()


class EventTransformer(TTLModelTransformer[Event]):
    name = "event"
    model = Event()

    def key(self, model: Event) -> str:
        return model.name


class EventEnabledTransformer(EventTransformer):
    async def load_items(self) -> Iterable[Event]:
        return await Event.filter(hidden=False).all()


class CarTypeTransformer(TTLModelTransformer[CarType]):
    name = "cartype"
    model = CarType()

    def key(self, model: CarType) -> str:
        return model.name

    async def load_items(self) -> Iterable[CarType]:
        return cartypes.values()


class CountryTransformer(TTLModelTransformer[Country]):
    name = "country"
    model = Country()

    def key(self, model: Country) -> str:
        return model.name

    async def load_items(self) -> Iterable[Country]:
        return countries.values()


CarTransform = app_commands.Transform[Car, CarTransformer]
CarInstanceTransform = app_commands.Transform[CarInstance, CarInstanceTransformer]
EventTransform = app_commands.Transform[Event, EventTransformer]
CarTypeTransform = app_commands.Transform[CarType, CarTypeTransformer]
CountryTransform = app_commands.Transform[Country, CountryTransformer]
EventEnabledTransform = app_commands.Transform[Event, EventEnabledTransformer]
CarEnabledTransform = app_commands.Transform[Car, CarEnabledTransformer]
