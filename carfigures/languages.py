import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import tomllib

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("carfigures.languages")


@dataclass
class Langs:
    english: str = ""
    french: str = ""
    arabic: str = ""
    turkish: str = ""
    greek: str = ""
    russian: str = ""


langs = Langs()


def readlangs(path: "Path"):
    with open(path, "rb") as f:
        rlangs = tomllib.load(f)

    langs.english = rlangs["EN"]
    langs.french = rlangs["FR"]
    langs.arabic = rlangs["AR"]
    langs.turkish = rlangs["TR"]
    langs.greek = rlangs["EL"]
    langs.russian = rlangs["RU"]
