import sys
import argparse
from pathlib import Path


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="PDF-Toolkit - универсальный инструмент для работы с PDF",
        usage="python main.py [--gui] [--cli] [аргументы]"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Запустить графический интерфейс"
    )
    
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Запустить командную строку"
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Показать версию"
    )
    
    args, unknown = parser.parse_known_args()
    return args, unknown


def show_version():
    """Показать версию приложения."""
    version = "0.1.0"
    print(f"PDF-Toolkit v{version}")
    print("© 2025 Все права защищены")
    print("\nМодули:")
    print("  - Индексация PDF")
    print("  - Извлечение текста (OCR)")
    print("  - Извлечение страниц")
    print("  - Экспорт данных")
    print("  - Нормализация структуры")
    print("  - Статистика")


def main():
    args, cli_args = parse_arguments()
    
    if args.version:
        show_version()
        sys.exit(0)
    
    if args.cli:
        try:
            from cli import main as cli_main
            sys.argv = [sys.argv[0]] + cli_args
            sys.exit(cli_main())
        except ImportError as e:
            print(f"❌ Ошибка загрузки CLI: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Ошибка в CLI: {e}")
            sys.exit(1)
    
    if args.gui or len(sys.argv) == 1:
        try:
            from gui.gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"❌ Ошибка загрузки GUI: {e}")
            print("Убедитесь, что файл существует: src/gui/gui.py")
            print("\nПереключение в CLI режим...")
            from cli import main as cli_main
            sys.exit(cli_main())
        except Exception as e:
            print(f"❌ Ошибка при запуске GUI: {e}")
            print("\nПереключение в CLI режим...")
            from cli import main as cli_main
            sys.exit(cli_main())
    
    else:
        print("Использование:")
        print("  python main.py --gui          # Запуск GUI")
        print("  python main.py --cli <args>   # Запуск CLI")
        print("  python main.py --version      # Показать версию")
        sys.exit(0)


if __name__ == "__main__":
    main()