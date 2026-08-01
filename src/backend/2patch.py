import os
import sys
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

import fitz
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol

NUM_WORKERS = 6
ZOOM_LEVEL = 3.0

def check_code39_patch2_on_page(page_data):
    try:
        page_bytes, page_num, pdf_path = page_data
        
        doc = fitz.open("pdf", page_bytes)
        if len(doc) == 0:
            return (pdf_path, page_num, False)
        
        page = doc[0]
        
        mat = fitz.Matrix(ZOOM_LEVEL, ZOOM_LEVEL)
        pix = page.get_pixmap(matrix=mat)
        
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)
        
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        barcodes = decode(
            Image.fromarray(enhanced),
            symbols=[ZBarSymbol.CODE39]
        )
        
        doc.close()
        
        for barcode in barcodes:
            try:
                barcode_data = barcode.data.decode('utf-8').strip()
                if barcode_data == "PATCH2":
                    return (pdf_path, page_num, True)
                elif barcode_data.replace(" ", "").upper() == "PATCH2":
                    return (pdf_path, page_num, True)
            except:
                continue
        
        return (pdf_path, page_num, False)
        
    except Exception:
        return (pdf_path, page_num, False)

def find_code39_patch2_pages_parallel(pdf_path):
    print(f"\nАнализируем файл: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"Всего страниц: {total_pages}")
    except Exception as e:
        print(f"Ошибка при открытии PDF: {e}")
        return pdf_path, []
    
    print("Поиск штрих-кодов Code39 'PATCH2'...")
    
    page_data_list = []
    for page_num in range(total_pages):
        single_page_doc = fitz.open()
        single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        page_bytes = single_page_doc.write()
        single_page_doc.close()
        page_data_list.append((page_bytes, page_num, pdf_path))
    
    doc.close()
    
    barcode_pages = []
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_page = {
            executor.submit(check_code39_patch2_on_page, page_data): page_data[1]
            for page_data in page_data_list
        }
        
        processed = 0
        for future in as_completed(future_to_page):
            file_path, page_num, has_barcode = future.result()
            processed += 1
            
            progress = processed / total_pages * 100
            bar_length = 30
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"\r  [{bar}] {progress:.1f}% | Страница {page_num + 1}/{total_pages}", end="")
            
            if has_barcode:
                barcode_pages.append(page_num)
                print(f"\n  Страница {page_num + 1}: НАЙДЕН Code39 'PATCH2'")
    
    elapsed_time = time.time() - start_time
    print(f"\nВремя обработки: {elapsed_time:.1f} секунд")
    
    barcode_pages.sort()
    
    print(f"Найдено разделителей: {len(barcode_pages)}")
    if barcode_pages:
        page_numbers = [p + 1 for p in barcode_pages]
        print(f"Страницы: {page_numbers}")
    
    return pdf_path, barcode_pages

def split_pdf_by_code39(pdf_path, barcode_pages, output_dir=None):
    if not barcode_pages:
        print("Нет страниц со штрих-кодом Code39 'PATCH2' для разделения")
        return []
    
    pdf_file = Path(pdf_path)
    if output_dir is None:
        output_dir = pdf_file.parent / f"{pdf_file.stem}_split"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Сохраняем результаты в: {output_dir}")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    barcode_pages.sort()
    
    created_files = []
    part_number = 1
    start_page = 0
    
    all_separators = barcode_pages + [total_pages]
    
    print("Начинаем разделение...")
    
    for separator in all_separators:
        if separator <= start_page:
            continue
        
        new_doc = fitz.open()
        
        for page_num in range(start_page, separator):
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        output_filename = output_dir / f"{pdf_file.stem}_part{part_number}.pdf"
        new_doc.save(str(output_filename))
        new_doc.close()
        
        page_count = separator - start_page
        print(f"Часть {part_number}: страницы {start_page + 1}-{separator} ({page_count} стр.)")
        
        created_files.append(str(output_filename))
        
        part_number += 1
        start_page = separator + 1
    
    doc.close()
    
    print(f"Разделение завершено!")
    print(f"Создано файлов: {len(created_files)}")
    
    return created_files

