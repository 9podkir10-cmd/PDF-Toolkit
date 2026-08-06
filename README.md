# PDF Toolkit

Набор инструментов для обработки PDF-файлов: извлечение страниц, работа со штрих-кодами и распознавание текста (OCR).

[![Build Status](https://img.shields.io/github/actions/workflow/status/username/pdf-toolkit/ci.yml?style=for-the-badge)](https://github.com/username/pdf-toolkit/actions)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue?style=for-the-badge)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)

## О проекте

PDF Toolkit — это инструмент для автоматизации рутинных задач по обработке PDF-документов. Проект разработан на Python и предоставляет два способа взаимодействия: графический интерфейс (GUI), командную строку (CLI)

## Основные возможности

- **Извлечение страниц:** Выделение отдельных страниц или диапазонов из PDF-файлов.
- **Работа со штрих-кодами:** Автоматическое обнаружение и декодирование штрих-кодов на страницах.
- **Оптическое распознавание (OCR):** Распознавание текста с использованием сторонних движков.
- **Гибкость запуска:** Поддержка как графического интерфейса, так и скриптов командной строки.
- **Конфигурация:** Управление настройками через `settings.json`.

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/username/pdf-toolkit.git
   cd pdf-toolkit