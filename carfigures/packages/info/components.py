import psutil
import discord
from discord import app_commands
from discord.ui import Select, View
from carfigures.configs import settings
from carfigures.docs import DocsManager


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
    def __init__(self, docs_manager: DocsManager, language: str):
        super().__init__()
        self.docs_manager = docs_manager
        self.language = language
        self.add_item(LibrarySource(docs_manager, language))


class LibrarySource(Select):
    def __init__(self, docs_manager: DocsManager, language: str):
        self.docs_manager = docs_manager
        self.language = language
        options = [
            discord.SelectOption(
                label=info["name"][language],
                description=info["description"][language],
                value=topic,
            )
            for topic, info in docs_manager.topics.items()
        ]
        super().__init__(
            placeholder="Choose a topic...", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_topic = self.values[0]
        topic_info = self.docs_manager.topics[selected_topic]
        content = self.docs_manager.get_topic_content(selected_topic, self.language)

        embed = discord.Embed(
            title=f"☳ {settings.bot_name} Documentations",
            description=f"∴ {topic_info['description'][self.language]}",
            color=settings.default_embed_color,
        )

        embed.add_field(
            name=f"⋄ {topic_info['name'][self.language]}",
            value=content[:1024]
            if content
            else "Content not available in this language.",
        )
        await interaction.response.edit_message(embed=embed, view=self.view)
