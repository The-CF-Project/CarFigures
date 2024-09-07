from typing import Dict, Any
from pathlib import Path
import yaml
import logging

log = logging.getLogger("carfigures.langs")


class DocsManager:
    def __init__(self):
        self.topics: Dict[str, Dict[str, Any]] = {}
        self.default_language = "english"

    def load_topics(self, docs_path: Path):
        for topic_folder in docs_path.iterdir():
            if topic_folder.is_dir():
                topic_info = self._load_topic_info(topic_folder)
                if topic_info:
                    self.topics[topic_folder.name] = topic_info

    def _load_topic_info(self, topic_folder: Path):
        info_file = topic_folder / "info.yaml"
        if info_file.exists():
            with open(info_file, "r", encoding="utf-8") as f:
                info = yaml.safe_load(f)

            for lang in topic_folder.glob("*.md"):
                sel_lang = lang.stem
                with open(lang, "r", encoding="utf-8") as f:
                    info[sel_lang] = f.read()

            return info
        return None

    def get_topic_content(self, topic: str, language: str) -> str:
        topic_info = self.topics.get(topic, {})
        return topic_info.get(
            language, topic_info.get(self.default_language, "Content not available")
        )


docsmanager = DocsManager()


def loaddocs(docs_path: Path):
    docsmanager.load_topics(docs_path)
    log.info("Documentation has been loaded!")


def getdoc(topic: str, language: str) -> str:
    return docsmanager.get_topic_content(topic, language)
