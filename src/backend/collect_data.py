import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import fitz


def extract_metadata(pdf_path: Path, record_id: int = None) -> dict:
    doc = fitz.open(pdf_path)
    pages = len(doc)
    doc.close()
    
    stat = pdf_path.stat()
    return {
        'id': record_id,        
        'file_name': pdf_path.name,
        'parent_directory': str(pdf_path.parent),
        'file_path': str(pdf_path),
        'file_size': stat.st_size,
        'date_created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'date_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'pages': pages,
        'file_extension': pdf_path.suffix.lower(),
        'file_name_hyperlink': f'=HYPERLINK("{pdf_path}", "{pdf_path.name}")'
    }


def scan_and_export(
    input_path: str,
    output_path: Optional[str] = None,
    format: str = 'excel',
    columns: Optional[List[str]] = None
) -> None:
    input_path = Path(input_path)
    
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = list(input_path.rglob("*.pdf"))
    else:
        raise ValueError("Путь должен быть папкой или PDF файлом")
    
    if not pdf_files:
        print("PDF файлы не найдены")
        return
    
    records = []
    for i, pdf in enumerate(pdf_files, 1):
        try:
            records.append(extract_metadata(pdf, i))
        except Exception as e:
            print(f"Ошибка {pdf.name}: {e}")
    
    if not records:
        print("Нет данных для экспорта")
        return
    
    df = pd.DataFrame(records)
    
    if columns:
        available = df.columns.tolist()
        valid_columns = [col for col in columns if col in available]
        if valid_columns:
            df = df[valid_columns]
        else:
            print("Указанные колонки не найдены, экспортируются все")
    
    if output_path:
        output_path = Path(output_path)

        if output_path.is_dir():
            output_path = output_path / f"pdf_export.{format}"

        output_path = str(output_path)
    else:
        output_path = str(input_path.parent / f"pdf_export.{format}")
    
    exporters = {
        'xlsx': lambda: df.to_excel(output_path, index=False, engine='openpyxl'),
        'csv': lambda: df.to_csv(output_path, index=False, encoding='utf-8-sig'),
        'json': lambda: df.to_json(output_path, orient='records', force_ascii=False, indent=2),
        'xml': lambda: df.to_xml(output_path, index=False, pretty_print=True),
        'html': lambda: df.to_html(output_path, index=False),
        'markdown': lambda: df.to_markdown(output_path, index=False),
        'txt': lambda: df.to_string(output_path, index=False),
        'tsv': lambda: df.to_csv(output_path, sep='\t', index=False, encoding='utf-8-sig'),
        'clipboard': lambda: df.to_clipboard(index=False, excel=True),
    }
    
    if format.lower() not in exporters:
        raise ValueError(f"Неподдерживаемый формат: {format}")
    
    exporters[format.lower()]()
    print(f"Экспортировано {len(df)} записей в {output_path}")