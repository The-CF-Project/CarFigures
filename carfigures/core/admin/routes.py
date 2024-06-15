from fastapi import Depends, Path
from fastapi_admin.app import app
from fastapi_admin.depends import get_current_admin, get_resources
from fastapi_admin.template import templates
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from tortoise.exceptions import DoesNotExist

from carfigures.core.models import (
    Admin,
    BlacklistedUser,
    BlacklistedGuild,
    Car,
    CarInstance,
    CarType,
    Country,
    GuildConfig,
    Player,
    Event,
)


@app.get("/")
async def admin(
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
            "admin_count": await Admin.all().count(),
            "event_count": await Event.all().count(),
            "card_count": await CarType.all().count(),
            "icon_count": await Country.all().count(),
            "entity_count": await Car.all().count(),
            "instance_count": await CarInstance.all().count(),
            "player_count": await Player.all().count(),
            "guild_count": await GuildConfig.all().count(),
            "blacklisteduser_count": await BlacklistedUser.all().count(),
            "blacklistedguild_count": await BlacklistedGuild.all().count(),
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
    car = await Car.get(pk=pk).prefetch_related("cartype", "country")
    temp_instance = CarInstance(car=car, player=await Player.first(), count=1)
    buffer = temp_instance.draw_card()
    return Response(content=buffer.read(), media_type="image/png")


@app.get("/event/generate/{pk}", dependencies=[Depends(get_current_admin)])
async def generate_event_card(
    request: Request,
    pk: str = Path(...),
):
    event = await Event.get(pk=pk)
    try:
        car = await Car.first().prefetch_related("cartype", "country")
    except DoesNotExist:
        return Response(
            content="At least one entity must exist", status_code=422, media_type="text/html"
        )
    temp_instance = CarInstance(car=car, event=event, player=await Player.first(), count=1)
    buffer = temp_instance.draw_card()
    return Response(content=buffer.read(), media_type="image/png")
