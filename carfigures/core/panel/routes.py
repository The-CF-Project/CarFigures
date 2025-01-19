from fastapi import Depends, Path
from fastapi_admin.app import app
from fastapi_admin.depends import get_current_admin, get_resources
from fastapi_admin.template import templates
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from tortoise.exceptions import DoesNotExist

from carfigures.core import models


@app.get("/")
async def home(
    request: Request,
    resources=Depends(get_resources),
):
    if not request.state.admin:
        return RedirectResponse(app.admin_path + "/login")
    return templates.TemplateResponse(
        "dashboard.html",
        context={
            "request": request,
            "resources": resources,
            "admin_count": await models.Admin.all().count(),
            "event_count": await models.Event.all().count(),
            "card_count": await models.CarType.all().count(),
            "icon_count": await models.Country.all().count(),
            "entity_count": await models.Car.all().count(),
            "instance_count": await models.CarInstance.all().count(),
            "player_count": await models.Player.all().count(),
            "guild_count": await models.GuildConfig.all().count(),
            "blacklisteduser_count": await models.BlacklistedUser.all().count(),
            "blacklistedguild_count": await models.BlacklistedGuild.all().count(),
            "resource_label": "Dashboard",
            "page_pre_title": "overview",
            "page_title": "Dashboard",
        },
    )


@app.get("/car/generate/{pk}", dependencies=[Depends(get_current_admin)])
async def generate_card(
    request: Request,
    pk: str = Path(...),
):
    car = await models.Car.get(pk=pk).prefetch_related("cartype", "cartype__fontsPack", "country")
    tempInstance = await models.CarInstance(car=car, player=await models.Player.first(), count=1)
    buffer = tempInstance.drawCard()
    return Response(content=buffer.read(), media_type="image/png")


@app.get("/event/generate/{pk}", dependencies=[Depends(get_current_admin)])
async def generate_event_card(
    request: Request,
    pk: str = Path(...),
):
    event = await models.Event.get(pk=pk)
    try:
        car = await models.Car.first().prefetch_related("cartype", "cartype__fontsPack", "country")
    except DoesNotExist:
        return Response(
            content="At least one entity must exist", status_code=422, media_type="text/html"
        )
    instance = models.CarInstance(
        car=car, event=event, player=await models.Player.first(), count=1
    )
    buffer = instance.drawCard()
    return Response(content=buffer.read(), media_type="image/png")


@app.get("/exclusive/generate/{pk}", dependencies=[Depends(get_current_admin)])
async def generate_exclusive_card(
    request: Request,
    pk: str = Path(...),
):
    exclusive = await models.Exclusive.get(pk=pk)
    try:
        car = await models.Car.first().prefetch_related("cartype", "cartype__fontsPack", "country")
    except DoesNotExist:
        return Response(
            content="At least one entity must exist", status_code=422, media_type="text/html"
        )
    instance = models.CarInstance(
        car=car, exclusive=exclusive, player=await models.Player.first(), count=1
    )
    buffer = instance.drawCard()
    return Response(content=buffer.read(), media_type="image/png")
