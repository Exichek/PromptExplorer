"""Перенос небольших плашек на следующую строку по доступной ширине."""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QLabel, QLayout


class FlowLayout(QLayout):
    """Размещать элементы слева направо без горизонтальной прокрутки."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(6)

    def addItem(self, item):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), False)

    def minimumSize(self):
        return QSize(0, max((item.minimumSize().height() for item in self._items), default=0))

    def sizeHint(self):
        return self.minimumSize()

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, True)

    def _arrange(self, rect, apply):
        x, y, row_height = rect.x(), rect.y(), 0
        for item in self._items:
            widget = item.widget()
            hint = widget.sizeHint()
            natural_width = (
                widget.fontMetrics().horizontalAdvance(widget.text()) + 16
                if isinstance(widget, QLabel)
                else hint.width()
            )
            width = min(natural_width, max(1, rect.width()))
            height = widget.heightForWidth(width) if widget.hasHeightForWidth() else hint.height()
            if x > rect.x() and x + width > rect.x() + rect.width():
                x = rect.x()
                y += row_height + self.spacing()
                row_height = 0
            if apply:
                item.setGeometry(QRect(x, y, width, max(1, height)))
            x += width + self.spacing()
            row_height = max(row_height, height)
        return y + row_height - rect.y()
