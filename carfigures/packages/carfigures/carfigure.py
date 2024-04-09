import logging
import random
import string

import discord

from carfigures.core.models import Car, cars
from carfigures.packages.carfigures.components import CatchView
from carfigures.settings import settings

log = logging.getLogger("carfigures.packages.carfigures")


class CarFigure:
    def __init__(self, model: Car):
        self.name = model.full_name
        self.model = model
        self.message: discord.Message = discord.utils.MISSING
        self.caught = False

    @classmethod
    async def get_random(cls):
        carfigures = list(filter(lambda m: m.enabled, cars.values()))
        if not carfigures:
            raise RuntimeError("No car to spawn")
        rarities = [x.rarity for x in carfigures]
        cb = random.choices(population=carfigures, weights=rarities, k=1)[0]
        return cls(cb)

    async def spawn(self, channel: discord.TextChannel):
        def generate_random_name():
            source = string.ascii_uppercase + string.ascii_lowercase + string.ascii_letters
            return "".join(random.choices(source, k=15))

        extension = self.model.spawn_picture.split(".")[-1]
        file_location = "." + self.model.spawn_picture
        file_name = f"nt_{generate_random_name()}.{extension}"
        try:
            permissions = channel.permissions_for(channel.guild.me)
            if permissions.attach_files and permissions.send_messages:
                self.message = await channel.send(
                    f"A wild {settings.collectible_name} appeared!",
                    view=CatchView(self),
                    file=discord.File(file_location, filename=file_name),
                )
            else:
                log.error("Missing permission to spawn car in channel %s.", channel)
        except discord.Forbidden:
            log.error(f"Missing permission to spawn car in channel {channel}.")
        except discord.HTTPException:
            log.error("Failed to spawn car", exc_info=True)
