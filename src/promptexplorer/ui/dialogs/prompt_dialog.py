from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...models import Prompt
from ..utils import theme_qss


class PromptDialog(QDialog):
    """Редактор промта, в котором обязательно только название."""

    def __init__(self, types: list[str], icon: QIcon, theme: str, existing: Prompt | None = None):
        super().__init__()

        self.setWindowTitle("Редактировать промт" if existing else "Новый промт")
        self.setWindowIcon(icon)
        self.setStyleSheet(theme_qss(theme))

        self.type = QComboBox()
        self.type.setEditable(True)
        self.type.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.type.setMaxVisibleItems(12)
        self.type.addItems(types)
        self.type.setCurrentIndex(-1)

        completer = QCompleter(self.type.model(), self.type)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.type.setCompleter(completer)

        self.name = QLineEdit()
        self.model = QLineEdit()

        self.lora = QPlainTextEdit()
        self.description = QPlainTextEdit()
        self.positive = QPlainTextEdit()
        self.negative = QPlainTextEdit()

        self.lora.setMinimumHeight(90)
        self.description.setMinimumHeight(110)
        self.positive.setMinimumHeight(170)
        self.negative.setMinimumHeight(170)

        self.name.setPlaceholderText("Пример: Dragon")
        self.type.setPlaceholderText("Необязательно — Без категории")
        self.model.setPlaceholderText("Необязательно, например SDXL")

        self.lora.setPlaceholderText("Через запятую или построчно")
        self.description.setPlaceholderText("Описание: чтобы не запутаться, что это за промт")
        self.positive.setPlaceholderText("Positive: ключевые слова/теги, описание сцены")
        self.negative.setPlaceholderText("Negative: что исключить")

        form = QFormLayout()
        form.addRow("Название *:", self.name)
        form.addRow("Категория:", self.type)
        form.addRow("Модель:", self.model)
        form.addRow("LoRA:", self.lora)
        form.addRow("Описание:", self.description)
        form.addRow("Positive:", self.positive)
        form.addRow("Negative:", self.negative)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText("Сохранить")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        self.buttons.accepted.connect(self._validate_then_accept)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        hint = QLabel("Обязательно только название. Остальное можно заполнить позже.")
        hint.setWordWrap(True)
        hint.setObjectName("Hint")
        root.addWidget(hint)
        fields = QWidget()
        fields.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(fields)
        root.addWidget(scroll)
        root.addWidget(self.buttons)
        self.setMinimumWidth(500)
        self.resize(700, 720)
        save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        save_shortcut.activated.connect(self._validate_then_accept)

        self.prompt_id: int | None = None
        if existing:
            self.prompt_id = existing.id
            self.name.setText(existing.name)
            self.type.setCurrentText(existing.type)
            self.model.setText(existing.model)
            self.lora.setPlainText(existing.lora)
            self.description.setPlainText(existing.description)
            self.positive.setPlainText(existing.positive)
            self.negative.setPlainText(existing.negative)
        self._initial_data = self.data()

    def reject(self) -> None:
        """Предупредить о потере несохранённых изменений при закрытии редактора."""
        if self.data() != self._initial_data:
            answer = QMessageBox.question(
                self,
                "Несохранённые изменения",
                "Закрыть редактор без сохранения?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        super().reject()

    def _validate_then_accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, "Проверьте поля", "Укажите название промта.")
            return
        self.accept()

    def data(self) -> dict[str, str]:
        return {
            "type_name": self.type.currentText().strip(),
            "name": self.name.text().strip(),
            "model": self.model.text().strip(),
            "lora": self.lora.toPlainText().strip(),
            "description": self.description.toPlainText().strip(),
            "positive": self.positive.toPlainText().strip(),
            "negative": self.negative.toPlainText().strip(),
        }
