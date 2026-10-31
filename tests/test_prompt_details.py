"""Проверки пропорций превью и точного отображения и копирования полей карточки."""

from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage

from promptexplorer.models import Prompt
from promptexplorer.ui.image_preview import ImagePreview, thumbnail_from_file
from promptexplorer.ui.prompt_details import PromptDetails, TextSection


@pytest.mark.parametrize("width,height", [(400, 400), (800, 400), (400, 800)])
def test_preview_frame_follows_image_proportions(qapp, tmp_path, width, height):
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor("#365b92"))
    path = tmp_path / "art.png"
    assert image.save(str(path))
    preview = ImagePreview()
    preview.set_image(thumbnail_from_file(str(path)))
    frame = preview.image.size()
    pixmap = preview.image.pixmap()
    assert abs(frame.width() / frame.height() - width / height) < 0.01
    assert abs(pixmap.width() / pixmap.height() - width / height) < 0.03
    if width == height:
        assert frame.width() == frame.height()
    preview.set_image(None)
    assert preview.image.width() == preview.image.height()
    assert preview.image.pixmap().isNull()


def test_collapsed_section_copies_complete_original(qapp):
    section = TextSection("Positive prompt")
    original = ("<lora:night:0.7>, blue sky, <b>literal text</b>\n" * 30).rstrip()
    section.set_text(original)
    assert section.body.text() != original
    assert section.body.textFormat() == Qt.PlainText
    section.copy_button.click()
    assert qapp.clipboard().text() == original
    section.toggle.click()
    assert section.body.text() == original
    section.toggle.click()
    assert section.body.text() != original
    section.set_text("Другой промт")
    assert section.body.text() == "Другой промт"
    assert section.toggle.isHidden()
    section.set_text("")
    assert not section.copy_button.isEnabled()


def sample_prompt():
    return Prompt(
        1,
        "Пейзажи",
        "<b>Город</b>",
        "Описание",
        "Свет",
        "Шум",
        "detail:0.6\nnight:0.4",
        "SDXL",
        "2026-11-01 00:00:00",
        "2026-11-01 00:00:00",
    )


def test_prompt_card_updates_resources_and_literal_text(qapp):
    card = PromptDetails()
    prompt = sample_prompt()
    card.set_prompt(prompt)
    assert card.title.text() == "<b>Город</b>"
    assert card.title.textFormat() == Qt.PlainText
    assert card.resources.count() == 3
    assert card.sections["positive"].body.text() == "Свет"
    card.sections["negative"].copy_button.click()
    assert qapp.clipboard().text() == "Шум"
    old_resources = [card.resources.itemAt(i).widget() for i in range(card.resources.count())]
    card.set_prompt(replace(prompt, name="Другой", model="", lora="", positive="", negative=""))
    assert card.resources.count() == 1
    assert all(row.isHidden() for row in old_resources)
    assert card.title.text() == "Другой"
    assert not card.sections["positive"].copy_button.isEnabled()
    card.setPlainText("Ничего не найдено.")
    assert card.content.isHidden()
    assert card.toPlainText() == "Ничего не найдено."
