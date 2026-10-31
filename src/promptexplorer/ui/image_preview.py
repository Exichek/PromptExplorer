"""Миниатюра результата генерации, связанная с выбранным промтом."""

from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt, Signal
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def thumbnail_from_file(path: str) -> bytes:
    """Прочитать PNG/JPEG/WebP и сохранить небольшую самостоятельную PNG-миниатюру."""
    if Path(path).stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Выберите изображение размером не больше 32 МБ.")
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    reader.setDecideFormatFromContent(True)
    if not reader.canRead() or bytes(reader.format()).lower() not in (b"png", b"jpeg", b"webp"):
        raise ValueError("Не удалось открыть изображение. Поддерживаются PNG, JPEG и WebP.")
    size = reader.size()
    if not size.isValid() or size.width() * size.height() > 100_000_000:
        raise ValueError("Слишком большое или повреждённое изображение.")
    if size.width() > 512 or size.height() > 512:
        reader.setScaledSize(size.scaled(QSize(512, 512), Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        raise ValueError("Не удалось прочитать изображение.")
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise ValueError("Не удалось подготовить превью.")
    return bytes(data)


class ImagePreview(QWidget):
    """Показать необязательный пример арта и предложить загрузку или удаление."""

    image_selected = Signal(bytes)
    remove_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setFixedWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Пример результата")
        title.setObjectName("Hint")
        self.image = QLabel("Превью не добавлено")
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setWordWrap(True)
        self.image.setFixedSize(220, 220)
        self.image.setObjectName("Preview")
        self.upload = QPushButton("Загрузить")
        self.remove = QPushButton("Убрать")
        self.upload.setToolTip("PNG, JPEG или WebP — сохраняется миниатюра до 512 px")
        self.upload.clicked.connect(self.choose_image)
        self.remove.clicked.connect(self.remove_requested.emit)
        buttons = QHBoxLayout()
        buttons.addWidget(self.upload)
        buttons.addWidget(self.remove)
        layout.addWidget(title)
        layout.addWidget(self.image, 0, Qt.AlignHCenter)
        layout.addLayout(buttons)
        layout.addStretch()
        self.set_image(None, enabled=False)

    def set_image(self, data: bytes | None, *, enabled: bool = True) -> None:
        """Обновить превью при выборе промта, не показывая картинку предыдущего."""
        self._pixmap = QPixmap()
        if data:
            self._pixmap.loadFromData(data)
        self.upload.setEnabled(enabled)
        self.remove.setEnabled(enabled and bool(data))
        if self._pixmap.isNull():
            self.image.setFixedSize(220, 220)
            self.image.setPixmap(QPixmap())
            self.image.setText("Превью не добавлено" if enabled else "Выберите промт")
        else:
            # Размер рамки повторяет пропорции изображения, в том числе для квадрата.
            size = self._pixmap.size().scaled(220, 320, Qt.KeepAspectRatio)
            self.image.setFixedSize(size)
            self.image.setPixmap(
                self._pixmap.scaled(size - QSize(2, 2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def choose_image(self) -> None:
        """Выбрать файл и передать миниатюру владельцу для сохранения в базе."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите пример арта", "", "Изображения (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        try:
            data = thumbnail_from_file(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Не удалось загрузить превью", str(exc))
            return
        self.image_selected.emit(data)
