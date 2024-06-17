import os
from typing import List

from fastapi_admin.app import app
from fastapi_admin.enums import Method
from fastapi_admin.file_upload import FileUpload
from fastapi_admin.resources import Action, Field, Link, Model
from fastapi_admin.widgets import displays, filters, inputs
from starlette.requests import Request

from carfigures.core.models import (
    Car,
    CarInstance,
    BlacklistedGuild,
    BlacklistedUser,
    Country,
    GuildConfig,
    Player,
    CarType,
    Event,
    Admin,
)


@app.register
class Home(Link):
    label = "Home"
    icon = "fas fa-home"
    url = "/admin"


upload = FileUpload(uploads_dir=os.path.join(".", "static", "uploads"))


@app.register
class AdminResource(Model):
    label = "Admins"
    model = Admin
    icon = "fas fa-user"
    page_pre_title = "The List of:"
    page_title = "Admins"
    filters = [
        filters.Search(
            name="username",
            label="Name",
            search_mode="contains",
            placeholder="Search for username",
        ),
    ]
    fields = [
        "id",
        "username",
        Field(
            name="password",
            label="Password",
            display=displays.InputOnly(),
            input_=inputs.Password(),
        ),
        Field(
            name="avatar",
            label="Avatar",
            display=displays.Image(width="40"),
            input_=inputs.Image(null=True, upload=upload),
        ),
        "created_at",
    ]

    async def cell_attributes(self, request: Request, obj: dict, field: Field) -> dict:
        if field.name == "id":
            return {"class": "bg-danger text-white"}
        return await super().cell_attributes(request, obj, field)


@app.register
class EventResource(Model):
    label = "Events"
    model = Event
    icon = "fas fa-star"
    page_pre_title = "The List of:"
    page_title = "Events"
    filters = [
        filters.Search(
            name="name", label="Name", search_mode="icontains", placeholder="Search for events"
        )
    ]
    fields = [
        Field(
            name="name",
            label="Name",
            display=displays.InputOnly(),
            input_=inputs.Text(),
        ),
        Field(
            name="description",
            label="Description",
            display=displays.InputOnly(),
            input_=inputs.TextArea(),
        ),
        Field(
            name="banner",
            label="The Event Banner!",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=False)
        ),
        Field(
            name="catch_phrase",
            label="Catch Phrase!",
            display=displays.InputOnly(),
            input_=inputs.Text(),
        ),
        Field(
            name="start_date",
            label="Start date of the event",
            display=displays.DateDisplay(),
            input_=inputs.Date(help_text="Date when special entities will start spawning"),
        ),
        Field(
            name="end_date",
            label="End date of the event",
            display=displays.DateDisplay(),
            input_=inputs.Date(help_text="Date when special entities will stop spawning"),
        ),
        "rarity",
        Field(
            name="card",
            label="The Event Card",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
        "emoji",
        Field(
            name="tradeable",
            label="Tradeable?",
            input_=inputs.Switch(),
            display=displays.Boolean(),
        )
    ]

    async def get_actions(self, request: Request) -> List[Action]:
        actions = await super().get_actions(request)
        actions.append(
            Action(
                icon="fas fa-upload",
                label="Generate card",
                name="generate",
                method=Method.GET,
                ajax=False,
            )
        )
        return actions


