"""Читаемая карточка промта с ресурсами, отдельными секциями и копированием."""

import re

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

from ..models import Prompt


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

    def _resource(self, value: str, kind: str) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = text_label(value, "ResourceName")
        badge = QLabel(kind)
        badge.setObjectName("ResourceBadge")
        layout.addWidget(label, 1)
        layout.addWidget(badge, 0, Qt.AlignTop)
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
        for resource in re.split(r"[,\n]+", prompt.lora):
            if resource.strip():
                self._resource(resource.strip(), "LORA")
        if not prompt.model and not prompt.lora.strip():
            self.resources.addWidget(text_label("Модель и LoRA не указаны", "Hint"))
        self.description.setText(prompt.description)
        self.description.setVisible(bool(prompt.description))
        self.sections["positive"].set_text(prompt.positive)
        self.sections["negative"].set_text(prompt.negative)
        self.updated.setText(f"Обновлён: {prompt.updated_at}")
        self.verticalScrollBar().setValue(0)
