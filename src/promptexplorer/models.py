from dataclasses import dataclass

# ============================================================
# Модель промта
# ============================================================


@dataclass
class Prompt:
    id: int
    type: str
    name: str
    description: str
    positive: str
    negative: str
    lora: str
    model: str
    created_at: str
    updated_at: str
    preview: bytes | None = None