def process_single_pdf_file(pdf_path, auto_mode=False):
    """Обработка одного PDF файла"""
    print("\n" + "=" * 80)
    print(f"ОБРАБОТКА ФАЙЛА: {pdf_path}")
    print("=" * 80)
    
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Файл не найден: {pdf_path}")
        return []
    
    if not pdf_file.is_file():
        print(f"Это не файл: {pdf_path}")
        return []
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"Файл должен быть в формате PDF")
        return []
    
    print(f"Файл найден: {pdf_path}")
    
    print("\n" + "-" * 80)
    print(f"Параметры обработки:")
    print(f"   Процессы: {NUM_WORKERS}")
    print(f"   Ищем: Code39 с данными 'PATCH2'")
    
    print("\n" + "-" * 80)
    file_path, barcode_pages = find_code39_patch2_pages_parallel(pdf_path)
    
    if not barcode_pages:
        print("\nШтрих-коды Code39 'PATCH2' не найдены. Разделение невозможно.")
        return []
    
    print("\n" + "-" * 80)
    print("План разделения:")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    start_page = 0
    part_num = 1
    
    for separator in barcode_pages:
        if separator > start_page:
            page_count = separator - start_page
            print(f"  Часть {part_num}: страницы {start_page + 1}-{separator} ({page_count} стр.)")
            part_num += 1
        start_page = separator + 1
    
    if start_page < total_pages:
        page_count = total_pages - start_page
        print(f"  Часть {part_num}: страницы {start_page + 1}-{total_pages} ({page_count} стр.)")
    
    print(f"\nСтраницы со штрих-кодом Code39 'PATCH2' будут удалены.")
    
    # В автоматическом режиме пропускаем подтверждение
    if not auto_mode:
        confirm = input("\nПродолжить разделение? (y/n): ").strip().lower()
        if confirm not in ['y', 'д', 'yes']:
            print("Операция отменена.")
            return []
    
    print("\n" + "-" * 80)
    created_files = split_pdf_by_code39(pdf_path, barcode_pages)
    
    if created_files:
        print("\n" + "=" * 80)
        print("Созданные файлы:")
        total_size = 0
        for i, file_path in enumerate(created_files, 1):
            file_size = Path(file_path).stat().st_size / 1024
            total_size += file_size
            print(f"  {i}. {Path(file_path).name} ({file_size:.1f} KB)")
        
        print(f"\nИтог: {len(created_files)} файлов, общий размер: {total_size:.1f} KB")
    
    return created_files

def find_pdf_files(directory):
    """Рекурсивный поиск PDF файлов в директории"""
    pdf_files = []
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Директория не найдена: {directory}")
        return []
    
    print(f"\nПоиск PDF файлов в: {directory}")
    print("Рекурсивный обход директорий...")
    
    # Используем словарь для хранения уникальных путей (решает проблему с дублированием)
    unique_pdf_files = {}
    
    # Рекурсивно ищем все PDF файлы
    for pdf_file in directory.rglob('*'):
        if pdf_file.is_file() and pdf_file.suffix.lower() == '.pdf':
            # Используем абсолютный путь как ключ для уникальности
            abs_path = str(pdf_file.absolute())
            unique_pdf_files[abs_path] = str(pdf_file)
    
    pdf_files = list(unique_pdf_files.values())
    
    print(f"\nНайдено уникальных PDF файлов: {len(pdf_files)}")
    
    if pdf_files:
        print("\nНайденные файлы:")
        for i, pdf_file in enumerate(pdf_files[:20], 1):  # Показываем первые 20 файлов
            print(f"  {i}. {pdf_file}")
        
        if len(pdf_files) > 20:
            print(f"  ... и еще {len(pdf_files) - 20} файлов")
    
    return pdf_files

