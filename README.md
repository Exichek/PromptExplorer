# PromptExplorer v 0.9.0.0 beta

Приложение на Python (PySide6) для хранения, редактирования и организации промтов  
для Stable Diffusion, ComfyUI и других инструментов для генерации.

Профили, типы промтов (категории), создание / редактирование / удаление промтов,  
статистика по профилю, экспорт промтов в `.txt`, локальная база данных (SQLite),  
хранится в:
- **Windows:** `%APPDATA%/PromptExplorer`
- **Linux:** `~/.promptexplorer`

---

A Python (PySide6) desktop application for storing, editing, and organizing prompts  
for Stable Diffusion, ComfyUI, and similar tools.

Profiles, prompt types (categories), create / edit / delete prompts,  
profile-based statistics, export prompts to `.txt`, local SQLite database  
stored in:
- **Windows:** `%APPDATA%/PromptExplorer`
- **Linux:** `~/.promptexplorer`

---

## How to use

### 1. Установка зависимостей

Python **3.11+**.  

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

### Запуск с исходника

python run.py

OR 

### Сборка приложения (Windows)

python -m pip install pyinstaller
python -m PyInstaller --clean --noconsole --name PromptExplorer --onedir `
  --icon promptexplorer/resources/app.ico `
  --add-data "promptexplorer/resources/app.ico;resources" `
  --add-data "promptexplorer/resources/moon.png;resources" `
  --add-data "promptexplorer/resources/sun.png;resources" `
  run.py

### Сборка приложения (Linux)

python -m pip install pyinstaller
python -m PyInstaller --clean --name PromptExplorer --onedir \
  --add-data "promptexplorer/resources/app.ico:resources" \
  --add-data "promptexplorer/resources/moon.png:resources" \
  --add-data "promptexplorer/resources/sun.png:resources" \
  run.py