@app.register
class CardResource(Model):
    label = "Cards"
    model = CarType
    icon = "fas fa-flag"
    page_pre_title = "The List of:"
    page_title = "Cards"
    fields = [
        "name",
        Field(
            name="image",
            label="Card Image (1428x2000)",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
    ]


@app.register
class IconResource(Model):
    label = "Icons"
    model = Country
    icon = "fas fa-coins"
    page_pre_title = "The List of:"
    page_title = "Icons"
    fields = [
        "name",
        Field(
            name="image",
            label="Icon Image (512x512)",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
    ]


@app.register
class EntityResource(Model):
    label = "Entities"
    model = Car
    page_size = 50
    icon = "fas fa-globe"
    page_pre_title = "The List of:"
    page_title = "Entities"
    filters = [
        filters.Search(
            name="full_name",
            label="Full Name",
            search_mode="icontains",
            placeholder="Search for cars",
        ),
        filters.ForeignKey(model=CarType, name="cartype", label="Card"),
        filters.ForeignKey(model=Country, name="country", label="Icon"),
        filters.Boolean(name="enabled", label="Enabled?"),
        filters.Boolean(name="tradeable", label="Tradeable?"),
    ]
    fields = [
        Field(
            name="full_name",
            label="Full Name",
            display=displays.Display(),
            input_=inputs.Text(),
        ),
        Field(
            name="short_name",
            label="Short Name",
            display = displays.Display(),
            input_ = inputs.Text(),
        ),
        "catch_names",
        "created_at",
        "cartype",
        "country",
        "weight",
        "horsepower",
        "rarity",
        Field(
            name="enabled",
            label="Ready to Spawn?",
            display=displays.Boolean(),
            input_=inputs.Switch()
        ),
        Field(
            name="tradeable",
            label="Tradeable?",
            display=displays.Boolean(),
            input_=inputs.Switch()
        ),
        Field(
            name="emoji_id",
            label="Emoji ID",
        ),
        Field(
            name="spawn_picture",
            label="Spawn Picture",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
        Field(
            name="collection_picture",
            label="Collection Picture",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
        Field(
            name="image_credits",
            label="Image credits",
        ),
        Field(
            name="car_suggester",
            label="The Entity Suggester",
        ),
        Field(
            name="capacity_name",
            label="Ability name",
        ),
        Field(
            name="capacity_description",
            label="Ability description",
        ),
    ]

    async def get_actions(self, request: Request) -> List[Action]:
        actions = await super().get_actions(request)
        actions.append(
            Action(
                icon="fas fa-upload",
                label="Generate card",
                name="generate",
                method=Method.GET,
                ajax=False,
            )
        )
        return actions


@app.register
class InstanceResource(Model):
    label = "Instances"
    model = CarInstance
    icon = "fas fa-atlas"
    page_pre_title = "The List of:"
    page_title = "Instances"
    filters = [
        filters.Search(
            name="id",
            label="Car Instance ID",
            placeholder="Search for car IDs",
        ),
        filters.ForeignKey(model=Car, name="car", label="Car"),
        filters.ForeignKey(model=Event, name="event", label="Event"),
        filters.Date(name="catch_date", label="Catch date"),
        filters.Boolean(name="limited", label="Limited Edition?"),
        filters.Boolean(name="favorite", label="Favorite?"),
        filters.Search(
            name="player__discord_id",
            label="User ID",
            placeholder="Search for Discord user ID",
        ),
        filters.Search(
            name="server_id",
            label="Server ID",
            placeholder="Search for Discord server ID",
        ),
        filters.Boolean(name="tradeable", label="Tradeable"),
    ]
    fields = [
        "id",
        "car",
        "player",
        "catch_date",
        "server_id",
        "limited",
        "event",
        "favorite",
        "weight_bonus",
        "horsepower_bonus",
        "tradeable",
    ]


@app.register
class PlayerResource(Model):
    label = "Players"
    model = Player
    icon = "fas fa-user"
    page_pre_title = "The List of:"
    page_title = "Players"
    filters = [
        filters.Search(
            name="discord_id",
            label="ID",
            search_mode="icontains",
            placeholder="Filter by ID",
        ),
    ]
    fields = [
        "discord_id",
        "cars",
        "donation_policy",
        "privacy_policy",
    ]


@app.register
class ServerResource(Model):
    label = "Server Settings"
    model = GuildConfig
    icon = "fas fa-cog"
    page_pre_title = "The List of:"
    page_title = "Server Setups"
    filters = [
        filters.Search(
            name="guild_id",
            label="ID",
            search_mode="icontains",
            placeholder="Filter by ID",
        ),
    ]
    fields = [
        Field(
            name="guild_id",
            label="The Server ID",
        ),
        Field(
            name="spawn_channel",
            label="The Channel Selected for Spawning",
        ),
        Field(
            name="spawn_ping",
            label="The Role Selected for Pinging"
        ),
        Field(
            name="enabled",
            label="Is Spawning Enabled?",
            display=displays.Boolean(),
            input_=inputs.Switch()
        )
    ]


@app.register
class BlacklistedUserResource(Model):
    label = "Blacklisted Users"
    model = BlacklistedUser
    icon = "fas fa-user-lock"
    page_pre_title = "The List of:"
    page_title = "Blacklisted User"
    filters = [
        filters.Search(
            name="discord_id",
            label="User ID",
            search_mode="icontains",
            placeholder="Filter by ID",
        ),
        filters.Search(
            name="reason",
            label="Reason",
            search_mode="search",
            placeholder="Search by reason",
        ),
    ]
    fields = [
        Field(
            name="discord_id",
            label="User ID",
        ),
        Field(
            name="reason",
            label="Reason Behind The Blacklist",
        )
    ]


@app.register
class BlacklistedGuildResource(Model):
    label = "Blacklisted Servers"
    model = BlacklistedGuild
    icon = "fas fa-lock"
    page_pre_title = "The List of:"
    page_title = "Blacklisted Servers"
    filters = [
        filters.Search(
            name="guild_id",
            label="Server ID",
            search_mode="icontains",
            placeholder="Filter by Guild ID",
        ),
        filters.Search(
            name="reason",
            label="Reason",
            search_mode="search",
            placeholder="Search by reason",
        ),
    ]
    fields = [
        Field(
            name="discord_id",
            label="Server ID",
        ),
        Field(
            name="reason",
            label="Reason Behind The Blacklist",
        )
    ]
