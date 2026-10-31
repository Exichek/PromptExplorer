# Разработка и проверки

Python 3.11–3.14. Проверяемые конфигурации CI: Windows и Linux, Python 3.11 и 3.14.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux:

```bash
source .venv/bin/activate
```

Установка зафиксированного окружения разработки:

```bash
python -m pip install -r requirements-dev.lock
python -m pip install --no-build-isolation --no-deps -e .
```

Проверки перед коммитом:

```bash
python -m pytest
ruff check .
ruff format --check .
python -m build --no-isolation
```

Тесты Qt запускаются через offscreen и не требуют видимого окна. Все базы и настройки
тестов временные. Проверяются откат неудачного импорта, сохранность данных при миграции,
резервные копии, связи профилей, поиск, выбор записи, переключение профилей и темы.

Снимки интерфейса с демонстрационными данными:

```bash
python scripts/preview.py --output build/preview
```

Сборка приложения для текущей ОС:

```bash
python scripts/build.py
python scripts/package.py
```

Результат — вся папка `dist/PromptExplorer`; переносить один exe без остальных файлов нельзя.
Команда упаковки создаёт ZIP для Windows или tar.gz для Linux и файл SHA-256 рядом с архивом.
Проверка запуска собранного приложения без пользовательской базы:

```powershell
dist\PromptExplorer\PromptExplorer.exe --smoke-test
```

Linux:

```bash
QT_QPA_PLATFORM=offscreen dist/PromptExplorer/PromptExplorer --smoke-test
```

На Linux для обычного запуска нужны системные библиотеки Qt/X11. Сборка выполняется
на той ОС, для которой предназначен результат. Автоматическая сборка сохраняет архивы
в артефактах GitHub Actions и не публикует релиз самостоятельно.

В Windows Qt использует системный ICU. Спецификация исключает одноимённые DLL,
случайно найденные в PATH сторонних программ: их набор функций может быть несовместим.
Проверка сборки в CI запускается через offscreen, без видимых окон.

Рабочая ветка — `develop`; для изменений создаются отдельные ветки и pull request.
`main` обновляется отдельно после проверки. Коммиты и описание изменений — на русском.
