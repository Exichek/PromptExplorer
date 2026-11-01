"""Читаемая карточка промта с ресурсами, отдельными секциями и копированием."""

import re
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..metadata import GENERATION_FIELDS
from ..models import Prompt
from .flow_layout import FlowLayout


def lora_resources(value: str) -> list[tuple[str, str | None]]:
    """Отделить явно заданный вес LoRA, не изменяя строку, сохранённую в промте."""
    numeric = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    # Десятичная запятая после двоеточия не должна разделять два ресурса.
    display = re.sub(r"(:\s*[+-]?\d+),(\d+)(?=\s*(?:>|[,;\n]|$))", r"\1.\2", value)
    result = []
    for resource in re.split(r"[,;\n]+", display):
        original = resource.strip()
        if not original:
            continue
        tag = re.fullmatch(r"<lora:(.+)>", original, re.IGNORECASE)
        body = tag.group(1) if tag else original
        incomplete = original.startswith("<") and tag is None
        match = (
            None
            if re.match(r"\w+://", body) or incomplete
            else re.fullmatch(rf"(.+):\s*({numeric})", body)
        )
        if match and match.group(1).strip():
            weight = re.sub(r"^([+-]?)\.", r"\g<1>0.", match.group(2))
            result.append((match.group(1).strip(), weight))
        else:
            result.append((original, None))
    return result


def text_label(text: str = "", name: str = "PromptText") -> QLabel:
    """Показать пользовательский текст буквально, без интерпретации HTML."""
    label = QLabel(text)
    label.setObjectName(name)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    return label


class TextSection(QWidget):
    """Отобразить полный текст или краткий фрагмент, всегда копируя оригинал."""

    copied = Signal()

    def __init__(self, title: str):
        super().__init__()
        self._text = ""
        self._expanded = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        caption = QLabel(title)
        caption.setObjectName("SectionTitle")
        self.copy_button = QPushButton("Копировать")
        self.copy_button.setObjectName("CopyButton")
        self.copy_button.setToolTip(f"Скопировать {title} целиком")
        self.copy_button.clicked.connect(self.copy)
        heading.addWidget(caption)
        heading.addStretch()
        heading.addWidget(self.copy_button)
        self.body = text_label()
        self.toggle = QPushButton("Показать полностью")
        self.toggle.setObjectName("TextToggle")
        self.toggle.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.toggle.clicked.connect(self.toggle_expanded)
        layout.addLayout(heading)
        layout.addWidget(self.body)
        layout.addWidget(self.toggle)

    def set_text(self, text: str) -> None:
        """Сменить текст и сбросить раскрытие при выборе другой записи."""
        self._text = text
        self._expanded = False
        self.copy_button.setEnabled(bool(text))
        self._render()

    def _render(self) -> None:
        long = len(self._text) > 520 or self._text.count("\n") > 7
        shown = self._text
        if long and not self._expanded:
            shown = "\n".join(self._text.splitlines()[:8])[:520].rstrip() + "…"
        self.body.setText(shown or "Не заполнено")
        self.toggle.setVisible(long)
        self.toggle.setText("Свернуть" if self._expanded else "Показать полностью")

    def toggle_expanded(self) -> None:
        """Раскрыть или свернуть только отображение, сохранив полный текст."""
        self._expanded = not self._expanded
        self._render()

    def copy(self) -> None:
        """Скопировать исходное поле без заголовков, сокращений и многоточия."""
        QApplication.clipboard().setText(self._text)
        self.copied.emit()


