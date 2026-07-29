import argparse
import os
import json
from pathlib import Path
from backend.extract_pages import extract_pages, process_all_pdfs
from backend.data import PDFDatabaseManager, ExcelExporter
from backend.clear_path import DirectoryNormalizer
from backend.ocr import RegionExtractor


def main():
    # Главный парсер утилиты
    parser = argparse.ArgumentParser(
        description="PDF-Toolkit Pro: Универсальная консольная утилита для работы с PDF."
    )
    
    # Создаем контейнер для подкоманд
    subparsers = parser.add_subparsers(dest="action", required=True, help="Доступные модули")

    # ==========================================
    # ПОДКОМАНДА 1: split
    # ==========================================
    split_parser = subparsers.add_parser("split", help="Модуль извлечения/разделения страниц PDF")
    split_parser.add_argument("-i", "--input", required=True, help="Путь к PDF-файлу или папке")
    split_parser.add_argument("-o", "--output", help="Папка для сохранения")
    split_parser.add_argument("-d", "--directory", action="store_true", help="Флаг: обрабатывать как папку")
    split_parser.add_argument("-m", "--mode", choices=["first", "last", "range"], required=True, help="Режим")
    split_parser.add_argument("-v", "--value", type=int, help="Количество страниц")
    split_parser.add_argument("-s", "--start", type=int, help="Начальная страница")
    split_parser.add_argument("-e", "--end", type=int, help="Конечная страница")

    # ==========================================
    # ПОДКОМАНДА 2: db
    # ==========================================
    db_parser = subparsers.add_parser("db", help="Модуль индексации метаданных в SQLite")
    db_parser.add_argument("--database", default="pdf_toolkit.db", help="Путь к файлу БД")
    
    db_actions = db_parser.add_subparsers(dest="db_task", required=True, help="Действия с базой данных")
    
    scan_p = db_actions.add_parser("scan", help="Сканировать папку в БД")
    scan_p.add_argument("-p", "--path", required=True, help="Путь к папке")
    
    db_actions.add_parser("stats", help="Показать статистику БД")
    
    export_p = db_actions.add_parser("export", help="Экспорт в Excel")
    export_p.add_argument("-o", "--output", default="pdf_report.xlsx", help="Имя Excel файла")
    export_p.add_argument("-c", "--columns", help="Колонки через запятую")

    # ==========================================
    # ПОДКОМАНДА 3: normalize
    # ==========================================
    normalize_parser = subparsers.add_parser(
        "normalize", 
        help="Модуль нормализации структуры PDF файлов (поиск дубликатов)"
    )
    normalize_parser.add_argument("source", help="Исходная папка для сканирования PDF файлов")
    normalize_parser.add_argument("-o", "--output", help="Выходная папка (по умолчанию: source_parent/output)")
    normalize_parser.add_argument("--no-cleanup", action="store_true", help="Не очищать существующую выходную папку")
    normalize_parser.add_argument("--quiet", "-q", action="store_true", help="Отключить подробный вывод в консоль")

    # ==========================================
    # ПОДКОМАНДА 4: extract
    # ==========================================
    extract_parser = subparsers.add_parser(
        "extract",
        help="Модуль извлечения текста из PDF с обучением"
    )
    
    extract_parser.add_argument(
        "source",
        help="Путь к PDF файлу или папке"
    )
    
    extract_parser.add_argument(
        "-o", "--output",
        help="Путь для сохранения результата"
    )
    
    extract_parser.add_argument(
        "--mode",
        choices=["auto", "interactive", "batch"],
        default="auto",
        help="Режим работы: auto - автоматический, interactive - ручной выбор, batch - пакетный"
    )
    
    extract_parser.add_argument(
        "--opening",
        help="Открывающий маркер для поиска текста"
    )
    
    extract_parser.add_argument(
        "--closing",
        help="Закрывающий маркер для поиска текста"
    )
    
    extract_parser.add_argument(
        "--pages",
        help="Номера страниц для сканирования (через запятую, например: 0,1,2)"
    )
    
    extract_parser.add_argument(
        "--region",
        help="Координаты области в формате: x,y,w,h,page"
    )
    
    extract_parser.add_argument(
        "--template",
        help="Использовать сохраненный шаблон"
    )
    
    extract_parser.add_argument(
        "--no-learn",
        action="store_true",
        help="Отключить режим обучения (не сохранять шаблоны)"
    )
    
    extract_parser.add_argument(
        "--stats",
        action="store_true",
        help="Показать статистику работы экстрактора"
    )
    
    extract_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Отключить подробный вывод"
    )

    # ==========================================
    # ОБРАБОТКА ЛОГИКИ ВЫЗОВОВ
    # ==========================================
    args = parser.parse_args()

    def cli_logger(msg): 
        if not hasattr(args, 'quiet') or not args.quiet:
            print(f"[CLI LOG] {msg}")

    if args.action == "split":
        if args.mode == "range" and (args.start is None or args.end is None):
            split_parser.error("Для режима 'range' нужны --start и --end")
        if args.mode in ["first", "last"] and args.value is None:
            split_parser.error(f"Для режима '{args.mode}' нужен --value")

        if args.directory:
            process_all_pdfs(args.input, args.output, args.mode, args.value, args.start, args.end, log_callback=cli_logger)
        else:
            extract_pages(args.input, args.output, args.mode, args.value, args.start, args.end, log_callback=cli_logger)

    elif args.action == "db":
        manager = PDFDatabaseManager(args.database)
        try:
            if args.db_task == "scan":
                manager.scan_directory(args.path, log_callback=cli_logger)
            elif args.db_task == "stats":
                df = manager.get_all_records()
                print(f"\nВсего записей в БД: {len(df)}")
                if not df.empty:
                    print(df[['file_name', 'pages']].head(3).to_string())
            elif args.db_task == "export":
                exporter = ExcelExporter(args.database)
                exporter.export_to_excel(None, args.output, log_callback=cli_logger)
        finally:
            manager.close()

    elif args.action == "normalize":
        try:
            normalizer = DirectoryNormalizer(args.source, args.output)
            result = normalizer.normalize_structure()
            
            if not args.quiet:
                print(f"\n{'='*50}")
                print("📊 РЕЗУЛЬТАТЫ НОРМАЛИЗАЦИИ")
                print(f"{'='*50}")
                print(f"✅ Успешно обработано: {result['stats']['success']}")
                print(f"🔄 Дубликатов найдено: {result['stats']['duplicates']}")
                print(f"❌ Ошибок: {result['stats']['errors']}")
                print(f"\n📁 Основная папка: {result['structure']['work_dir']}")
                print(f"📁 Папка дубликатов: {result['structure']['check_dir']}")
                print(f"📄 Папка отчетов: {result['structure']['results_dir']}")
                
                if result['stats']['errors'] > 0 and 'errors_list' in result:
                    print(f"\n⚠️ Первые 5 ошибок:")
                    for error in result['errors_list'][:5]:
                        print(f"  • {error}")
                
                print(f"\n{'='*50}")
                print("✨ Нормализация завершена!")
            
            return result
            
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            return None

    elif args.action == "extract":
        try:
            extractor = RegionExtractor()
            
            if args.stats:
                stats = extractor.get_stats()
                print(f"\n{'='*50}")
                print("📊 СТАТИСТИКА ЭКСТРАКТОРА")
                print(f"{'='*50}")
                print(f"Сохраненных шаблонов: {stats['templates_count']}")
                print(f"Записей в истории: {stats['history_count']}")
                print(f"Средний процент успеха: {stats['avg_success_rate']*100:.1f}%")
                print(f"Самый используемый шаблон: {stats['most_used']}")
                print(f"{'='*50}")
                return

            if args.no_learn:
                extractor.learning_mode = False

            markers = None
            if args.opening or args.closing:
                markers = {
                    'opening': args.opening or '',
                    'closing': args.closing or ''
                }

            region = None
            if args.region:
                try:
                    coords = [int(x.strip()) for x in args.region.split(',')]
                    if len(coords) >= 4:
                        region = {
                            'x': coords[0],
                            'y': coords[1],
                            'w': coords[2],
                            'h': coords[3],
                            'page': coords[4] if len(coords) > 4 else 0
                        }
                except ValueError:
                    print("⚠️ Неверный формат региона. Используйте: x,y,w,h,page")

            source_path = Path(args.source)
            
            if source_path.is_file():
                interactive = args.mode == "interactive"
                result = extractor.extract(
                    str(source_path), 
                    markers=markers,
                    interactive=interactive
                )
                
                if not args.quiet:
                    print(f"\n{'='*50}")
                    print(f"📄 РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ")
                    print(f"{'='*50}")
                    print(f"Файл: {source_path.name}")
                    print(f"Статус: {'✅ УСПЕШНО' if result['success'] else '❌ НЕ УДАЛОСЬ'}")
                    print(f"Метод: {result.get('method', 'unknown')}")
                    print(f"Уверенность: {result.get('confidence', 0)*100:.0f}%")
                    if result['success'] and result['text']:
                        print(f"\nИзвлеченный текст:")
                        print("-" * 50)
                        print(result['text'][:500])
                        if len(result['text']) > 500:
                            print("... (текст обрезан)")
                        print("-" * 50)
                
                if args.output and result['success'] and result['text']:
                    output_path = Path(args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(result['text'])
                    print(f"💾 Результат сохранен в: {output_path}")
                
            elif source_path.is_dir():
                if args.mode == "interactive":
                    print("⚠️ Интерактивный режим недоступен для папок. Используйте режим batch или auto")
                    return
                
                results = extractor.extract_batch(
                    str(source_path),
                    markers=markers,
                    interactive=False
                )
                
                success_count = sum(1 for r in results if r['success'])
                
                if not args.quiet:
                    print(f"\n{'='*50}")
                    print(f"📁 ПАКЕТНАЯ ОБРАБОТКА")
                    print(f"{'='*50}")
                    print(f"Всего файлов: {len(results)}")
                    print(f"✅ Успешно: {success_count}")
                    print(f"❌ Неудачно: {len(results) - success_count}")
                    print(f"📊 Успешность: {success_count/len(results)*100:.1f}%")
                    
                    if success_count < len(results):
                        print(f"\n⚠️ Файлы с ошибками:")
                        for r in results:
                            if not r['success']:
                                print(f"  • {Path(r['pdf_path']).name}")
                
                if args.output:
                    output_path = Path(args.output)
                    output_path.mkdir(parents=True, exist_ok=True)
                    
                    for i, result in enumerate(results):
                        if result['success'] and result['text']:
                            file_name = Path(result['pdf_path']).stem
                            file_path = output_path / f"{file_name}_extracted.txt"
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(result['text'])
                    
                    print(f"💾 Результаты сохранены в: {output_path}")
                    
                    summary_path = output_path / "_summary.json"
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            'total': len(results),
                            'success': success_count,
                            'failed': len(results) - success_count,
                            'results': results
                        }, f, ensure_ascii=False, indent=2)
            
            else:
                print("❌ Указанный путь не существует")
                return
            
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    main()