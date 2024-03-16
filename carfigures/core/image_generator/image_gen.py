import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from carfigures.core.models import CarInstance


SOURCES_PATH = Path(os.path.dirname(os.path.abspath(__file__)), "./src")
WIDTH = 1500
HEIGHT = 2000

RECTANGLE_WIDTH = WIDTH - 40
RECTANGLE_HEIGHT = (HEIGHT // 5) * 2

CORNERS = ((0, 181), (1427, 948))
artwork_size = [b - a for a, b in zip(*CORNERS)]

title_font = ImageFont.truetype(str(SOURCES_PATH / "LemonMilkMedium-mLZYV.otf"), 140)
capacity_name_font = ImageFont.truetype(str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), 110)
capacity_description_font = ImageFont.truetype(str(SOURCES_PATH / "MomcakeThin-9Y6aZ.otf"), 75)
stats_font = ImageFont.truetype(str(SOURCES_PATH / "NewAthleticM54-31vz.ttf"), 130)
credits_font = ImageFont.truetype(str(SOURCES_PATH / "BinomaTrialBold-1jPDj.ttf"), 40)


def draw_card(car_instance: "CarInstance"):
    car = car_instance.carfigure
    car_weight = (255, 255, 255, 255)

    if car_instance.limited:
        image = Image.open(str(SOURCES_PATH / "limited.png"))
        car_weight = (255, 255, 255, 255)
    elif special_image := car_instance.special_card:
        image = Image.open("." + special_image)
    else:
        image = Image.open("." + car.cached_cartype.background)
    icon = Image.open("." + car.cached_country.icon) if car.cached_country else None

    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 0),
        car.short_name or car.full_name,
        font=title_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255)
        )
    for i, line in enumerate(textwrap.wrap(f"Ability: {car.capacity_name}", width=26)):
        draw.text(
            (100, 1050 + 100 * i),
            line,
            font=capacity_name_font,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    for i, line in enumerate(textwrap.wrap(car.capacity_description, width=32)):
        draw.text(
            (60, 1300 + 60 * i),
            line,
            font=capacity_description_font,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (320, 1660),
        str(car_instance.weight),
        font=stats_font,
        fill=car_weight,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
    )
    draw.text(
        (1120, 1660),
        str(car_instance.horsepower),
        font=stats_font,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra",
    )
    draw.text(
        (30, 1870),
        # Modifying the line below is breaking the license as you are removing credits
        # If you don't want to receive a DMCA, just don't
        "Created by El Laggron - Modified By Array_YE\n" f"Image Credits: {car.credits}",
        font=credits_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )

    artwork = Image.open("." + car.collection_picture)
    image.paste(ImageOps.fit(artwork, artwork_size), CORNERS[0])  # type: ignore

    if icon:
        icon = ImageOps.fit(icon, (181, 181))
        image.paste(icon, (1247, 0), mask=icon)
        icon.close()
    artwork.close()

    return image