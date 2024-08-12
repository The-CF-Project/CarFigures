import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageOps

from carfigures.settings import appearance

if TYPE_CHECKING:
    from carfigures.core.models import CarInstance, Event

SOURCES_PATH = Path(os.path.dirname(os.path.abspath(__file__)), "./src")

CARD_WIDTH = 1500
CARD_HEIGHT = 2000

RECTANGLE_WIDTH = CARD_WIDTH - 40
RECTANGLE_HEIGHT = (CARD_HEIGHT // 5) * 2

card_title_font = ImageFont.truetype(
    str(SOURCES_PATH / "LemonMilkMedium-mLZYV.otf"), 140
)
card_capacity_name_font = ImageFont.truetype(
    str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), 110
)
card_capacity_description_font = ImageFont.truetype(
    str(SOURCES_PATH / "MomcakeThin-9Y6aZ.otf"), 75
)
card_stats_font = ImageFont.truetype(str(SOURCES_PATH / "NewAthleticM54-31vz.ttf"), 130)
card_credits_font = ImageFont.truetype(
    str(SOURCES_PATH / "BinomaTrialBold-1jPDj.ttf"), 40
)

CARD_CORNERS = ((0, 181), (1428, 948))
artwork_size = [b - a for a, b in zip(*CARD_CORNERS)]


def draw_card(car_instance: "CarInstance"):
    car = car_instance.carfigure
    car_weight = (255, 255, 255, 255)

    if exclusive_image := car_instance.exclusive_card:
        image = Image.open("." + exclusive_image)
    elif event_image := car_instance.event_card:
        image = Image.open("." + event_image)
    else:
        image = Image.open("." + car.cached_cartype.image)
    image = image.convert("RGBA")
    icon = (
        Image.open("." + car.cached_country.image).convert("RGBA")
        if car.cached_country
        else None
    )

    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 0),
        car.short_name or car.full_name,
        font=card_title_font,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
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
        f"Image Credits: {car.image_credits}\n{appearance.collectible_singular.title()} Suggester: {car.car_suggester}",
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

    image_width, image_height = image.size

    title_font_size = int(image_width * 0.03)
    description_font_size = int(image_width * 0.025)
    status_font_size = int(image_width * 0.02)
    credits_font_size = int(image_width * 0.015)

    event_title_font = ImageFont.truetype(
        str(SOURCES_PATH / "LemonMilkMedium-mLZYV.otf"), title_font_size
    )
    event_description_font = ImageFont.truetype(
        str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), description_font_size
    )
    event_status_font = ImageFont.truetype(
        str(SOURCES_PATH / "MomcakeBold-WyonA.otf"), status_font_size
    )
    event_credits_font = ImageFont.truetype(
        str(SOURCES_PATH / "BinomaTrialBold-1jPDj.ttf"), credits_font_size
    )

    # Calculate dynamic positions
    title_position = (int(image_width * 0.015), int(image_height * 0.01))
    description_position_y = int(image_height * 0.15)
    status_position = (int(image_width * 0.01), int(image_height * 0.95))
    credits_position = (int(image_width * 0.99), int(image_height * 0.95))

    # Draw title
    draw.text(
        title_position,
        event.name,
        font=event_title_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=2,
    )

    # Draw description
    for i, line in enumerate(textwrap.wrap(event.description, width=100)):
        draw.text(
            (title_position[0], description_position_y + i * description_font_size * 2),
            line,
            font=event_description_font,
            fill=(255, 255, 255, 255),
            stroke_fill=(0, 0, 0, 255),
            stroke_width=2,
        )

    # Draw event status
    draw.text(
        status_position,
        "Event Status:",
        font=event_status_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=1,
    )
    status_text = "Live!" if event.end_date > datetime.now(timezone.utc) else "Ended!"
    draw.text(
        (status_position[0] + int(image_width * 0.12), status_position[1]),
        status_text,
        font=event_status_font,
        fill=(0, 255, 0, 255) if status_text == "Live!" else (255, 0, 0, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=1,
    )

    # Draw credits
    draw.text(
        credits_position,
        "Created by Array_YE",
        font=event_credits_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=2,
        anchor="ra",
    )

    return image
