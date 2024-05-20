from fastapi import Depends, Path
from fastapi_admin.app import app
from fastapi_admin.depends import get_resources
from fastapi_admin.template import templates
from starlette.requests import Request
from starlette.responses import Response
from tortoise.exceptions import DoesNotExist

from carfigures.core.models import Car, CarInstance, GuildConfig, Player, Event


@app.get("/")
async def admin(
    request: Request,
    resources=Depends(get_resources),
):
    return templates.TemplateResponse(
        "dashboard.html",
        context={
            "request": request,
            "resources": resources,
            "car_count": await Car.all().count(),
            "player_count": await Player.all().count(),
            "guild_count": await GuildConfig.all().count(),
            "event_count": await Event.all().count(),
            "resource_label": "Dashboard",
            "page_pre_title": "overview",
            "page_title": "Dashboard",
        },
    )


@app.get("/car/generate/{pk}")
async def generate_card(
    request: Request,
    pk: str = Path(...),
):
    car = await Car.get(pk=pk).prefetch_related("cartype", "country")
    temp_instance = CarInstance(car=car, player=await Player.first(), count=1)
    buffer = temp_instance.draw_card()
    return Response(content=buffer.read(), media_type="image/png")


@app.get("/event/generate/{pk}")
async def generate_event_card(
    request: Request,
    pk: str = Path(...),
):
    event = await Event.get(pk=pk)
    try:
        car = await Car.first().prefetch_related("cartype", "country")
    except DoesNotExist:
        return Response(
            content="At least one car must exist", status_code=422, media_type="text/html"
        )
    temp_instance = CarInstance(car=car, event=event, player=await Player.first(), count=1)
    buffer = temp_instance.draw_card()
    return Response(content=buffer.read(), media_type="image/png")