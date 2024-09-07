import yaml
import logging
from typing import Dict
from carfigures.core.models import Languages
from pathlib import Path

log = logging.getLogger("carfigures.langs")

LANGUAGE_MAP = {
    1: "English",
    2: "Français",
    3: "العربية",
    4: "中文",
    5: "Deutsch",
    6: "Русский",
    7: "Türkçe",
    8: "Ελληνικά",
    9: "Dansk",
    10: "Polski",
    11: "Lietuvių",
    12: "Українська",
    13: "Bosanski",
    14: "Tiếng Việt",
}


class LanguageManager:
    def __init__(self):
        self.languages: Dict[str, Dict[str, str]] = {}
        self.default_language = "english"

    def _load_langs(self, file_path: Path):
        with open(file_path, "r", encoding="utf-8") as f:
            self.languages = yaml.safe_load(f)

    def _get_translation(self, key: str, language: Languages, **kwargs) -> str:
        lang = language.name.lower()
        translation = self.languages.get(lang, {}).get(
            key, self.languages[self.default_language][key]
        )
        return translation.format(**kwargs)


langmanager = LanguageManager()


def readlangs(file_path: Path):
    langmanager._load_langs(file_path)
    log.info("Languages have been loaded!")


def translate(key: str, language: Languages, **kwargs) -> str:
    return langmanager._get_translation(key, language, **kwargs)
