# PDF-Toolkit

[![Python Version](https://img.shields.io/badge/python-3.13.14-blue?style=for-the-badge)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)

PDF-Toolkit — утилита для обработки PDF: извлечение страниц, экспорт метаданных, нормализация структуры папок, разделение по штрих-кодам и распознавание текста (OCR). 

Скачайте готовый исполняемый файл для Windows или установите из исходного кода.  
[Скачать релиз](https://github.com/9podkir10-cmd/PDF-Toolkit/releases) · [Установка из исходного кода](#Установка-из-исходного-кода) · [Upcoming features](#Планируемые-изменения)

## Быстрый старт

1. Скачайте последнюю версию из раздела [Releases](https://github.com/9podkir10-cmd/PDF-Toolkit/releases).
2. Распакуйте архив в любую папку.
3. Запустите `PDF-Toolkit.exe`.
4. Укажите путь к Tesseract OCR (если используете) через настройки GUI.

## Что нового в версии v1.0.7?

- Централизована логика работы с `manifest.json`

## Функционал

Основной синтаксис:

```bash
python cli.py <команда> [аргументы]
# или через main.py:
python main.py --cli <команда> [аргументы]
```

Доступные команды:

### 1. `split` — Извлечение страниц

```bash
python cli.py split -i <путь> -m <режим> [-o <папка>] [-v <количество>] [-s <начало>] [-e <конец>]
```

- `-i, --input` — путь к PDF-файлу или папке (обязательно)
- `-o, --output` — папка для сохранения результатов (по умолчанию — рядом с исходным)
- `-m, --mode` — режим: `first`, `last`, `range` (обязательно)
- `-v, --value` — количество страниц для `first`/`last`
- `-s, --start` — начальная страница для `range`
- `-e, --end` — конечная страница для `range`

**Примеры:**

```bash
# Извлечь первую страницу из документа
python cli.py split -i document.pdf -m first -v 1

# Извлечь последние 5 страниц
python cli.py split -i document.pdf -m last -v 5

# Извлечь страницы с 3 по 10
python cli.py split -i document.pdf -m range -s 3 -e 10

# Обработать все PDF в папке
python cli.py split -i ./pdfs -m first -v 1 -o ./output
```

---

### 2. `export` — Экспорт метаданных

```bash
python cli.py export -i <путь> [-o <файл>] [-f <формат>] [-c <колонки>]
```

- `-i, --input` — путь к PDF-файлу или папке (обязательно)
- `-o, --output` — путь к выходному файлу (если не указан, создаётся рядом с входным)
- `-f, --format` — формат: `excel`, `csv`, `json`, `parquet`, `html`, `markdown`, `text`, `tsv`, `clipboard`
- `-c, --columns` — список колонок через запятую: `id, file_name, parent_directory, file_path, file_size, date_created, date_modified, pages, file_extension, file_name_hyperlink (для .xlsx)`

**Примеры:**

```bash
# Экспорт в Excel
python cli.py export -i ./pdfs -o report.xlsx

# Экспорт в CSV с выбором колонок
python cli.py export -i ./pdfs -f csv -c file_name,pages,file_size

# Копировать в буфер обмена
python cli.py export -i document.pdf -f clipboard
```

---

### 3. `index` — Индексация/нормализация

```bash
python cli.py index -i <только папка>
```

Приводит структуру директории к единому стандарту - хардлинки на уникальные файлы плюс manifest.json

---

### 4. `patch` — Разделение по штрих-кодам

```bash
python cli.py patch -i <путь> -m <режим> [-o <папка>]
```

- `-i, --input` — путь к PDF-файлу или папке (обязательно)
- `-o, --output` — папка для сохранения результатов
- `-m, --mode` — режим поиска: `patch1`, `patch2`, `patch3`, `patch4`, `patchT` (src\assets\patches-for-printing-on-a4-paper)

**Примеры:**

```bash
# Разделить один файл по штрих-коду patch1
python cli.py patch -i document.pdf -m patch1

# Обработать все PDF в папке
python cli.py patch -i ./pdfs -m patch3 -o ./output
```

---

### 5. `ocr` — извлечение текста

Запустите GUI:

```bash
python main.py --gui
# или просто
python main.py
```

В GUI вы можете все вышеперечисленное плюс:
- Выделять координаты боксов мышью.
- Распознавать текст (OCR).
- Переименовывать файлы и последовательно обрабатывать папки.

При первом запуске программа создаст файл `settings.json` рядом с исполняемым файлом.
Содержимое:

- `ocr_path` — путь к исполняемому файлу Tesseract (обязательно для OCR).
- `language` — язык распознавания: `rus`, `eng`, `rus+eng`.

В настройках есть опция сбора распозанных областей в папку `ocr_storage`.

- `images/` — все вырезанные области в формате PNG (имя файла — случайный UUID).
- `metadata.json` — JSON-файл с метаданными:

Все данные сохраняются локально, можно использовать для дообучения OCR

## Установка из исходного кода

```bash
git clone https://github.com/9podkir10-cmd/PDF-Toolkit.git
cd PDF-Toolkit
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
python main.py --gui
```

## Системные требования

- **Windows** (основная платформа), Linux/macOS (не тестировалось).
- **Python 3.9+** (для сборки из исходников).
- Для OCR необходим **Tesseract OCR** 4.0+ (скачать с [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)).

## Планируемые изменения

- Поддержка альтернативных движков OCR.
- Перенос части функционала на C++
- Централизовать логику работы с конфигом

## Лицензия

PDF-Toolkit распространяется под лицензией **MIT**. Подробности в файле `LICENSE`.