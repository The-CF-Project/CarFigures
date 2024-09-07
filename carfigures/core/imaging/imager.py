import textwrap
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from carfigures.core.models import CarInstance, Event

CARD_CORNERS = ((0, 181), (1428, 948))
artwork_size = [b - a for a, b in zip(*CARD_CORNERS)]


def draw_card(instance: "CarInstance"):
    car = instance.carfigure

    if instance.exclusivecard:
        image = Image.open("." + instance.exclusivecard.image)
        fonts = instance.exclusivecard.cached_fontspack
    elif instance.eventcard:
        image = Image.open("." + instance.eventcard.card)
        fonts = instance.eventcard.cached_fontspack
    else:
        image = Image.open("." + car.cached_cartype.image)
        fonts = car.cached_cartype.cached_fontspack
    image = image.convert("RGBA")
    icon = (
        Image.open("." + car.cached_country.image).convert("RGBA")
        if car.cached_country
        else None
    )

    titlefont = ImageFont.truetype(fonts.title, 140)
    capacitynfont = ImageFont.truetype(fonts.capacityn, 110)
    capacitydfont = ImageFont.truetype(fonts.capacityd, 75)
    statsfont = ImageFont.truetype(fonts.stats, 130)

    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 0),
        car.short_name or car.full_name,
        font=titlefont,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )
    for i, line in enumerate(textwrap.wrap(f"Ability: {car.capacity_name}", width=26)):
        draw.text(
            (100, 1050 + 100 * i),
            line,
            font=capacitynfont,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    for i, line in enumerate(textwrap.wrap(car.capacity_description, width=32)):
        draw.text(
            (60, 1300 + 60 * i),
            line,
            font=capacitydfont,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (320, 1660),
        str(instance.weight),
        font=statsfont,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
    )
    draw.text(
        (1120, 1660),
        str(instance.horsepower),
        font=statsfont,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra",
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
    fonts = event.fontspack

    # Dynamically Resize the text based on the banner size
    titlefont = ImageFont.truetype(fonts.title, int(image_width * 0.03))
    descriptionfont = ImageFont.truetype(fonts.capacityd, int(image_width * 0.025))
    statusfont = ImageFont.truetype(fonts.capacityn, int(image_width * 0.02))
    creditsfont = ImageFont.truetype(fonts.stats, int(image_width * 0.015))

    # Dynamically position the text
    titleposition = (int(image_width * 0.015), int(image_height * 0.01))
    descriptionposition = int(image_height * 0.15)
    statusposition = (int(image_width * 0.01), int(image_height * 0.95))
    creditsposition = (int(image_width * 0.99), int(image_height * 0.95))

    draw.text(
        titleposition,
        event.name,
        font=titlefont,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=2,
    )

    for i, line in enumerate(textwrap.wrap(event.description, width=100)):
        draw.text(
            (titleposition[0], descriptionposition + i * int(image_width * 0.025) * 2),
            line,
            font=descriptionfont,
            fill=(255, 255, 255, 255),
            stroke_fill=(0, 0, 0, 255),
            stroke_width=2,
        )

    draw.text(
        statusposition,
        "Event Status:",
        font=statusfont,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=1,
    )
    eventstatus = "Live!" if event.end_date > datetime.now(timezone.utc) else "Ended!"
    draw.text(
        (statusposition[0] + int(image_width * 0.12), statusposition[1]),
        eventstatus,
        font=statusfont,
        fill=(0, 255, 0, 255) if eventstatus == "Live!" else (255, 0, 0, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=1,
    )

    draw.text(
        creditsposition,
        "Created by Array_YE",
        font=creditsfont,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=2,
        anchor="ra",
    )

    return image
