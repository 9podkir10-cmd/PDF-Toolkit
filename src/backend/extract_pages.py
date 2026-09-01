import pymupdf
from pathlib import Path

def extract_pages(pdf_path, output_dir=None, mode='first', value=None, start=None, end=None, log_callback=None):
    def log(message):
        if log_callback:
            log_callback(message)

    try:
        with pymupdf.open(pdf_path) as pdf_document:
            total_pages = len(pdf_document)

            if mode == 'first':
                if value is None or value <= 0:
                    raise ValueError("Укажите положительное число страниц.")
                if value > total_pages:
                    raise ValueError(f"Запрошено {value} стр., но в файле всего {total_pages}.")
                start_page = 0
                end_page = value - 1
                suffix = f"first_{value}_pages"
            elif mode == 'last':
                if value is None or value <= 0:
                    raise ValueError("Укажите положительное число страниц.")
                if value > total_pages:
                    raise ValueError(f"Запрошено {value} стр., но в файле всего {total_pages}.")
                start_page = total_pages - value
                end_page = total_pages - 1
                suffix = f"last_{value}_pages"
            elif mode == 'range':
                if start is None or end is None:
                    raise ValueError("Укажите начальную и конечную страницу.")
                if start < 1 or end > total_pages or start > end:
                    raise ValueError(f"Некорректный диапазон. Допустимые страницы в файле: 1..{total_pages}")
                start_page = start - 1
                end_page = end - 1
                suffix = f"pages_{start}-{end}"
            else:
                raise ValueError("Неизвестный режим работы.")

            new_pdf = pymupdf.open()
            try:
                new_pdf.insert_pdf(pdf_document, from_page=start_page, to_page=end_page)

                if output_dir is None:
                    output_dir = Path(pdf_path).parent
                else:
                    output_dir = Path(output_dir)

                output_dir.mkdir(parents=True, exist_ok=True)

                original_name = Path(pdf_path).stem
                output_path = output_dir / f"{original_name}_{suffix}.pdf"

                new_pdf.save(str(output_path))
                log(f"Сохранено: {output_path}")
                return output_path
            finally:
                new_pdf.close()

    except Exception as e:
        raise RuntimeError(f"Ошибка при обработке {Path(pdf_path).name}: {e}")

def process_all_pdfs(directory, output_base_dir=None, mode='first', value=None,
                     start=None, end=None, log_callback=None):
    root = Path(directory).resolve()
    output_root = Path(output_base_dir).resolve() if output_base_dir else None

    pdf_files = []
    for p in root.rglob("*.pdf", case_sensitive=False):
        if not p.is_file():
            continue

        if output_root:
            try:
                p.relative_to(output_root)
                continue 
            except ValueError:
                pass

        pdf_files.append(p)
    pdf_files.sort()

    if not pdf_files:
        if log_callback:
            log_callback("PDF файлы в указанной директории не найдены.")
        return []

    successful_files = []
    for pdf_path in pdf_files:
        if output_root:
            relative_parent = pdf_path.parent.relative_to(root)
            output_dir = output_root / relative_parent
        else:
            output_dir = pdf_path.parent

        try:
            out_file = extract_pages(str(pdf_path), output_dir, mode, value, start, end, log_callback)
            if out_file:
                successful_files.append(out_file)
        except Exception as e:
            if log_callback:
                log_callback(str(e))
    return successful_files