class PromptDetails(QScrollArea):
    """Карточка выбранного промта с компактными ресурсами и текстовыми секциями."""

    copied = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("PromptDetails")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(270)
        surface = QWidget()
        surface.setObjectName("PromptSurface")
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)
        self.empty = text_label("", "Hint")
        self.content = QWidget()
        content = QVBoxLayout(self.content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(18)
        self.title = text_label("", "PromptTitle")
        self.category = QLabel()
        self.category.setTextFormat(Qt.PlainText)
        self.category.setObjectName("ResourceBadge")
        self.category.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.category.setWordWrap(True)
        self.resource_box = QWidget()
        self.resources = QVBoxLayout(self.resource_box)
        self.resources.setContentsMargins(0, 0, 0, 0)
        self.resources.setSpacing(10)
        resources_title = QLabel("Ресурсы")
        resources_title.setObjectName("SectionTitle")
        self.description = text_label()
        self.sections = {
            "positive": TextSection("Positive prompt"),
            "negative": TextSection("Negative prompt"),
        }
        self.updated = text_label("", "Hint")
        self.metadata_box = QWidget()
        metadata_layout = QVBoxLayout(self.metadata_box)
        metadata_layout.setContentsMargins(0, 0, 0, 0)
        metadata_title = QLabel("Параметры генерации")
        metadata_title.setObjectName("SectionTitle")
        self.metadata_chips = QWidget()
        self.metadata_flow = FlowLayout(self.metadata_chips)
        metadata_layout.addWidget(metadata_title)
        metadata_layout.addWidget(self.metadata_chips)
        content.addWidget(self.title)
        content.addWidget(self.category)
        content.addWidget(resources_title)
        content.addWidget(self.resource_box)
        content.addWidget(self.description)
        for section in self.sections.values():
            separator = QFrame()
            separator.setObjectName("SectionSeparator")
            separator.setFixedHeight(1)
            content.addWidget(separator)
            content.addWidget(section)
            section.copied.connect(self.copied.emit)
        content.addWidget(self.metadata_box)
        content.addWidget(self.updated)
        layout.addWidget(self.empty)
        layout.addWidget(self.content)
        layout.addStretch()
        self.setWidget(surface)
        self.setPlainText("Создайте промт.")

    def setPlainText(self, text: str) -> None:
        """Показать пустое состояние вместо данных предыдущего промта."""
        self._plain_text = text
        self.content.hide()
        self.empty.setText(text)
        self.empty.show()
        for section in self.sections.values():
            section.set_text("")

    def toPlainText(self) -> str:
        """Вернуть полные данные без декоративного оформления и сокращений."""
        return self._plain_text

    def _resource(self, value: str, kind: str, weight: str | None = None) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = text_label(value, "ResourceName")
        badge = QLabel(kind)
        badge.setObjectName("ResourceBadge")
        layout.addWidget(label, 1)
        layout.addWidget(badge, 0, Qt.AlignTop)
        if weight is not None:
            weight_badge = QLabel(weight)
            weight_badge.setObjectName("WeightBadge")
            weight_badge.setAlignment(Qt.AlignCenter)
            weight_badge.setToolTip("Вес LoRA")
            layout.addWidget(weight_badge, 0, Qt.AlignTop)
        self.resources.addWidget(row)

    def set_prompt(self, prompt: Prompt) -> None:
        """Заполнить карточку реальными полями записи без выдуманных метаданных."""
        self._plain_text = "\n".join(
            [
                prompt.name,
                prompt.type,
                prompt.model,
                prompt.lora,
                prompt.description,
                prompt.positive,
                prompt.negative,
            ]
        )
        self.empty.hide()
        self.content.show()
        self.title.setText(prompt.name)
        self.category.setText(prompt.type)
        while self.resources.count():
            item = self.resources.takeAt(0)
            item.widget().hide()
            item.widget().deleteLater()
        if prompt.model:
            self._resource(prompt.model, "CHECKPOINT")
        for resource, weight in lora_resources(prompt.lora):
            self._resource(resource, "LORA", weight)
        if not prompt.model and not prompt.lora.strip():
            self.resources.addWidget(text_label("Модель и LoRA не указаны", "Hint"))
        self.description.setText(prompt.description)
        self.description.setVisible(bool(prompt.description))
        self.sections["positive"].set_text(prompt.positive)
        self.sections["negative"].set_text(prompt.negative)
        while self.metadata_flow.count():
            item = self.metadata_flow.takeAt(0)
            item.widget().hide()
            item.widget().deleteLater()
        labels = {key: caption for key, caption, _ in GENERATION_FIELDS}
        ordered = [key for key, _, _ in GENERATION_FIELDS if key in prompt.metadata]
        ordered.extend(key for key in prompt.metadata if key not in labels)
        for key in ordered:
            chip = text_label(
                f"{labels.get(key, key.upper())}: {prompt.metadata[key].upper()}", "MetadataBadge"
            )
            chip.setMargin(0)
            chip.setIndent(0)
            chip.setToolTip("<qt>" + escape(prompt.metadata[key]) + "</qt>")
            self.metadata_flow.addWidget(chip)
        self.metadata_box.setVisible(bool(prompt.metadata))
        self.updated.setText(f"Обновлён: {prompt.updated_at}")
        self.verticalScrollBar().setValue(0)
