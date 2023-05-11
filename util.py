import os
import json
from typing import Any, List


def config(key: str) -> Any:
    config_dir = os.path.abspath(os.path.dirname(__file__))
    config_path = os.path.join(config_dir, 'config.json')
    data = {}
    with open(config_path, 'r', encoding='utf8') as fp:
        data = json.load(fp)
        if key in data:
            return data[key]
    return None


def get_tags(text: str) -> List:
    text = text.strip()
    words = text.split()
    tags_list = []
    text_list = []
    for word in words:
        word = word.strip()
        if word[0] == '#':
            tags_list.append(word)
        else:
            text_list.append(word)
    return [' '.join(text_list), tags_list]
