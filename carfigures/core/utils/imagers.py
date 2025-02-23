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
    car_weight = (255, 255, 255, 255)

    if instance.exclusive_card:
        image = Image.open("." + instance.exclusive_card.image)
        fonts = instance.exclusive_card.cachedFontsPack
    elif instance.event_card:
        image = Image.open("." + instance.event_card.card)
        fonts = instance.event_card.cachedFontsPack
    else:
        image = Image.open("." + car.cached_album.image)
        fonts = car.cached_album.cachedFontsPack
    image = image.convert("RGBA")
    icon = Image.open("." + car.cached_country.image).convert("RGBA") if car.cached_country else None

    # Load fonts with dynamic sizes
    titleFont = ImageFont.truetype("." + fonts.title, 140)
    capacityNFont = ImageFont.truetype("." + fonts.capacityn, 110)
    capacityDFont = ImageFont.truetype("." + fonts.capacityd, 75)
    statsFont = ImageFont.truetype("." + fonts.stats, 130)
    creditsFont = ImageFont.truetype("." + fonts.credits, 40)

    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 0),
        car.shortName or car.fullName,
        font=titleFont,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )
    for i, line in enumerate(textwrap.wrap(f"Ability: {car.capacityName}", width=26)):
        draw.text(
            (100, 1050 + 100 * i),
            line,
            font=capacityNFont,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    for i, line in enumerate(textwrap.wrap(car.capacityDescription, width=32)):
        draw.text(
            (60, 1300 + 60 * i),
            line,
            font=capacityDFont,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (320, 1660),
        str(instance.weight),
        font=statsFont,
        fill=car_weight,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
    )
    draw.text(
        (1120, 1660),
        str(instance.horsepower),
        font=statsFont,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra",
    )
    draw.text(
        (30, 1870),
        f"Credits:\n{car.carCredits}\n",
        font=creditsFont,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )

    artwork = Image.open("." + car.collectionPicture).convert("RGBA")
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

    imageWidth, imageHeight = image.size
    fonts = event.cachedFontsPack

    # Dynamically Resize the text based on the banner size
    title_font = ImageFont.truetype(str("." + fonts.title), int(imageWidth * 0.03))
    description_font = ImageFont.truetype(str("." + fonts.capacityd), int(imageWidth * 0.025))
    status_font = ImageFont.truetype(str("." + fonts.capacityn), int(imageWidth * 0.02))
    credits_font = ImageFont.truetype(str("." + fonts.stats), int(imageWidth * 0.015))

    # Dynamically position the text
    title_position = (int(imageWidth * 0.015), int(imageHeight * 0.01))
    description_position = int(imageHeight * 0.15)
    status_position = (int(imageWidth * 0.01), int(imageHeight * 0.95))
    credits_position = (int(imageWidth * 0.99), int(imageHeight * 0.95))
    draw.text(
        title_position,
        event.name,
        font=title_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=2,
    )

    for i, line in enumerate(textwrap.wrap(event.description, width=100)):
        draw.text(
            (title_position[0], description_position + i * int(imageWidth * 0.025) * 2),
            line,
            font=description_font,
            fill=(255, 255, 255, 255),
            stroke_fill=(0, 0, 0, 255),
            stroke_width=2,
        )

    draw.text(
        status_position,
        "Event Status:",
        font=status_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=1,
    )
    eventstatus = "Live!" if event.endDate > datetime.now(timezone.utc) else "Ended!"
    draw.text(
        (status_position[0] + int(imageWidth * 0.12), status_position[1]),
        eventstatus,
        font=status_font,
        fill=(0, 255, 0, 255) if eventstatus == "Live!" else (255, 0, 0, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=1,
    )

    draw.text(
        credits_position,
        "Created by Array_YE",
        font=credits_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=2,
        anchor="ra",
    )

    return image
