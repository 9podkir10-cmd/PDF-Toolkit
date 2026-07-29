import sqlite3
import os
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
import pandas as pd

class PDFDatabaseManager:
    def __init__(self, db_path="pdf_toolkit.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pdf_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                parent_directory TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                file_size INTEGER,
                date_created TEXT,
                date_modified TEXT,
                pages INTEGER,
                file_extension TEXT,
                file_name_hyperlink TEXT
            )
        ''')
        self.conn.commit()

    def scan_directory(self, directory_path, log_callback=None):
        def send_log(msg):
            if log_callback: log_callback(msg)

        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Директория {directory_path} не существует")

        cursor = self.conn.cursor()
        pdf_files = list(directory.rglob("*.pdf"))
        
        send_log(f"Найдено PDF файлов для обработки: {len(pdf_files)}")

        for pdf_path in pdf_files:
            try:
                doc = fitz.open(pdf_path)
                pages = len(doc)
                doc.close()

                stat = pdf_path.stat()
                file_size = stat.st_size
                date_created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                date_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

                parent_dir = str(pdf_path.parent)
                file_name = pdf_path.name
                ext = pdf_path.suffix.lower()
                hyperlink = f'=HYPERLINK("{pdf_path}", "{file_name}")'

                cursor.execute('''
                    INSERT OR REPLACE INTO pdf_files (
                        file_name, parent_directory, file_path, file_size,
                        date_created, date_modified, pages, file_extension,
                        file_name_hyperlink
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (file_name, parent_dir, str(pdf_path), file_size,
                      date_created, date_modified, pages, ext, hyperlink))
                send_log(f"Добавлен в БД: {file_name}")
            except Exception as e:
                send_log(f"Ошибка при обработке {pdf_path.name}: {e}")

        self.conn.commit()
        send_log(f"Успешно завершено! Обработано файлов: {len(pdf_files)}")

    def get_all_records(self, columns=None):
        if columns is None:
            columns = ['id', 'file_name', 'parent_directory', 'file_path',
                       'file_size', 'date_created', 'date_modified',
                       'pages', 'file_extension', 'file_name_hyperlink']
        cols_str = ", ".join(columns)
        query = f"SELECT {cols_str} FROM pdf_files ORDER BY file_name"
        return pd.read_sql_query(query, self.conn)

    def close(self):
        if self.conn:
            self.conn.close()

class ExcelExporter:
    def __init__(self, db_path="pdf_toolkit.db"):
        self.db_path = db_path

    def export_to_excel(self, columns, output_path, log_callback=None):
        try:
            manager = PDFDatabaseManager(self.db_path)
            df = manager.get_all_records(columns)
            manager.close()

            if df.empty:
                if log_callback: log_callback("Ошибка: Нет данных в БД для экспорта.")
                return False

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='PDF_List')

            if log_callback: log_callback(f"Экспорт успешно выполнен в: {output_path}")
            return True
        except Exception as e:
            if log_callback: log_callback(f"Ошибка при экспорте: {e}")
            return False