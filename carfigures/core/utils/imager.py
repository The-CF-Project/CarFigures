import textwrap
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from carfigures.core.models import CarInstance, Event

CARD_CORNERS = ((0, 181), (1428, 948))
artwork_size = [b - a for a, b in zip(*CARD_CORNERS)]


def drawCard(instance: "CarInstance"):
    car = instance.carfigure
    car_weight = (255, 255, 255, 255)

    if instance.exclusiveCard:
        image = Image.open("." + instance.exclusiveCard.image)
        fonts = instance.exclusiveCard.cachedFontsPack
    elif instance.eventCard:
        image = Image.open("." + instance.eventCard.card)
        fonts = instance.eventCard.cachedFontsPack
    else:
        image = Image.open("." + car.cachedCartype.image)
        fonts = car.cachedCartype.cachedFontsPack
    image = image.convert("RGBA")
    icon = Image.open("." + car.cachedCountry.image).convert("RGBA") if car.cachedCountry else None

    titlefont = ImageFont.truetype(fonts.titleFont, 140)
    capacitynfont = ImageFont.truetype(fonts.capacityNFont, 110)
    capacitydfont = ImageFont.truetype(fonts.capacityDFont, 75)
    statsfont = ImageFont.truetype(fonts.statsFont, 130)

    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 0),
        car.shortName or car.fullName,
        font=titlefont,
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )
    for i, line in enumerate(textwrap.wrap(f"Ability: {car.capacityName}", width=26)):
        draw.text(
            (100, 1050 + 100 * i),
            line,
            font=capacitynfont,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
    for i, line in enumerate(textwrap.wrap(car.capacityDescription, width=32)):
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
        fill=car_weight,
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
    draw.text(
        (30, 1870),
        f"Image Credits: {car.carCredits}\n",
        font=statsfont,
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


def drawBanner(event: "Event"):
    image = Image.open("." + event.banner)
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)

    imageWidth, imageHeight = image.size
    fonts = event.fontsPack

    # Dynamically Resize the text based on the banner size
    titlefont = ImageFont.truetype(fonts.titleFont, int(imageWidth * 0.03))
    descriptionfont = ImageFont.truetype(fonts.capacityDFont, int(imageWidth * 0.025))
    statusfont = ImageFont.truetype(fonts.capacityNFont, int(imageWidth * 0.02))
    creditsfont = ImageFont.truetype(fonts.statsFont, int(imageWidth * 0.015))

    # Dynamically position the text
    titleposition = (int(imageWidth * 0.015), int(imageHeight * 0.01))
    descriptionposition = int(imageHeight * 0.15)
    statusposition = (int(imageWidth * 0.01), int(imageHeight * 0.95))
    creditsposition = (int(imageWidth * 0.99), int(imageHeight * 0.95))
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
            (titleposition[0], descriptionposition + i * int(imageWidth * 0.025) * 2),
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
    eventstatus = "Live!" if event.endDate > datetime.now(timezone.utc) else "Ended!"
    draw.text(
        (statusposition[0] + int(imageWidth * 0.12), statusposition[1]),
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
