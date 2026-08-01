import sys
import argparse
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="PDF-Toolkit - универсальный инструмент для работы с PDF",
        usage="python main.py [--gui] [--cli] [аргументы]"
    )
    
    parser.add_argument("--gui", action="store_true", help="Запустить графический интерфейс")
    parser.add_argument("--cli", action="store_true", help="Запустить командную строку")
    parser.add_argument("--version", action="store_true", help="Показать версию")
    
    args, unknown = parser.parse_known_args()
    return args, unknown


def show_version():
    version = "0.1.1"
    print(f"PDF-Toolkit v{version}")


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
            print(f"Ошибка загрузки CLI: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка в CLI: {e}")
            sys.exit(1)
    
    if args.gui or len(sys.argv) == 1:
        try:
            from gui.gui import run_gui as gui_main
            gui_main()
        except ImportError as e:
            print(f"Ошибка загрузки GUI: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка при запуске GUI: {e}")
            sys.exit(1)
    
    else:
        print("Использование:")
        print("  python main.py --gui          # Запуск GUI")
        print("  python main.py --cli <args>   # Запуск CLI")
        print("  python main.py --version      # Показать версию")
        sys.exit(0)


if __name__ == "__main__":
    main()