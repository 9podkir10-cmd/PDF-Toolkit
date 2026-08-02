import argparse
import os
import json
from pathlib import Path
from backend.extract_pages import extract_pages, process_all_pdfs
from backend.collect_data import scan_and_export
from backend.clear_path import DirectoryNormalizer
from backend.barcodes import process_single_pdf_file, process_directory

def main():
    parser = argparse.ArgumentParser(description="PDF-Toolkit: Универсальная утилита для работы с PDF.")
    
    subparsers = parser.add_subparsers(dest="action", required=True, help="Доступные модули")

    # ПОДКОМАНДА 1: разделение пдф
    split_parser = subparsers.add_parser("split", help="Модуль извлечения/разделения страниц PDF")
    split_parser.add_argument("-i", "--input", required=True, help="Путь к PDF-файлу или папке")
    split_parser.add_argument("-o", "--output", help="Папка для сохранения")
    split_parser.add_argument("-m", "--mode", choices=["first", "last", "range"], required=True, help="Режим")
    split_parser.add_argument("-v", "--value", type=int, help="Количество страниц")
    split_parser.add_argument("-s", "--start", type=int, help="Начальная страница")
    split_parser.add_argument("-e", "--end", type=int, help="Конечная страница")


    # ПОДКОМАНДА 2: экспорт (ecxel, scv, cipboard, json и т.д.)
    export_parser = subparsers.add_parser("export", help="Модуль экспорта метаданных пдф")
    export_parser.add_argument("-i","--input", help="Путь к PDF-файлу или папке")
    export_parser.add_argument("-o", "--output", help="Папка для сохранения")
    export_parser.add_argument("-f", "--format",
    choices=['excel', 'csv', 'json', 'parquet', 'html', 'markdown', 'text', 'tsv', 'clipboard'], 
    default='excel', help="Формат экспорта (по умолчанию - excel)")
    export_parser.add_argument("-c", "--columns", help="Нужные колонки через запятую: id, file_name, parent_directory, file_path, file_size, date_created, date_modified, pages, file_extension, file_name_hyperlink]")


    # ПОДКОМАНДА 3: приведение директории в порядок перед индексацией + индексация
    index_parser = subparsers.add_parser("index",  help="Модуль индексации PDF файлов")
    index_parser.add_argument("-i", "--input", help="Исходная ПАПКА для сканирования PDF файлов")
    # index_parser.add_argument("--ocr", help="Путь к движку распознавания текста (.exe, в будущем обработка нейронок)")
    # index_parser.add_argument("-r", "--region", help="Координаты области в формате: x,y,w,h,page")
    # index_parser.add_argument("-t", "--template", help="Использовать сохраненный шаблон")

    # ПОДКОМАНДА 4: разделение по штрихкодам
    patch_parser = subparsers.add_parser("patch", help="Модуль разделения PDF по штрихкодам")
    patch_parser.add_argument("-i", "--input", required=True, help="Путь к PDF-файлу или папке")
    patch_parser.add_argument("-o", "--output", help="Папка для сохранения")
    patch_parser.add_argument("-m", "--mode", choices=["patch1", "patch2", "patch3","patch4","patchT"],
                              required=True, help="Режим")

    #ПОДКОМАНДА 5: обработка дубликатов (в разработке...)

    # ОБРАБОТКА ЛОГИКИ ВЫЗОВОВ
    args = parser.parse_args()

    def cli_logger(msg): 
        if not hasattr(args, 'quiet') or not args.quiet:
            print(f"[CLI LOG] {msg}")

    if args.action == "split":
        if args.mode == "range" and (args.start is None or args.end is None):
            split_parser.error("Для режима 'range' нужны --start и --end")
        if args.mode in ["first", "last"] and args.value is None:
            split_parser.error(f"Для режима '{args.mode}' нужен --value")

        input_path = args.input
        is_directory = os.path.isdir(input_path)
        if is_directory:
            process_all_pdfs(args.input, args.output, args.mode, args.value, args.start, args.end, log_callback=cli_logger)
        else:
            extract_pages(args.input, args.output, args.mode, args.value, args.start, args.end, log_callback=cli_logger)

    elif args.action == "export":
        if not args.input:
            export_parser.error("Требуется указать --input")
        
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Путь не существует: {input_path}")
            return
        
        columns = None
        if args.columns:
            columns = [col.strip() for col in args.columns.split(',')]
        
        format_map = {
            'xlsx': 'excel',
            'scv': 'csv',
            'csv': 'csv',
            'txt': 'text',
            'json': 'json',
            'parquet': 'parquet',
            'html': 'html',
            'markdown': 'md',
            'tsv': 'tsv',
            'clipboard': 'clipboard'
        }
        
        format_type = format_map.get(args.format, 'excel') if args.format else 'excel'
        
        if format_type == 'clipboard':
            output_path = None
        else:
            if args.output:
                output_path = args.output
            else:
                ext_map = {
                    'excel': 'xlsx',
                    'csv': 'csv',
                    'text': 'txt',
                    'json': 'json',
                    'parquet': 'parquet',
                    'html': 'html',
                    'md': 'md',
                    'tsv': 'tsv'
                }
                ext = ext_map.get(format_type, 'xlsx')
                output_path = str(input_path.parent / f"pdf_export.{ext}")
        
        try:
            scan_and_export(
                input_path=str(input_path),
                output_path=output_path,
                format=format_type,
                columns=columns
            )
        except Exception as e:
            print(f"Ошибка: {e}")

    elif args.action == "index":
        try:
            normalizer = DirectoryNormalizer(args.input)
            result = normalizer.normalize_structure()
        except Exception as e:
            index_parser.error(str(e))

   
    elif args.action == "patch":
        input_path = args.input
        output_dir = args.output if args.output else None
        mode = args.mode
        
        if not os.path.exists(input_path):
            patch_parser.error(f"Ошибка: Путь '{input_path}' не существует")
        
        target_codes = [mode]
        
        if os.path.isfile(input_path) and input_path.lower().endswith('.pdf'):
            created_files = process_single_pdf_file(input_path, target_codes, output_dir)
            if created_files:
                print(f"Создано файлов: {len(created_files)}")
                for f in created_files:
                    print(f"  {f}")
            else:
                print(f"Штрихкод {mode} не найден")
        
        elif os.path.isdir(input_path):
            result = process_directory(input_path, target_codes, output_dir)
            total_processed = 0
            total_created = 0
            
            for pdf_path, created_files in result["results"].items():
                if created_files:
                    total_processed += 1
                    total_created += len(created_files)
                    print(f"{Path(pdf_path).name}: создано {len(created_files)} файлов")
            
            print(f"\nОбработано PDF: {total_processed}")
            print(f"Создано файлов: {total_created}")
        else:
            patch_parser.error(f"Ошибка: '{input_path}' не является файлом PDF или папкой")


if __name__ == "__main__":
    main()