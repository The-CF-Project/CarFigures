import re
import discord
from pathlib import Path

DONATION_POLICY_MAP = {
    1: "Accept all",
    2: "Approval Required",
    3: "Deny all",
}

PRIVATE_POLICY_MAP = {
    1: "Public Inventory",
    2: "Friends only Inventory",
    3: "Private Inventory",
}
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")


async def save_file(attachment: discord.Attachment) -> Path:
    path = Path(f"./static/uploads/{attachment.filename}")
    match = FILENAME_RE.match(attachment.filename)
    if not match:
        raise TypeError("The file you uploaded lacks an extension.")
    i = 1
    while path.exists():
        path = Path(f"./static/uploads/{match.group(1)}-{i}{match.group(2)}")
        i = i + 1
    await attachment.save(path)
    return path
