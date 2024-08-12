import psutil
from typing import List

import discord
from discord import app_commands
from discord.ui import Select, View

from carfigures.core.models import Library
from carfigures.settings import settings


def machine_info():
    """
    Function to gather information about the machine's CPU, memory, and disk usage.
    """
    cpu_usage = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    memory_usage = round(memory.used / (1024**2), 2)
    memory_total = round(memory.total / (1024**2), 2)
    memory_percentage = memory.percent
    disk = psutil.disk_usage("/")
    disk_usage = round(disk.used / (1024**3), 2)
    disk_total = round(disk.total / (1024**3), 2)
    disk_percentage = disk.percent
    return (
        cpu_usage,
        memory_usage,
        memory_total,
        memory_percentage,
        disk_usage,
        disk_total,
        disk_percentage,
    )


def mention_app_command(app_command: app_commands.Command | app_commands.Group) -> str:
    """
    Generate a mention for the provided app command.
    """
    if "mention" in app_command.extras:
        return app_command.extras["mention"]
    else:
        if isinstance(app_command, app_commands.ContextMenu):
            return f"`{app_command.name}`"
        else:
            return f"`/{app_command.name}`"


class LibrarySelector(View):
    def __init__(self, topics: List[Library]):
        super().__init__()
        self.add_item(LibrarySource(topics))


class LibrarySource(Select):
    def __init__(self, library: List[Library]):
        options = [
            discord.SelectOption(
                label=topic.name,
                description=topic.description,
                value=str(topic.pk),
            )
            for topic in library
        ]
        super().__init__(
            placeholder="Choose a topic...", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        topic_id = int(self.values[0])
        selected_topic = await Library.get(id=topic_id)
        embed = discord.Embed(
            title=f"☳ {settings.bot_name} Documentations",
            description=f"∴ {selected_topic.description}",
            color=settings.default_embed_color,
        )
        embed.add_field(
            name=f"⋄ {selected_topic.name} | {selected_topic.description}",
            value=selected_topic.text,
        )
        await interaction.response.edit_message(embed=embed, view=self.view)
