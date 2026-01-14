from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QCompleter,
)

from ..models import Prompt
from ..utils import theme_qss


# ============================================================
# Dialog: Create / Edit prompt
# ============================================================

class PromptDialog(QDialog):

    def __init__(self, types: list[str], icon: QIcon, theme: str, existing: Prompt | None = None):
        super().__init__()

        self.setWindowTitle("Редактировать промт" if existing else "Новый промт")
        self.setWindowIcon(icon)
        self.setStyleSheet(theme_qss(theme))
        # ---------------------------
        # Type combobox (editable + search)
        # ---------------------------
        self.type = QComboBox()
        self.type.setEditable(True)
        self.type.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # Qt6-правильно
        self.type.setMaxVisibleItems(12)
        self.type.addItems(types)

        if hasattr(self.type, "setAutoCompletion"):
            self.type.setAutoCompletion(False)

        completer = QCompleter(self.type.model(), self.type)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.type.setCompleter(completer)

        le = self.type.lineEdit()
        le.textEdited.connect(lambda txt: self.type.showPopup() if txt.strip() else self.type.hidePopup())
        # ---------------------------
        # Other fields
        # ---------------------------
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
        self.type.setPlaceholderText("Пример: Cowgirl pose")
        self.model.setPlaceholderText("Пример: Xavier")

        self.lora.setPlaceholderText("Через запятую или построчно")
        self.description.setPlaceholderText("Описание: чтобы не запутаться, что это за промт")
        self.positive.setPlaceholderText("Positive: ключевые слова/теги, описание сцены")
        self.negative.setPlaceholderText("Negative: что исключить")
        # ---------------------------
        # Form layout
        # ---------------------------
        form = QFormLayout()
        form.addRow("Name:", self.name)
        form.addRow("Type:", self.type)
        form.addRow("Model:", self.model)
        form.addRow("LoRA:", self.lora)
        form.addRow("Описание:", self.description)
        form.addRow("Positive:", self.positive)
        form.addRow("Negative:", self.negative)

        # Save/Cancel
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._validate_then_accept)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.buttons)

        self.setMinimumWidth(640)

        # ---------------------------
        # If editing — prefill the fields
        # ---------------------------
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

    def _validate_then_accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, "Допиши", "Поле Name не заполнено.")
            return
        if not self.type.currentText().strip():
            QMessageBox.warning(self, "Допиши", "Поле Type не заполнено.")
            return
        if not self.model.text().strip():
            QMessageBox.warning(self, "Допиши", "Поле Model не заполнено.")
            return
        self.accept()

    def data(self) -> dict[str, str]:
        return {
            "type_name": self.type.currentText().strip(),
            "name": self.name.text().strip(),
            "model": self.model.text().strip(),
            "lora": self.lora.toPlainText().strip(),
            "description": self.description.toPlainText().strip() or "(без описания)",
            "positive": self.positive.toPlainText().strip(),
            "negative": self.negative.toPlainText().strip(),
        }
