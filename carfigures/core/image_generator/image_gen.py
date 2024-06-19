import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from carfigures.core.models import CarInstance, Event

SOURCES_PATH = Path(os.path.dirname(os.path.abspath(__file__)), "./src")

CARD_WIDTH = 1500
CARD_HEIGHT = 2000

RECTANGLE_WIDTH = CARD_WIDTH - 40
RECTANGLE_HEIGHT = (CARD_HEIGHT // 5) * 2

card_title_font = ImageFont.truetype(str(SOURCES_PATH / "LemonMilkMedium-mLZYV.otf"), 140)
card_capacity_name_font = ImageFont.truetype(str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), 110)
card_capacity_description_font = ImageFont.truetype(str(SOURCES_PATH / "MomcakeThin-9Y6aZ.otf"), 75)
card_stats_font = ImageFont.truetype(str(SOURCES_PATH / "NewAthleticM54-31vz.ttf"), 130)
card_credits_font = ImageFont.truetype(str(SOURCES_PATH / "BinomaTrialBold-1jPDj.ttf"), 40)

CARD_CORNERS = ((0, 181), (1428, 948))
artwork_size = [b - a for a, b in zip(*CARD_CORNERS)]


EVENT_WIDTH = 1920
Event_HEIGHT = 1080

EVENT_CORNERS = ((0, 0), (1920, 1080))

event_title_font = ImageFont.truetype(str(SOURCES_PATH / "LemonMilkMedium-mLZYV.otf"), 80)
event_description_font = ImageFont.truetype(str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), 60)
event_status_font = ImageFont.truetype(str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), 50)
event_credits_font = ImageFont.truetype(str(SOURCES_PATH / "BinomaTrialBold-1jPDj.ttf"), 30)


def draw_card(car_instance: "CarInstance"):
    car = car_instance.carfigure
    car_weight = (255, 255, 255, 255)

    if car_instance.limited:
        image = Image.open(str(SOURCES_PATH / "limited.png"))
        car_weight = (255, 255, 255, 255)
    elif event_image := car_instance.event_card:
        image = Image.open("." + event_image)
    else:
        image = Image.open("." + car.cached_cartype.image)
    image = image.convert("RGBA")
    icon = (
        Image.open("." + car.cached_country.image).convert("RGBA") if car.cached_country else None
    )

    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 0),
        car.short_name or car.full_name,
        font=card_title_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255)
        )
    for i, line in enumerate(textwrap.wrap(f"Ability: {car.capacity_name}", width=26)):
        draw.text(
            (100, 1050 + 100 * i),
            line,
            font=card_capacity_name_font,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    for i, line in enumerate(textwrap.wrap(car.capacity_description, width=32)):
        draw.text(
            (60, 1300 + 60 * i),
            line,
            font=card_capacity_description_font,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (320, 1660),
        str(car_instance.weight),
        font=card_stats_font,
        fill=car_weight,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
    )
    draw.text(
        (1120, 1660),
        str(car_instance.horsepower),
        font=card_stats_font,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra",
    )
    draw.text(
        (30, 1870),
        f"Image Credits: {car.image_credits}\nCar Suggester:{car.car_suggester}",
        font=card_credits_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )

    artwork = Image.open("." + car.collection_picture).convert("RGBA")
    image.paste(ImageOps.fit(artwork, artwork_size), CARD_CORNERS[0])  # type: ignore

    if icon:
        icon = ImageOps.fit(icon, (181, 181))
        image.paste(icon, (1247, 0), mask=icon)
        icon.close()
    artwork.close()

    return image


def draw_banner(event: "Event"):

    image = Image.open("." + event.banner)
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.text(
        (35, 5),
        event.name,
        font=event_title_font,
        fill=(0, 0, 0, 255)
        )
    draw.text(
        (30, 0),
        event.name,
        font=event_title_font,
        fill=(255, 255, 255, 255)
        )
    for i, line in enumerate(textwrap.wrap(event.description, width=100)):
        draw.text(
            (60, 100 + 60 * i),
            line,
            font=event_description_font,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (30, 1015),
        f"Event Status:",
        font=event_status_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )
    if event.end_date > datetime.now(timezone.utc):
        draw.text(
            (320, 1015),
            "Live!",
            font=event_status_font,
            fill=(0, 255, 0, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    else:
        draw.text(
            (320, 1015),
            "Ended!",
            font=event_status_font,
            fill=(255, 0, 0, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (1900, 1035),
        "Created by Array_YE",
        font=event_credits_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra",
    )
    image.paste(image, (EVENT_CORNERS[0]))
    return image
