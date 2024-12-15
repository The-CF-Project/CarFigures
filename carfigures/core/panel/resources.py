import os
from typing import List

from fastapi_admin.app import app
from fastapi_admin.enums import Method
from fastapi_admin.file_upload import FileUpload
from fastapi_admin.resources import Action, Field, Link, Model
from fastapi_admin.widgets import displays, filters, inputs
from starlette.requests import Request

from carfigures.core import models


@app.register
class Home(Link):
    label = "Home"
    icon = "fas fa-home"
    url = "/admin"


upload = FileUpload(uploads_dir=os.path.join(".", "static", "uploads"))


@app.register
class AdminResource(Model):
    label = "Admins"
    model = models.Admin
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
class FontsPackResource(Model):
    label = "FontsPacks"
    model = models.FontsPack
    icon = "fas fa-bag"
    page_pre_title = "The List of:"
    page_title = "Fonts Packs"
    fields = [
        Field(name="name", label="The name of the pack"),
        Field(
            name="title",
            label="The Font of the Title",
            display=displays.Display(),
            input_=inputs.File(upload=upload, null=False),
        ),
        Field(
            name="capacityn",
            label="The Font of the Capacity Name",
            display=displays.Display(),
            input_=inputs.File(upload=upload, null=False),
        ),
        Field(
            name="capacityd",
            label="The Font of the Capacity Description",
            display=displays.Display(),
            input_=inputs.File(upload=upload, null=False),
        ),
        Field(
            name="stats",
            label="The Font of the Stats",
            display=displays.Display(),
            input_=inputs.File(upload=upload, null=False),
        ),
        Field(
            name="credits",
            label="The Font of The Credits",
            display=displays.Display(),
            input_=inputs.File(upload=upload, null=False),
        ),
    ]


@app.register
class EventResource(Model):
    label = "Events"
    model = models.Event
    icon = "fas fa-star"
    page_pre_title = "The List of:"
    page_title = "Events"
    filters = [
        filters.Search(
            name="name",
            label="Name",
            search_mode="icontains",
            placeholder="Search for events",
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
        "fontsPack",
        Field(
            name="banner",
            label="The Event Banner!",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=False),
        ),
        Field(
            name="catchPhrase",
            label="Catch Phrase!",
            display=displays.InputOnly(),
            input_=inputs.Text(),
        ),
        Field(
            name="startDate",
            label="Start date of the event",
            display=displays.DateDisplay(),
            input_=inputs.Date(help_text="Date when special entities will start spawning"),
        ),
        Field(
            name="endDate",
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
class ExclusiveResource(Model):
    label = "Exclusives"
    model = models.Exclusive
    icon = "fas fa-star"
    page_pre_title = "The List of:"
    page_title = "Exclusives"
    fields = [
        "name",
        Field(
            name="image",
            label="Card Image (1428x2000)",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
        "fontsPack",
        "rarity",
        Field(
            name="rebirthRequired",
            label="The Amount of Rebirths Required to be able to Obtain this card",
            display=displays.Display(),
            input_=inputs.Number(),
        ),
        "emoji",
        Field(
            name="catchPhrase",
            label="The Catch Phrase!",
            display=displays.InputOnly(),
            input_=inputs.Text(),
        ),
    ]


@app.register
class CardResource(Model):
    label = "Cards"
    model = models.CarType
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
        "fontsPack",
    ]


@app.register
class IconResource(Model):
    label = "Icons"
    model = models.Country
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
    model = models.Car
    page_size = 50
    icon = "fas fa-globe"
    page_pre_title = "The List of:"
    page_title = "Entities"
    filters = [
        filters.Search(
            name="fullName",
            label="Full Name",
            search_mode="icontains",
            placeholder="Search for cars",
        ),
        filters.ForeignKey(model=models.CarType, name="cartype", label="Card"),
        filters.ForeignKey(model=models.Country, name="country", label="Icon"),
        filters.Boolean(name="enabled", label="Enabled?"),
        filters.Boolean(name="tradeable", label="Tradeable?"),
    ]
    fields = [
        Field(
            name="fullName",
            label="Full Name",
            display=displays.Display(),
            input_=inputs.Text(),
        ),
        Field(
            name="shortName",
            label="Short Name",
            display=displays.Display(),
            input_=inputs.Text(),
        ),
        "catchNames",
        "createdAt",
        "cartype",
        "country",
        "weight",
        "horsepower",
        "rarity",
        Field(
            name="enabled",
            label="Ready to Spawn?",
            display=displays.Boolean(),
            input_=inputs.Switch(),
        ),
        Field(
            name="tradeable",
            label="Tradeable?",
            display=displays.Boolean(),
            input_=inputs.Switch(),
        ),
        Field(
            name="emoji",
            label="Emoji ID",
        ),
        Field(
            name="spawnPicture",
            label="Spawn Picture",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
        Field(
            name="collectionPicture",
            label="Collection Picture",
            display=displays.Image(width="40"),
            input_=inputs.Image(upload=upload, null=True),
        ),
        Field(
            name="carCredits",
            label="The Credits (artwork, suggester, etc)",
        ),
        Field(
            name="capacityName",
            label="The Ability name of this Entity!",
        ),
        Field(
            name="capacityDescription",
            label="The Description of this ability!",
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
    model = models.CarInstance
    icon = "fas fa-atlas"
    page_pre_title = "The List of:"
    page_title = "Instances"
    filters = [
        filters.Search(
            name="id",
            label="Car Instance ID",
            placeholder="Search for car IDs",
        ),
        filters.ForeignKey(model=models.Car, name="car", label="Car"),
        filters.ForeignKey(model=models.Event, name="event", label="Event"),
        filters.ForeignKey(model=models.Exclusive, name="exclusive", label="Exclusive"),
        filters.Date(name="catchDate", label="Catch date"),
        filters.Boolean(name="favorite", label="Favorite?"),
        filters.Search(
            name="player__discord_id",
            label="User ID",
            placeholder="Search for Discord user ID",
        ),
        filters.Search(
            name="server",
            label="Server ID",
            placeholder="Search for Discord server ID",
        ),
        filters.Boolean(name="tradeable", label="Tradeable"),
    ]
    fields = [
        "id",
        "car",
        "player",
        "catchDate",
        "server",
        "exclusive",
        "event",
        "favorite",
        "weightBonus",
        "horsepowerBonus",
        Field(
            name="tradeable",
            label="Tradeable?",
            display=displays.Boolean(),
            input_=inputs.Switch(),
        ),
    ]


@app.register
class PlayerResource(Model):
    label = "Players"
    model = models.Player
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
        "rebirths",
        "donationPolicy",
        "privacyPolicy",
    ]


@app.register
class ServerResource(Model):
    label = "Server Settings"
    model = models.GuildConfig
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
            name="spawnChannel",
            label="The Channel Selected for Spawning",
        ),
        Field(name="spawnRole", label="The Role Selected for Pinging"),
        Field(
            name="enabled",
            label="Is Spawning Enabled?",
            display=displays.Boolean(),
            input_=inputs.Switch(),
        ),
    ]


@app.register
class BlacklistedUserResource(Model):
    label = "Blacklisted Users"
    model = models.BlacklistedUser
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
        ),
    ]


@app.register
class BlacklistedGuildResource(Model):
    label = "Blacklisted Servers"
    model = models.BlacklistedGuild
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
        ),
    ]
