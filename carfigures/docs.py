from pathlib import Path
import yaml

class DocsManager:
    def __init__(self, docs: str):
        self.docs = Path(docs)
        self.topics = self._load_topics()

    def _load_topics(self):
        topics = {}
        for topic_folder in self.docs.iterdir():
            if topic_folder.is_dir():
                topic_info = self._load_topic_info(topic_folder)
                if topic_info:
                    topics[topic_folder.name] = topic_info
        return topics

    def _load_topic_info(self, topic_folder):
        info_file = topic_folder / 'info.yaml'
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return None

    def get_topic_content(self, topic: str, language: str):
        topic_folder = self.docs / topic
        lang_file = topic_folder / f'{language}.md'
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
