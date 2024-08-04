from typing import TYPE_CHECKING, Iterable

import discord

from carfigures.core.models import Trade as BattleModel
from carfigures.core.utils import menus
from carfigures.core.utils.paginator import Pages
from carfigures.packages.battle.battle_user import BattlingUser

if TYPE_CHECKING:
    from carfigures.core.bot import CarFiguresBot

def _get_prefix_emote(battler: BattlingUser) -> str:
    if battler.cancelled:
        return "\N{NO ENTRY SIGN}"
    elif battler.accepted:
        return "\N{WHITE HEAVY CHECK MARK}"
    elif battler.locked:
        return "\N{LOCK}"
    else:
        return ""


def _build_list_of_strings(
    battler: BattlingUser, bot: "CarFiguresBot", short: bool = False
) -> list[str]:
    # this builds a list of strings always lower than 1024 characters
    # while not cutting in the middle of a line
    proposal: list[str] = [""]
    i = 0

    for carfigure in battler.proposal:
        cb_text = countryball.description(short=short, include_emoji=True, bot=bot, is_trade=True)
        if battler.locked:
            text = f"- *{cb_text}*\n"
        else:
            text = f"- {cb_text}\n"
        if battler.cancelled:
            text = f"~~{text}~~"

        if len(text) + len(proposal[i]) > 950:
            # move to a new list element
            i += 1
            proposal.append("")
        proposal[i] += text

    if not proposal[0]:
        proposal[0] = "*Empty*"

    return proposal


def fill_battle_embed_fields(
    embed: discord.Embed,
    bot: "CarFiguresBot",
    battler1: BattlingUser,
    battler2: BattlingUser,
    compact: bool = False,
):
    """
    Fill the fields of an embed with the items part of a battle.

    This handles embed limits and will shorten the content if needed.

    Parameters
    ----------
    embed: discord.Embed
        The embed being updated. Its fields are cleared.
    bot: CarFiguresBot
        The bot object, used for getting emojis.
    battler1: BattlingUser
        The player that initiated the battle, displayed on the left side.
    battler2: BattlingUser
        The player that was invited to battle, displayed on the right side.
    compact: bool
        If `True`, display carfigures in a compact way. This should not be used directly.
    """
    embed.clear_fields()

    # first, build embed strings
    # to play around the limit of 1024 characters per field, we'll be using multiple fields
    # these vars are list of fields, being a list of lines to include
    battler1_proposal = _build_list_of_strings(battler1, bot, compact)
    battler2_proposal = _build_list_of_strings(battler2, bot, compact)

    # then display the text. first page is easy
    embed.add_field(
        name=f"{_get_prefix_emote(battler1)} {battler1.user.name}",
        value=battler1_proposal[0],
        inline=True,
    )
    embed.add_field(
        name=f"{_get_prefix_emote(battler2)} {battler2.user.name}",
        value=battler2_proposal[0],
        inline=True,
    )

    if len(battler1_proposal) > 1 or len(battler2_proposal) > 1:
        # we'll have to trick for displaying the other pages
        # fields have to stack themselves vertically
        # to do this, we add a 3rd empty field on each line (since 3 fields per line)
        i = 1
        while i < len(battler1_proposal) or i < len(battler2_proposal):
            embed.add_field(name="\u200B", value="\u200B", inline=True)  # empty

            if i < len(battler1_proposal):
                embed.add_field(name="\u200B", value=battler1_proposal[i], inline=True)
            else:
                embed.add_field(name="\u200B", value="\u200B", inline=True)

            if i < len(battler2_proposal):
                embed.add_field(name="\u200B", value=battler2_proposal[i], inline=True)
            else:
                embed.add_field(name="\u200B", value="\u200B", inline=True)
            i += 1

        # always add an empty field at the end, otherwise the alignment is off
        embed.add_field(name="\u200B", value="\u200B", inline=True)

    if len(embed) > 6000:
        if not compact:
            return fill_battle_embed_fields(embed, bot, battler1, battler2, compact=True)
        else:
            embed.clear_fields()
            embed.add_field(
                name=f"{_get_prefix_emote(battler1)} {battler1.user.name}",
                value=f"Battle too long, only showing last page:\n{battler1_proposal[-1]}",
                inline=True,
            )
            embed.add_field(
                name=f"{_get_prefix_emote(battler2)} {battler2.user.name}",
                value=f"Battle too long, only showing last page:\n{battler2_proposal[-1]}",
                inline=True,
            )
