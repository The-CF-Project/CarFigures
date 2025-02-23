import logging
import time
from typing import TYPE_CHECKING
import asyncio

import discord
from discord.ext import commands
from tortoise import Tortoise
from tortoise.exceptions import DoesNotExist

from carfigures.packages.carfigures.carfigure import CarFigure
from carfigures.core.dev import pagify, send_interactive
from carfigures.core.models import Car, CarInstance, Player
from carfigures.settings import appearance

log = logging.getLogger("carfigures.core.commands")

if TYPE_CHECKING:
    from .bot import CarFiguresBot

class SimpleCheckView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.value = False

    async def interaction_check(self, interaction: discord.Interaction["CarFiguresBot"]) -> bool:
        return interaction.user == self.ctx.author

    @discord.ui.button(
        style=discord.ButtonStyle.success, emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}"
    )
    async def confirm_button(
        self, interaction: discord.Interaction["CarFiguresBot"], button: discord.ui.Button
    ):
        await interaction.response.edit_message(content="Starting upload...", view=None)
        self.value = True
        self.stop()

class Core(commands.Cog):
    """
    Core commands of CarFigures bot
    """

    def __init__(self, bot: "CarFiguresBot"):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """
        Ping!
        """
        await ctx.send("Pong.")

    @commands.command()
    @commands.is_owner()
    async def reloadtree(self, ctx: commands.Context):
        """
        Sync the application commands with Discord
        """
        await self.bot.tree.sync()
        await ctx.send("Application commands tree reloaded.")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, package: str):
        """
        Reload an extension
        """
        package = "carfigures.packages." + package
        try:
            try:
                await self.bot.reload_extension(package)
            except commands.ExtensionNotLoaded:
                await self.bot.load_extension(package)
        except commands.ExtensionNotFound:
            await ctx.send("Extension not found.")
        except Exception:
            await ctx.send("Failed to reload extension.")
            log.error(f"Failed to reload extension {package}", exc_info=True)
        else:
            await ctx.send("Extension reloaded.")

    @commands.command()
    @commands.is_owner()
    async def reloadcache(self, ctx: commands.Context):
        """
        Reload the cache of database models.

        This is needed each time the database is updated, otherwise changes won't reflect until
        next start.
        """
        await self.bot.reload_cache()
        await ctx.send("Database models cache have been reloaded.")

    @commands.command()
    @commands.is_owner()
    async def analyzedb(self, ctx: commands.Context):
        """
        Analyze the database. This refreshes the counts displayed by the `/info status` command.
        """
        connection = Tortoise.get_connection("default")
        t1 = time.time()
        await connection.execute_query("ANALYZE")
        t2 = time.time()
        await ctx.send(f"Analyzed database in {round((t2 - t1) * 1000)}ms.")

    @commands.command()
    @commands.is_owner()
    async def spawn(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel | None = None,
        amount: int = 1,
        *,
        car: str | None = None,
    ):
        """
        Spawn an entity.
        """
        for _ in range(amount):
            if not car:
                carfigure = await CarFigure.getRandom()
            else:
                try:
                    car_model = await Car.get(fullName__iexact=car.lower())
                except DoesNotExist:
                    await ctx.send(f"No such {appearance.collectible_singular} exists.")
                    return
                carfigure = CarFigure(car_model)
            await carfigure.spawn(channel or ctx.channel)

    @commands.command()
    @commands.is_owner()
    async def transfer(
        self,
        ctx: commands.Context,
        gifter: discord.User,
        receiver: discord.User,
    ):
        """
        Transfer someone's inventory to someone else.
        """
        try:
            oldPlayer = await Player.get(discord_id=gifter.id)
        except DoesNotExist:
            await ctx.send(f"Original player doesn't have any {appearance.collectible_plural}.")
            return
        
        newPlayer, _ = await Player.get_or_create(discord_id=receiver.id)

        await CarInstance.filter(player=oldPlayer).update(player=newPlayer)

        await ctx.send(
            f"The {appearance.garage_name} of {gifter.display_name} has been transferred to {receiver.display_name}."
        )

    @commands.command()
    @commands.is_owner()
    async def migrateemotes(self, ctx: commands.Context):
        cars = await Car.all()
        if not cars:
            await ctx.send(f"No {appearance.collectible_plural} found.")
            return

        application_emojis = set(x.name for x in await self.bot.fetch_application_emojis())

        not_found: set[Car] = set()
        already_uploaded: list[tuple[Car, discord.Emoji]] = []
        matching_name: list[tuple[Car, discord.Emoji]] = []
        to_upload: list[tuple[Car, discord.Emoji]] = []

        for car in cars:
            emote = self.bot.get_emoji(car.emoji)
            if not emote:
                not_found.add(car)
            elif emote.is_application_owned():
                already_uploaded.append((car, emote))
            elif emote.name in application_emojis:
                matching_name.append((car, emote))
            else:
                to_upload.append((car, emote))

        if len(already_uploaded) == len(cars):
            await ctx.send(
                f"All of your {appearance.collectible_plural} already use application emojis."
            )
            return
        if len(to_upload) + len(application_emojis) > 2000:
            await ctx.send(
                f"{len(to_upload)} emojis are available for migration, but this would "
                f"result in {len(to_upload) + len(application_emojis)} total application emojis, "
                "which is above the limit (2000)."
            )
            return

        text = ""
        if not_found:
            not_found_str = ", ".join(f"{x.fullName} ({x.emoji})" for x in not_found)
            text += f"### {len(not_found)} emojis not found\n{not_found_str}\n"
        if matching_name:
            matching_name_str = ", ".join(f"{x[1]} {x[0].fullName}" for x in matching_name)
            text += (
                f"### {len(matching_name)} emojis with conflicting names\n{matching_name_str}\n"
            )
        if already_uploaded:
            already_uploaded_str = ", ".join(f"{x[1]} {x[0].fullName}" for x in already_uploaded)
            text += (
                f"### {len(already_uploaded)} emojis are already "
                f"application emojis\n{already_uploaded_str}\n"
            )
        if to_upload:
            to_upload_str = ", ".join(f"{x[1]} {x[0].fullName}" for x in to_upload)
            text += f"## {len(to_upload)} emojis to migrate\n{to_upload_str}"
        else:
            text += "\n**No emojis can be migrated at this time.**"

        pages = pagify(text, delims=["###", "\n\n", "\n"], priority=True)
        await send_interactive(ctx, pages, block=None)
        if not to_upload:
            return

        view = SimpleCheckView(ctx)
        msg = await ctx.send("Do you want to proceed?", view=view)
        if await view.wait() or view.value is False:
            return

        uploaded = 0

        async def update_message_loop():
            nonlocal uploaded
            for i in range(5 * 12 * 10):  # timeout progress after 10 minutes
                print(f"Updating msg {uploaded}")
                await msg.edit(
                    content=f"Uploading emojis... ({uploaded}/{len(to_upload)})",
                    view=None,
                )
                await asyncio.sleep(5)

        task = self.bot.loop.create_task(update_message_loop())
        try:
            async with ctx.typing():
                for car, emote in to_upload:
                    new_emote = await self.bot.create_application_emoji(
                        name=emote.name, image=await emote.read()
                    )
                    car.emoji = new_emote.id
                    await car.save()
                    uploaded += 1
                    print(f"Uploaded {car}")
                    await asyncio.sleep(1)
                await self.bot.reload_cache()
            task.cancel()
            assert self.bot.application
            await ctx.send(
                f"Successfully migrated {len(to_upload)} emojis. You can check them [here]("
                f"<https://discord.com/developers/applications/{self.bot.application.id}/emojis>)."
            )
        finally:
            task.cancel()