def process_directory():
    """Обработка всех PDF файлов в директории"""
    print("=" * 80)
    print("      Code39 'PATCH2'")
    print("=" * 80)
    
    # Запрос пути к директории
    while True:
        dir_path = input("\nВведите путь к директории (или нажмите Enter для текущей директории): ").strip()
        
        if dir_path.startswith(('"', "'")) and dir_path.endswith(('"', "'")):
            dir_path = dir_path[1:-1]
        
        # Если пустая строка - используем текущую директорию
        if not dir_path:
            dir_path = "."
            print(f"Используется текущая директория: {Path.cwd()}")
        
        dir_path_obj = Path(dir_path)
        
        if not dir_path_obj.exists():
            print(f"Директория не найдена: {dir_path}")
            continue
        
        if not dir_path_obj.is_dir():
            print(f"Это не директория: {dir_path}")
            continue
        
        break
    
    pdf_files = find_pdf_files(dir_path)
    
    if not pdf_files:
        print("\nPDF файлы не найдены.")
        input("\nНажмите Enter для выхода...")
        return
    
    print("\n" + "-" * 80)
    print("РЕЖИМ ОБРАБОТКИ:")
    print("  Будет выполнена автоматическая обработка ВСЕХ найденных PDF файлов.")
    print(f"  Всего файлов для обработки: {len(pdf_files)}")
    
    confirm = input("\nНачать автоматическую обработку всех файлов? (y/n): ").strip().lower()
    if confirm not in ['y', 'д', 'yes']:
        print("Операция отменена.")
        input("\nНажмите Enter для выхода...")
        return
    
    results = {}
    print("\n" + "=" * 80)
    print("НАЧАЛО АВТОМАТИЧЕСКОЙ ОБРАБОТКИ")
    print("=" * 80)
    
    start_total_time = time.time()
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n\n{'#' * 80}")
        print(f"ФАЙЛ {i} из {len(pdf_files)}: {pdf_file}")
        print('#' * 80)
        
        try:
            created_files = process_single_pdf_file(pdf_file, auto_mode=True)
            results[pdf_file] = created_files if created_files else []
        except Exception as e:
            print(f"Ошибка при обработке файла {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
            results[pdf_file] = []
    
    total_elapsed_time = time.time() - start_total_time
    
    # Вывод итоговой статистики
    print_summary(results, total_elapsed_time)
    
    input("\nНажмите Enter для выхода...")

def print_summary(results, total_time):
    """Вывод итоговой статистики"""
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)
    
    total_processed = len(results)
    total_with_barcodes = sum(1 for files in results.values() if files)
    total_created = sum(len(files) for files in results.values())
    
    print(f"\nОбщее время обработки: {total_time:.1f} секунд")
    print(f"Обработано файлов: {total_processed}")
    print(f"Файлов со штрих-кодами: {total_with_barcodes}")
    print(f"Создано новых файлов: {total_created}")
    
    if total_with_barcodes > 0:
        print("\nДетали по обработанным файлам:")
        print("-" * 40)
        
        for pdf_file, created_files in results.items():
            if created_files:
                file_name = Path(pdf_file).name
                created_count = len(created_files)
                print(f"  {file_name}:")
                print(f"    Создано файлов: {created_count}")
                for i, created_file in enumerate(created_files[:3], 1):  # Показываем первые 3 созданных файла
                    print(f"      {i}. {Path(created_file).name}")
                if created_count > 3:
                    print(f"      ... и еще {created_count - 3} файлов")
                print()
    
    # Файлы без штрих-кодов
    files_without_barcodes = [f for f, files in results.items() if not files]
    if files_without_barcodes:
        print(f"\nФайлы без штрих-кодов Code39 'PATCH2' ({len(files_without_barcodes)}):")
        for pdf_file in files_without_barcodes[:10]:  # Показываем первые 10
            print(f"  • {Path(pdf_file).name}")
        if len(files_without_barcodes) > 10:
            print(f"  ... и еще {len(files_without_barcodes) - 10} файлов")

def check_dependencies():
    """Проверка необходимых зависимостей"""
    print("Проверка зависимостей...")
    
    dependencies = {
        'PyMuPDF': 'fitz',
        'OpenCV': 'cv2',
        'pyzbar': 'pyzbar',
        'NumPy': 'numpy',
        'Pillow': 'PIL.Image'
    }
    
    missing = []
    
    for lib_name, import_name in dependencies.items():
        try:
            if import_name == 'fitz':
                import fitz
            elif import_name == 'cv2':
                import cv2
            elif import_name == 'pyzbar':
                import pyzbar
            elif import_name == 'numpy':
                import numpy
            elif import_name == 'PIL.Image':
                from PIL import Image
            print(f"  ✓ {lib_name}")
        except ImportError:
            print(f"  ✗ {lib_name}")
            missing.append(lib_name)
    
    if missing:
        print(f"\nОтсутствуют зависимости: {', '.join(missing)}")
        install_all = input("\nУстановить все зависимости? (y/n): ").strip().lower()
        
        if install_all in ['y', 'д']:
            install_commands = {
                'PyMuPDF': 'PyMuPDF',
                'OpenCV': 'opencv-python',
                'pyzbar': 'pyzbar',
                'NumPy': 'numpy',
                'Pillow': 'Pillow'
            }
            
            for missing_lib in missing:
                cmd = install_commands.get(missing_lib)
                if cmd:
                    print(f"Устанавливаю {missing_lib}...")
                    os.system(f"pip install {cmd}")
            
            print("\nЗависимости установлены. Перезапустите программу.")
        else:
            print("\nУстановите зависимости вручную:")
            print("pip install PyMuPDF opencv-python pyzbar numpy Pillow")
        
        return False
    
    print("\nВсе зависимости установлены!")
    return True

def main():
    """Основная функция программы"""
    print("=" * 80)
    
    if not check_dependencies():
        input("\nНажмите Enter для выхода...")
        return
    
    print(f"\nДоступно CPU ядер: {cpu_count()}")
    print(f"Используется процессов: {NUM_WORKERS}")
    
    try:
        process_directory()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем.")
        input("\nНажмите Enter для выхода...")
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()