"""Необязательные параметры генерации и их безопасное хранение в JSON."""

import json
from typing import Any

GENERATION_FIELDS = (
    ("workflow", "WORKFLOW", "Например, txt2img или img2img:hires-fix"),
    ("priority", "PRIORITY", "Например, low"),
    ("output_format", "OUTPUTFORMAT", "Например, JPEG или PNG"),
    ("sampler", "SAMPLER", "Например, Euler A"),
    ("cfg_scale", "CFGSCALE", "Например, 4"),
    ("steps", "STEPS", "Например, 40"),
    ("clip_skip", "CLIPSKIP", "Например, 2"),
    ("seed", "SEED", "Например, 147572794 или -1"),
    ("denoise", "DENOISE", "Например, 0.5"),
    ("quantity", "QUANTITY", "Например, 1"),
)


def read_metadata(value: Any) -> dict[str, str]:
    """Прочитать строковые параметры, сохранив также неизвестные ключи при импорте."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("Некорректные параметры генерации.") from exc
    if not isinstance(value, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()
    ):
        raise ValueError("Параметры генерации должны содержать текстовые названия и значения.")
    return {key: item for key, item in value.items() if item}


def write_metadata(value: Any) -> str:
    """Сериализовать параметры без потери кириллицы и исходных значений."""
    result = json.dumps(read_metadata(value), ensure_ascii=False, sort_keys=True)
    if len(result.encode("utf-8")) > 65536:
        raise ValueError("Слишком большой объём параметров генерации.")
    return result
