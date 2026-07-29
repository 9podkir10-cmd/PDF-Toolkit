import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import threading
from pathlib import Path
from datetime import datetime

from backend.extract_pages import extract_pages, process_all_pdfs
from backend.data import PDFDatabaseManager, ExcelExporter
from backend.clear_path import DirectoryNormalizer
from backend.ocr import RegionExtractor


def get_app_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


class PDFToolkitGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Toolkit")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)
        self.root.configure(bg='#f0f0f0')

        self.app_dir = get_app_directory()
        self.current_pdf_pages = []
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()

        self.main_container = tk.Frame(self.root, bg='#f0f0f0')
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)

        self._create_sidebar()
        self._create_content_area()
        self._create_bottom_bar()

        self.frames = {}
        self._create_all_frames()
        self.show_frame("index")

        self._create_copyright()

    def _configure_styles(self):
        self.style.configure('Sidebar.TButton', font=('Segoe UI', 10),
                            padding=10, anchor='w', background='#ffffff')
        self.style.configure('Active.TButton', font=('Segoe UI', 10, 'bold'),
                            padding=10, anchor='w', background='#e3f2fd')
        self.style.configure('Header.TLabel', font=('Segoe UI', 13, 'bold'),
                            foreground='#1565c0')
        self.style.configure('Status.TLabel', font=('Segoe UI', 9))
        self.style.configure('Success.TLabel', foreground='#2e7d32')
        self.style.configure('Error.TLabel', foreground='#c62828')

    def _create_sidebar(self):
        sidebar = tk.Frame(self.main_container, bg='#ffffff', width=200,
                          relief='raised', bd=1)
        sidebar.pack(side='left', fill='y', padx=(0, 10))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="PDF Toolkit", font=('Segoe UI', 14, 'bold'),
                bg='#ffffff', fg='#1565c0').pack(pady=(20, 15))

        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', padx=10, pady=(0, 10))

        self.sidebar_buttons = {}
        modules = [
            ("index", "Индексация"),
            ("extract", "Извлечение текста"),
            ("pages", "Извлечение страниц"),
            ("export", "Экспорт"),
            ("normalize", "Очистка"),
            ("stats", "Статистика")
        ]

        for key, label in modules:
            btn = tk.Button(sidebar, text=label, font=('Segoe UI', 10),
                           bg='#ffffff', fg='#333333', bd=0, anchor='w',
                           padx=15, pady=10, relief='flat',
                           activebackground='#e3f2fd',
                           activeforeground='#1565c0',
                           command=lambda k=key: self.show_frame(k))
            btn.pack(fill='x', pady=1)
            self.sidebar_buttons[key] = btn

        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', padx=10, pady=10)
        tk.Label(sidebar, text="v2.0", font=('Segoe UI', 8),
                bg='#ffffff', fg='#999999').pack(side='bottom', pady=10)

    def _create_content_area(self):
        self.content_area = tk.Frame(self.main_container, bg='#f5f5f5',
                                     relief='flat', bd=1)
        self.content_area.pack(side='left', fill='both', expand=True)

    def _create_bottom_bar(self):
        bottom_frame = tk.Frame(self.content_area, bg='#f5f5f5', height=50)
        bottom_frame.pack(side='bottom', fill='x')
        bottom_frame.pack_propagate(False)

        dir_frame = tk.Frame(bottom_frame, bg='#f5f5f5')
        dir_frame.pack(fill='x', padx=15, pady=(8, 0))

        tk.Label(dir_frame, text="Путь к директории:", font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555555').pack(side='left')

        self.path_entry = tk.Entry(dir_frame, font=('Segoe UI', 9),
                                   bg='white', fg='#333333',
                                   relief='solid', bd=1)
        self.path_entry.pack(side='left', fill='x', expand=True, padx=(10, 10), ipady=3)

        self.browse_btn = tk.Button(dir_frame, text="Обзор",
                                    font=('Segoe UI', 9),
                                    bg='#1565c0', fg='white',
                                    relief='flat', padx=15, pady=3,
                                    cursor='hand2',
                                    command=self._browse_path)
        self.browse_btn.pack(side='right')

        status_frame = tk.Frame(bottom_frame, bg='#f5f5f5')
        status_frame.pack(fill='x', padx=15, pady=(5, 8))

        self.status_label = tk.Label(status_frame, text="Готов к работе",
                                     font=('Segoe UI', 9),
                                     bg='#f5f5f5', fg='#555555',
                                     anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True)

        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate',
                                            length=150)
        self.progress_bar.pack(side='right', padx=(10, 0))

    def _create_copyright(self):
        copyright_frame = tk.Frame(self.root, bg='#f0f0f0')
        copyright_frame.pack(side='bottom', fill='x', pady=(0, 5))
        tk.Label(copyright_frame, text="PDF Toolkit v0.1.0  2025  Все права защищены",
                font=('Segoe UI', 8), bg='#f0f0f0', fg='#999999').pack()

    def _browse_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, directory)

    def _create_all_frames(self):
        frame_classes = [
            ("index", self._create_index_frame),
            ("extract", self._create_extract_frame),
            ("pages", self._create_pages_frame),
            ("export", self._create_export_frame),
            ("normalize", self._create_normalize_frame),
            ("stats", self._create_stats_frame)
        ]

        for key, creator in frame_classes:
            frame = creator(self.content_area)
            frame.pack(fill='both', expand=True)
            frame.pack_forget()
            self.frames[key] = frame

    def show_frame(self, name):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill='both', expand=True)

        for key, btn in self.sidebar_buttons.items():
            btn.config(bg='#ffffff', fg='#333333')
        if name in self.sidebar_buttons:
            self.sidebar_buttons[name].config(bg='#e3f2fd', fg='#1565c0')

    def set_status(self, message, is_error=False):
        color = '#c62828' if is_error else '#2e7d32'
        self.status_label.config(text=message, fg=color)
        self.root.update_idletasks()

    def start_progress(self):
        self.progress_bar.start()

    def stop_progress(self):
        self.progress_bar.stop()

    def _create_index_frame(self, parent):
        frame = tk.Frame(parent, bg='#f5f5f5')

        tk.Label(frame, text="Индексация PDF файлов", font=('Segoe UI', 14, 'bold'),
                bg='#f5f5f5', fg='#1565c0').pack(anchor='w', pady=(15, 15))

        dir_frame = tk.LabelFrame(frame, text="Настройки индексации",
                                  font=('Segoe UI', 10, 'bold'),
                                  bg='#f5f5f5', fg='#333333')
        dir_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.opening_entry = self._create_marker_row(dir_frame, "Открывающий элемент (0 - с начала):", "open")
        self.closing_entry = self._create_marker_row(dir_frame, "Закрывающий элемент (0 - до конца):", "close")

        sep_frame = tk.Frame(dir_frame, bg='#f5f5f5')
        sep_frame.pack(fill='x', pady=5, padx=5)
        self.has_separator_var = tk.BooleanVar()
        tk.Checkbutton(sep_frame, text="Есть разделитель",
                       variable=self.has_separator_var,
                       bg='#f5f5f5', font=('Segoe UI', 9),
                       command=self._toggle_separator).pack(side='left')
        self.separator_entry = tk.Entry(sep_frame, width=30, state='disabled')
        self.separator_entry.pack(side='left', padx=10)

        mode_frame = tk.Frame(dir_frame, bg='#f5f5f5')
        mode_frame.pack(fill='x', pady=5, padx=5)

        self.mode_var = tk.StringVar(value="rename")
        tk.Radiobutton(mode_frame, text="Переименовать папки",
                       variable=self.mode_var, value="rename",
                       bg='#f5f5f5', font=('Segoe UI', 9)).pack(anchor='w')
        tk.Radiobutton(mode_frame, text="Извлечь текст в файл",
                       variable=self.mode_var, value="extract",
                       bg='#f5f5f5', font=('Segoe UI', 9)).pack(anchor='w')

        self.rename_pdf_var = tk.BooleanVar(value=True)
        tk.Checkbutton(mode_frame, text="Переименовывать PDF-файлы",
                       variable=self.rename_pdf_var,
                       bg='#f5f5f5', font=('Segoe UI', 9)).pack(anchor='w', padx=20)

        btn_frame = tk.Frame(frame, bg='#f5f5f5')
        btn_frame.pack(fill='x', pady=10, padx=10)

        tk.Button(btn_frame, text="Запустить индексацию",
                 font=('Segoe UI', 10, 'bold'),
                 bg='#1565c0', fg='white', relief='flat',
                 padx=20, pady=8, cursor='hand2',
                 command=self._run_indexing).pack(side='left')

        self.index_result_label = tk.Label(frame, text="",
                                          font=('Segoe UI', 9),
                                          bg='#f5f5f5', fg='#2e7d32')
        self.index_result_label.pack(anchor='w', pady=5, padx=10)

        return frame

    def _create_marker_row(self, parent, label, key):
        row = tk.Frame(parent, bg='#f5f5f5')
        row.pack(fill='x', pady=5, padx=5)

        tk.Label(row, text=label, font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555555', width=30).pack(side='left')

        entry = tk.Entry(row, width=30, font=('Segoe UI', 9),
                        bg='white', fg='#333333', relief='solid', bd=1)
        entry.pack(side='left', padx=5)

        var = tk.BooleanVar()
        tk.Checkbutton(row, text="Включать", variable=var,
                      bg='#f5f5f5', font=('Segoe UI', 9)).pack(side='left', padx=5)

        setattr(self, f"include_{key}_var", var)
        return entry

    def _toggle_separator(self):
        if self.has_separator_var.get():
            self.separator_entry.config(state='normal')
        else:
            self.separator_entry.config(state='disabled')

    def _run_indexing(self):
        directory = self.path_entry.get().strip()
        if not directory or not os.path.exists(directory):
            messagebox.showerror("Ошибка", "Укажите существующую директорию через поле 'Путь к директории'")
            return

        config = {
            'opening_element': self.opening_entry.get().strip() or "0",
            'include_opening': self.include_open_var.get(),
            'closing_element': self.closing_entry.get().strip() or "0",
            'include_closing': self.include_close_var.get(),
            'separator_element': self.separator_entry.get().strip() if self.has_separator_var.get() else None,
            'mode': 'rename_folders' if self.mode_var.get() == "rename" else 'extract_text'
        }

        def run():
            try:
                self.start_progress()
                self.set_status("Запуск индексации...")

                from backend.clear_path import process_pdf_folder, process_pdf_for_text_extraction

                output_path = self.app_dir / "output"
                work_path = output_path / "work"
                work_path.mkdir(parents=True, exist_ok=True)

                results = []
                errors = []

                if config['mode'] == 'rename_folders':
                    for folder in work_path.iterdir():
                        if folder.is_dir():
                            process_pdf_folder(folder, config, results, errors,
                                             self.rename_pdf_var.get())
                else:
                    pdf_files = list(work_path.rglob("*.pdf"))
                    for pdf_file in pdf_files:
                        process_pdf_for_text_extraction(pdf_file, config, results, errors)

                итоги_path = output_path / "Итоги"
                итоги_path.mkdir(exist_ok=True)

                with open(итоги_path / "results.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

                if errors:
                    with open(итоги_path / "incorrect.txt", "w", encoding="utf-8") as f:
                        f.write("\n".join(errors))

                self.stop_progress()
                success_count = len([r for r in results if r.get('status') == 'success'])
                self.set_status(f"Индексация завершена. Успешно: {success_count}")
                self.index_result_label.config(text=f"Результаты сохранены в: {итоги_path}")

            except Exception as e:
                self.stop_progress()
                self.set_status(f"Ошибка: {e}", is_error=True)
                messagebox.showerror("Ошибка", str(e))

        threading.Thread(target=run, daemon=True).start()

    def _create_extract_frame(self, parent):
        frame = tk.Frame(parent, bg='#f5f5f5')

        tk.Label(frame, text="Извлечение текста из PDF", font=('Segoe UI', 14, 'bold'),
                bg='#f5f5f5', fg='#1565c0').pack(anchor='w', pady=(10, 10))

        top_frame = tk.Frame(frame, bg='#f5f5f5')
        top_frame.pack(fill='x', padx=10)

        left_panel = tk.Frame(top_frame, bg='#f5f5f5')
        left_panel.pack(side='left', fill='both', expand=True)

        options_frame = tk.LabelFrame(left_panel, text="Параметры извлечения",
                                     font=('Segoe UI', 10, 'bold'),
                                     bg='#f5f5f5', fg='#333333')
        options_frame.pack(fill='x', pady=(0, 5))

        self.extract_scope = tk.StringVar(value="file")

        scope_frame = tk.Frame(options_frame, bg='#f5f5f5')
        scope_frame.pack(fill='x', padx=5, pady=3)
        tk.Radiobutton(scope_frame, text="Один файл", variable=self.extract_scope,
                      value="file", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_extract_source).pack(side='left', padx=5)
        tk.Radiobutton(scope_frame, text="Папка с файлами", variable=self.extract_scope,
                      value="folder", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_extract_source).pack(side='left', padx=5)

        self.extract_file_frame = tk.Frame(options_frame, bg='#f5f5f5')
        self.extract_file_frame.pack(fill='x', padx=20, pady=3)
        self.extract_file_var = tk.StringVar()
        self.extract_file_var.trace('w', self._on_pdf_file_selected)
        tk.Entry(self.extract_file_frame, textvariable=self.extract_file_var,
                font=('Segoe UI', 9), bg='white', relief='solid', bd=1).pack(
                side='left', fill='x', expand=True, padx=5)
        tk.Button(self.extract_file_frame, text="Обзор PDF",
                 font=('Segoe UI', 9), bg='#1565c0', fg='white',
                 relief='flat', padx=10, cursor='hand2',
                 command=lambda: self._browse_pdf_file(self.extract_file_var)).pack(
                 side='left', padx=5)

        self.extract_folder_frame = tk.Frame(options_frame, bg='#f5f5f5')
        self.extract_folder_frame.pack(fill='x', padx=20, pady=3)
        self.extract_folder_var = tk.StringVar()
        tk.Entry(self.extract_folder_frame, textvariable=self.extract_folder_var,
                font=('Segoe UI', 9), bg='white', relief='solid', bd=1).pack(
                side='left', fill='x', expand=True, padx=5)
        tk.Button(self.extract_folder_frame, text="Обзор папки",
                 font=('Segoe UI', 9), bg='#1565c0', fg='white',
                 relief='flat', padx=10, cursor='hand2',
                 command=lambda: self._browse_dir_var(self.extract_folder_var)).pack(
                 side='left', padx=5)
        self.extract_folder_frame.pack_forget()

        self.extract_mode_var = tk.StringVar(value="auto")
        mode_frame = tk.Frame(options_frame, bg='#f5f5f5')
        mode_frame.pack(fill='x', padx=5, pady=3)
        tk.Radiobutton(mode_frame, text="Автоматически", variable=self.extract_mode_var,
                      value="auto", bg='#f5f5f5', font=('Segoe UI', 9)).pack(
                      side='left', padx=10)
        tk.Radiobutton(mode_frame, text="Интерактивный", variable=self.extract_mode_var,
                      value="interactive", bg='#f5f5f5', font=('Segoe UI', 9)).pack(
                      side='left', padx=10)

        btn_frame = tk.Frame(options_frame, bg='#f5f5f5')
        btn_frame.pack(fill='x', pady=5)

        tk.Button(btn_frame, text="Извлечь текст",
                 font=('Segoe UI', 10, 'bold'),
                 bg='#1565c0', fg='white', relief='flat',
                 padx=20, pady=6, cursor='hand2',
                 command=self._run_extract).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Очистить выделение",
                 font=('Segoe UI', 9),
                 bg='#e0e0e0', fg='#333333', relief='flat',
                 padx=15, pady=6, cursor='hand2',
                 command=self._clear_selection).pack(side='left', padx=5)

        self.extract_result_label = tk.Label(options_frame, text="",
                                            font=('Segoe UI', 9),
                                            bg='#f5f5f5', fg='#2e7d32')
        self.extract_result_label.pack(anchor='w', pady=3, padx=10)

        preview_frame = tk.LabelFrame(top_frame, text="Предпросмотр PDF",
                                     font=('Segoe UI', 10, 'bold'),
                                     bg='#f5f5f5', fg='#333333')
        preview_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        nav_frame = tk.Frame(preview_frame, bg='#f5f5f5')
        nav_frame.pack(fill='x', pady=3)

        tk.Button(nav_frame, text="◀", font=('Segoe UI', 10),
                 bg='#e0e0e0', relief='flat', padx=10,
                 command=self._prev_page).pack(side='left', padx=2)

        self.page_label = tk.Label(nav_frame, text="Страница 1/1",
                                  font=('Segoe UI', 9),
                                  bg='#f5f5f5', fg='#555555')
        self.page_label.pack(side='left', padx=10)

        tk.Button(nav_frame, text="▶", font=('Segoe UI', 10),
                 bg='#e0e0e0', relief='flat', padx=10,
                 command=self._next_page).pack(side='left', padx=2)

        tk.Label(nav_frame, text="Масштаб:", font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555555').pack(side='left', padx=(20, 5))

        self.zoom_var = tk.StringVar(value="100%")
        zoom_entry = tk.Entry(nav_frame, textvariable=self.zoom_var,
                             width=6, font=('Segoe UI', 9),
                             bg='white', relief='solid', bd=1)
        zoom_entry.pack(side='left', padx=2)
        tk.Button(nav_frame, text="Применить", font=('Segoe UI', 8),
                 bg='#e0e0e0', relief='flat', padx=8,
                 command=self._apply_zoom).pack(side='left', padx=2)

        self.canvas_frame = tk.Frame(preview_frame, bg='white', relief='sunken', bd=1)
        self.canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.canvas.pack(fill='both', expand=True)

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        self.pdf_image = None
        self.current_page_image = None

        bottom_frame = tk.Frame(frame, bg='#f5f5f5', height=120)
        bottom_frame.pack(side='bottom', fill='x', padx=10, pady=(5, 10))

        tk.Label(bottom_frame, text="Результат распознавания:", font=('Segoe UI', 9, 'bold'),
                bg='#f5f5f5', fg='#555555').pack(anchor='w')

        self.extract_text_area = tk.Text(bottom_frame, height=5, wrap=tk.WORD,
                                        font=('Consolas', 9),
                                        bg='white', fg='#333333',
                                        relief='solid', bd=1)
        self.extract_text_area.pack(fill='both', expand=True)

        return frame

    def _toggle_extract_source(self):
        if self.extract_scope.get() == "file":
            self.extract_file_frame.pack(fill='x', padx=20, pady=3)
            self.extract_folder_frame.pack_forget()
        else:
            self.extract_folder_frame.pack(fill='x', padx=20, pady=3)
            self.extract_file_frame.pack_forget()
            self.current_pdf_pages = []
            self.canvas.delete("all")
            self.pdf_image = None

    def _browse_pdf_file(self, var):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            var.set(file_path)

    def _browse_dir_var(self, var):
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)

    def _on_pdf_file_selected(self, *args):
        pdf_path = self.extract_file_var.get().strip()
        if pdf_path and os.path.exists(pdf_path) and pdf_path.lower().endswith('.pdf'):
            self._load_pdf_preview(pdf_path)

    def _load_pdf_preview(self, pdf_path):
        try:
            from backend.ocr import PDFProcessor
            import cv2

            processor = PDFProcessor()
            images = processor.pdf_to_images(pdf_path, dpi=200)

            if not images:
                self.set_status("Не удалось загрузить PDF", is_error=True)
                return

            self.current_pdf_pages = images
            self.current_page_index = 0
            self.zoom_level = 1.0
            self.zoom_var.set("100%")
            self._display_current_page()

            self.set_status(f"Загружено PDF: {Path(pdf_path).name}, страниц: {len(images)}")

        except Exception as e:
            self.set_status(f"Ошибка загрузки PDF: {e}", is_error=True)
            self.current_pdf_pages = []

    def _display_current_page(self):
        if not self.current_pdf_pages:
            self.canvas.delete("all")
            self.page_label.config(text="Страница 0/0")
            return

        image = self.current_pdf_pages[self.current_page_index]
        self.current_page_image = image

        import cv2
        import numpy as np
        from PIL import Image, ImageTk

        h, w = image.shape[:2]
        display_w = int(w * self.zoom_level)
        display_h = int(h * self.zoom_level)

        if display_w > 800 or display_h > 600:
            scale_x = 800 / display_w
            scale_y = 600 / display_h
            scale = min(scale_x, scale_y, 1.0)
            display_w = int(display_w * scale)
            display_h = int(display_h * scale)

        resized = cv2.resize(image, (display_w, display_h), interpolation=cv2.INTER_LANCZOS4)

        if len(resized.shape) == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        pil_image = Image.fromarray(resized)
        self.tk_image = ImageTk.PhotoImage(pil_image)

        self.canvas.delete("all")
        self.canvas.config(width=display_w, height=display_h)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

        self.page_label.config(text=f"Страница {self.current_page_index + 1}/{len(self.current_pdf_pages)}")

        self.canvas.image_width = display_w
        self.canvas.image_height = display_h




    def _prev_page(self):
        if self.current_pdf_pages and self.current_page_index > 0:
            self.current_page_index -= 1
            self._display_current_page()

    def _next_page(self):
        if self.current_pdf_pages and self.current_page_index < len(self.current_pdf_pages) - 1:
            self.current_page_index += 1
            self._display_current_page()

    def _apply_zoom(self):
        try:
            zoom_str = self.zoom_var.get().replace('%', '')
            zoom = float(zoom_str) / 100
            if zoom < 0.1:
                zoom = 0.1
            if zoom > 3.0:
                zoom = 3.0
            self.zoom_level = zoom
            self.zoom_var.set(f"{int(zoom * 100)}%")
            self._display_current_page()
        except:
            self.zoom_var.set(f"{int(self.zoom_level * 100)}%")

    def _on_canvas_click(self, event):
        if not self.current_pdf_pages:
            return
        self.selection_start = (event.x, event.y)
        self.selection_end = None
        self.is_selecting = True

    def _on_canvas_drag(self, event):
        if not self.is_selecting or not self.current_pdf_pages:
            return

        self.canvas.delete("selection_rect")

        if self.selection_start:
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y

            self.canvas.create_rectangle(x1, y1, x2, y2,
                                        outline='#1565c0',
                                        width=2,
                                        fill='#1565c010',
                                        tags="selection_rect")

    def _on_canvas_release(self, event):
        if not self.is_selecting or not self.current_pdf_pages:
            return

        self.is_selecting = False
        self.selection_end = (event.x, event.y)

        if self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end

            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)

            if x2 - x1 > 10 and y2 - y1 > 10:
                self.set_status(f"Выбрана область: {x2-x1}x{y2-y1} пикселей")

                if self.extract_mode_var.get() == "interactive":
                    self._extract_from_selected_region(x1, y1, x2, y2)

    def _clear_selection(self):
        self.canvas.delete("selection_rect")
        self.selection_start = None
        self.selection_end = None
        self.set_status("Выделение очищено")

    def _extract_from_selected_region(self, x1, y1, x2, y2):
        if not self.current_pdf_pages:
            return

        pdf_path = self.extract_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            return

        image = self.current_pdf_pages[self.current_page_index]

        import cv2
        import numpy as np

        h, w = image.shape[:2]

        display_w = int(w * self.zoom_level)
        display_h = int(h * self.zoom_level)

        if display_w > 800 or display_h > 600:
            scale_x = 800 / display_w
            scale_y = 600 / display_h
            scale = min(scale_x, scale_y, 1.0)
            display_w = int(display_w * scale)
            display_h = int(display_h * scale)

        scale_x = w / display_w
        scale_y = h / display_h

        orig_x1 = int(x1 * scale_x)
        orig_y1 = int(y1 * scale_y)
        orig_x2 = int(x2 * scale_x)
        orig_y2 = int(y2 * scale_y)

        orig_x1 = max(0, orig_x1)
        orig_y1 = max(0, orig_y1)
        orig_x2 = min(w, orig_x2)
        orig_y2 = min(h, orig_y2)

        if orig_x2 - orig_x1 < 10 or orig_y2 - orig_y1 < 10:
            self.set_status("Выбранная область слишком мала", is_error=True)
            return

        cropped = image[orig_y1:orig_y2, orig_x1:orig_x2]

        try:
            from backend.ocr import PDFProcessor
            processor = PDFProcessor()
            text = processor.ocr.extract_text(cropped)

            self.extract_text_area.delete(1.0, tk.END)
            self.extract_text_area.insert(tk.END, text if text else "Текст не распознан")

            if text and text.strip():
                self.set_status("Текст извлечен из выбранной области")
            else:
                self.set_status("Не удалось распознать текст в выбранной области", is_error=True)

        except Exception as e:
            self.set_status(f"Ошибка распознавания: {e}", is_error=True)

    def _run_extract(self):
        source = self.extract_scope.get()
        source_path = self.extract_file_var.get().strip() if source == "file" else self.extract_folder_var.get().strip()

        if not source_path or not os.path.exists(source_path):
            messagebox.showerror("Ошибка", "Укажите существующий файл или папку")
            return

        mode = self.extract_mode_var.get()

        if source == "file" and mode == "interactive":
            if not self.current_pdf_pages:
                self._load_pdf_preview(source_path)
                if not self.current_pdf_pages:
                    return

            self.set_status("Выберите область на изображении для распознавания")
            return

        def run():
            try:
                self.start_progress()
                self.set_status("Извлечение текста...")
                self.extract_text_area.delete(1.0, tk.END)

                extractor = RegionExtractor()

                if source == "file":
                    result = extractor.extract(source_path, interactive=False)

                    self.extract_text_area.insert(tk.END, f"Файл: {Path(source_path).name}\n")
                    self.extract_text_area.insert(tk.END, f"Статус: {'УСПЕШНО' if result['success'] else 'НЕ УДАЛОСЬ'}\n")
                    self.extract_text_area.insert(tk.END, f"Метод: {result.get('method', 'unknown')}\n")
                    self.extract_text_area.insert(tk.END, "-"*50 + "\n")
                    if result['success'] and result['text']:
                        self.extract_text_area.insert(tk.END, result['text'])

                else:
                    results = extractor.extract_batch(source_path, interactive=False)
                    success = sum(1 for r in results if r['success'])

                    self.extract_text_area.insert(tk.END, f"ПАКЕТНАЯ ОБРАБОТКА\n")
                    self.extract_text_area.insert(tk.END, f"Всего файлов: {len(results)}\n")
                    self.extract_text_area.insert(tk.END, f"Успешно: {success}\n")
                    self.extract_text_area.insert(tk.END, "-"*50 + "\n\n")

                    for r in results[:10]:
                        status = "+" if r['success'] else "-"
                        self.extract_text_area.insert(tk.END, f"{status} {Path(r['pdf_path']).name}\n")

                    if len(results) > 10:
                        self.extract_text_area.insert(tk.END, f"\n... и еще {len(results) - 10} файлов")

                self.stop_progress()
                self.set_status("Извлечение завершено")

            except Exception as e:
                self.stop_progress()
                self.set_status(f"Ошибка: {e}", is_error=True)
                messagebox.showerror("Ошибка", str(e))

        threading.Thread(target=run, daemon=True).start()

    def _create_pages_frame(self, parent):
        frame = tk.Frame(parent, bg='#f5f5f5')

        tk.Label(frame, text="Извлечение страниц из PDF", font=('Segoe UI', 14, 'bold'),
                bg='#f5f5f5', fg='#1565c0').pack(anchor='w', pady=(15, 15))

        source_frame = tk.LabelFrame(frame, text="Источник",
                                    font=('Segoe UI', 10, 'bold'),
                                    bg='#f5f5f5', fg='#333333')
        source_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.pages_scope = tk.StringVar(value="file")
        tk.Radiobutton(source_frame, text="Один файл", variable=self.pages_scope,
                      value="file", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_pages_source).pack(anchor='w', padx=5)
        tk.Radiobutton(source_frame, text="Все файлы в папке", variable=self.pages_scope,
                      value="folder", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_pages_source).pack(anchor='w', padx=5)

        self.pages_file_frame = tk.Frame(source_frame, bg='#f5f5f5')
        self.pages_file_frame.pack(fill='x', padx=20, pady=5)
        self.pages_file_var = tk.StringVar()
        tk.Entry(self.pages_file_frame, textvariable=self.pages_file_var,
                font=('Segoe UI', 9), bg='white', relief='solid', bd=1).pack(
                side='left', fill='x', expand=True, padx=5)
        tk.Button(self.pages_file_frame, text="Обзор PDF",
                 font=('Segoe UI', 9), bg='#1565c0', fg='white',
                 relief='flat', padx=10, cursor='hand2',
                 command=lambda: self._browse_pdf_file(self.pages_file_var)).pack(
                 side='left', padx=5)

        self.pages_folder_frame = tk.Frame(source_frame, bg='#f5f5f5')
        self.pages_folder_frame.pack(fill='x', padx=20, pady=5)
        self.pages_folder_var = tk.StringVar()
        tk.Entry(self.pages_folder_frame, textvariable=self.pages_folder_var,
                font=('Segoe UI', 9), bg='white', relief='solid', bd=1).pack(
                side='left', fill='x', expand=True, padx=5)
        tk.Button(self.pages_folder_frame, text="Обзор папки",
                 font=('Segoe UI', 9), bg='#1565c0', fg='white',
                 relief='flat', padx=10, cursor='hand2',
                 command=lambda: self._browse_dir_var(self.pages_folder_var)).pack(
                 side='left', padx=5)
        self.pages_folder_frame.pack_forget()

        mode_frame = tk.LabelFrame(frame, text="Режим извлечения",
                                  font=('Segoe UI', 10, 'bold'),
                                  bg='#f5f5f5', fg='#333333')
        mode_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.pages_mode = tk.StringVar(value="first")

        mode_row = tk.Frame(mode_frame, bg='#f5f5f5')
        mode_row.pack(fill='x', pady=5, padx=5)

        tk.Radiobutton(mode_row, text="Первые N страниц", variable=self.pages_mode,
                      value="first", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_pages_mode).pack(side='left', padx=10)
        tk.Radiobutton(mode_row, text="Последние N страниц", variable=self.pages_mode,
                      value="last", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_pages_mode).pack(side='left', padx=10)
        tk.Radiobutton(mode_row, text="Диапазон", variable=self.pages_mode,
                      value="range", bg='#f5f5f5', font=('Segoe UI', 9),
                      command=self._toggle_pages_mode).pack(side='left', padx=10)

        self.pages_params = tk.Frame(mode_frame, bg='#f5f5f5')
        self.pages_params.pack(fill='x', pady=5, padx=20)

        self.pages_value = tk.Entry(self.pages_params, width=10,
                                   font=('Segoe UI', 9), bg='white',
                                   relief='solid', bd=1)
        self.pages_value.pack(side='left', padx=5)
        tk.Label(self.pages_params, text="страниц", font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555555').pack(side='left', padx=5)

        self.pages_start = tk.Entry(self.pages_params, width=10,
                                   font=('Segoe UI', 9), bg='white',
                                   relief='solid', bd=1)
        tk.Label(self.pages_params, text="до", font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555555').pack(side='left', padx=5)
        self.pages_end = tk.Entry(self.pages_params, width=10,
                                 font=('Segoe UI', 9), bg='white',
                                 relief='solid', bd=1)

        self.pages_start.pack_forget()
        self.pages_end.pack_forget()

        tk.Button(frame, text="Извлечь страницы",
                 font=('Segoe UI', 10, 'bold'),
                 bg='#1565c0', fg='white', relief='flat',
                 padx=20, pady=8, cursor='hand2',
                 command=self._run_pages_extract).pack(anchor='w', pady=10, padx=10)

        self.pages_result = tk.Label(frame, text="", font=('Segoe UI', 9),
                                    bg='#f5f5f5', fg='#2e7d32')
        self.pages_result.pack(anchor='w', pady=5, padx=10)

        return frame

    def _toggle_pages_source(self):
        if self.pages_scope.get() == "file":
            self.pages_file_frame.pack(fill='x', padx=20, pady=5)
            self.pages_folder_frame.pack_forget()
        else:
            self.pages_folder_frame.pack(fill='x', padx=20, pady=5)
            self.pages_file_frame.pack_forget()

    def _toggle_pages_mode(self):
        mode = self.pages_mode.get()
        self.pages_value.pack_forget()
        self.pages_start.pack_forget()
        self.pages_end.pack_forget()

        if mode == "range":
            self.pages_start.pack(side='left', padx=5)
            self.pages_end.pack(side='left', padx=5)
        else:
            self.pages_value.pack(side='left', padx=5)

    def _run_pages_extract(self):
        scope = self.pages_scope.get()
        source = self.pages_file_var.get().strip() if scope == "file" else self.pages_folder_var.get().strip()

        if not source or not os.path.exists(source):
            messagebox.showerror("Ошибка", "Укажите существующий файл или папку")
            return

        mode = self.pages_mode.get()

        try:
            if mode == "range":
                start = int(self.pages_start.get().strip())
                end = int(self.pages_end.get().strip())
                if start <= 0 or end <= 0 or start > end:
                    raise ValueError
                value = None
            else:
                value = int(self.pages_value.get().strip())
                if value <= 0:
                    raise ValueError
                start = end = None
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные номера страниц")
            return

        def run():
            try:
                self.start_progress()
                self.set_status("Извлечение страниц...")

                if scope == "file":
                    extract_pages(source, output_dir=None, mode=mode, value=value, start=start, end=end)
                else:
                    process_all_pdfs(source, output_base_dir=None, mode=mode, value=value, start=start, end=end)

                self.stop_progress()
                self.set_status("Извлечение страниц завершено")
                self.pages_result.config(text="Результаты сохранены в папке output")

            except Exception as e:
                self.stop_progress()
                self.set_status(f"Ошибка: {e}", is_error=True)
                messagebox.showerror("Ошибка", str(e))

        threading.Thread(target=run, daemon=True).start()

    def _create_export_frame(self, parent):
        frame = tk.Frame(parent, bg='#f5f5f5')

        tk.Label(frame, text="Экспорт данных", font=('Segoe UI', 14, 'bold'),
                bg='#f5f5f5', fg='#1565c0').pack(anchor='w', pady=(15, 15))

        columns_frame = tk.LabelFrame(frame, text="Выбор колонок для экспорта",
                                     font=('Segoe UI', 10, 'bold'),
                                     bg='#f5f5f5', fg='#333333')
        columns_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.column_vars = {}
        columns = [
            ('file_name', 'Имя файла'),
            ('parent_directory', 'Папка'),
            ('file_path', 'Путь'),
            ('file_size', 'Размер'),
            ('date_created', 'Создан'),
            ('date_modified', 'Изменен'),
            ('pages', 'Страницы'),
            ('file_extension', 'Расширение')
        ]

        for i, (key, label) in enumerate(columns):
            var = tk.BooleanVar(value=(key in ['file_name', 'parent_directory', 'pages']))
            self.column_vars[key] = var
            tk.Checkbutton(columns_frame, text=label, variable=var,
                          bg='#f5f5f5', font=('Segoe UI', 9)).grid(
                          row=i//3, column=i%3, sticky='w', padx=10, pady=2)

        bottom_frame = tk.Frame(frame, bg='#f5f5f5')
        bottom_frame.pack(fill='x', pady=10, padx=10)

        tk.Label(bottom_frame, text="Имя файла:", font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555555').pack(side='left', padx=5)
        self.export_name = tk.Entry(bottom_frame, width=30,
                                   font=('Segoe UI', 9), bg='white',
                                   relief='solid', bd=1)
        self.export_name.insert(0, "pdf_report")
        self.export_name.pack(side='left', padx=5)

        self.export_format = tk.StringVar(value=".xlsx")
        format_menu = ttk.Combobox(bottom_frame, textvariable=self.export_format,
                                   values=['.xlsx', '.csv'], width=8)
        format_menu.pack(side='left', padx=5)

        tk.Button(bottom_frame, text="Экспорт",
                 font=('Segoe UI', 10, 'bold'),
                 bg='#1565c0', fg='white', relief='flat',
                 padx=20, pady=8, cursor='hand2',
                 command=self._run_export).pack(side='left', padx=20)

        self.export_result = tk.Label(frame, text="", font=('Segoe UI', 9),
                                     bg='#f5f5f5', fg='#2e7d32')
        self.export_result.pack(anchor='w', pady=5, padx=10)

        return frame

    def _run_export(self):
        name = self.export_name.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Укажите имя файла")
            return

        selected = [key for key, var in self.column_vars.items() if var.get()]
        if not selected:
            messagebox.showerror("Ошибка", "Выберите хотя бы одну колонку")
            return

        fmt = self.export_format.get()
        output_path = self.app_dir / f"{name}{fmt}"

        def run():
            try:
                self.start_progress()
                self.set_status("Экспорт данных...")

                db_path = self.app_dir / 'pdf_toolkit.db'

                if fmt == '.xlsx':
                    exporter = ExcelExporter(str(db_path))
                    success = exporter.export_to_excel(selected, str(output_path))
                else:
                    manager = PDFDatabaseManager(str(db_path))
                    df = manager.get_all_records()
                    df = df[selected] if selected else df
                    df.to_csv(output_path, index=False, encoding='utf-8-sig')
                    success = True
                    manager.close()

                self.stop_progress()
                if success:
                    self.set_status(f"Экспорт завершен: {output_path}")
                    self.export_result.config(text=f"Файл сохранен: {output_path}")
                    messagebox.showinfo("Успех", f"Данные экспортированы в {output_path}")
                else:
                    self.set_status("Ошибка экспорта", is_error=True)

            except Exception as e:
                self.stop_progress()
                self.set_status(f"Ошибка: {e}", is_error=True)
                messagebox.showerror("Ошибка", str(e))

        threading.Thread(target=run, daemon=True).start()

    def _create_normalize_frame(self, parent):
        frame = tk.Frame(parent, bg='#f5f5f5')

        tk.Label(frame, text="Очистка структуры директорий", font=('Segoe UI', 14, 'bold'),
                bg='#f5f5f5', fg='#1565c0').pack(anchor='w', pady=(15, 15))

        options_frame = tk.LabelFrame(frame, text="Параметры очистки",
                                     font=('Segoe UI', 10, 'bold'),
                                     bg='#f5f5f5', fg='#333333')
        options_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.norm_cleanup = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Очищать выходную папку перед запуском",
                      variable=self.norm_cleanup,
                      bg='#f5f5f5', font=('Segoe UI', 9)).pack(anchor='w', padx=5, pady=2)

        self.norm_quiet = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Тихий режим (без подробного вывода)",
                      variable=self.norm_quiet,
                      bg='#f5f5f5', font=('Segoe UI', 9)).pack(anchor='w', padx=5, pady=2)

        tk.Button(frame, text="Запустить очистку",
                 font=('Segoe UI', 10, 'bold'),
                 bg='#1565c0', fg='white', relief='flat',
                 padx=20, pady=8, cursor='hand2',
                 command=self._run_normalize).pack(anchor='w', pady=10, padx=10)

        self.norm_result = tk.Label(frame, text="", font=('Segoe UI', 9),
                                   bg='#f5f5f5', fg='#2e7d32')
        self.norm_result.pack(anchor='w', pady=5, padx=10)

        self.norm_output = tk.Text(frame, height=8, wrap=tk.WORD,
                                  font=('Consolas', 9),
                                  bg='white', fg='#333333',
                                  relief='solid', bd=1)
        self.norm_output.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        return frame

    def _run_normalize(self):
        source = self.path_entry.get().strip()
        if not source or not os.path.exists(source):
            messagebox.showerror("Ошибка", "Укажите существующую директорию через поле 'Путь к директории'")
            return

        def run():
            try:
                self.start_progress()
                self.set_status("Запуск очистки...")
                self.norm_output.delete(1.0, tk.END)

                normalizer = DirectoryNormalizer(source)
                result = normalizer.normalize_structure()

                self.norm_output.insert(tk.END, "РЕЗУЛЬТАТЫ ОЧИСТКИ\n")
                self.norm_output.insert(tk.END, "="*50 + "\n")
                self.norm_output.insert(tk.END, f"Успешно: {result['stats']['success']}\n")
                self.norm_output.insert(tk.END, f"Дубликатов: {result['stats']['duplicates']}\n")
                self.norm_output.insert(tk.END, f"Ошибок: {result['stats']['errors']}\n")
                self.norm_output.insert(tk.END, f"\nОсновная папка: {result['structure']['work_dir']}\n")
                self.norm_output.insert(tk.END, f"Дубликаты: {result['structure']['check_dir']}\n")
                self.norm_output.insert(tk.END, f"Отчеты: {result['structure']['results_dir']}\n")

                self.stop_progress()
                self.set_status("Очистка завершена")
                self.norm_result.config(text="Очистка выполнена успешно")

            except Exception as e:
                self.stop_progress()
                self.set_status(f"Ошибка: {e}", is_error=True)
                self.norm_output.insert(tk.END, f"\nОшибка: {e}")
                messagebox.showerror("Ошибка", str(e))

        threading.Thread(target=run, daemon=True).start()

    def _create_stats_frame(self, parent):
        frame = tk.Frame(parent, bg='#f5f5f5')

        tk.Label(frame, text="Статистика", font=('Segoe UI', 14, 'bold'),
                bg='#f5f5f5', fg='#1565c0').pack(anchor='w', pady=(15, 15))

        info_frame = tk.LabelFrame(frame, text="Общая информация",
                                  font=('Segoe UI', 10, 'bold'),
                                  bg='#f5f5f5', fg='#333333')
        info_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.stats_info = tk.Label(info_frame, text="Загрузка данных...",
                                  font=('Segoe UI', 9),
                                  bg='#f5f5f5', fg='#555555')
        self.stats_info.pack(anchor='w', pady=10, padx=10)

        tk.Button(frame, text="Обновить статистику",
                 font=('Segoe UI', 10, 'bold'),
                 bg='#1565c0', fg='white', relief='flat',
                 padx=20, pady=8, cursor='hand2',
                 command=self._update_stats).pack(anchor='w', pady=10, padx=10)

        self.stats_text = tk.Text(frame, height=10, wrap=tk.WORD,
                                 font=('Consolas', 9),
                                 bg='white', fg='#333333',
                                 relief='solid', bd=1)
        self.stats_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self._update_stats()
        return frame

    def _update_stats(self):
        def run():
            try:
                self.start_progress()
                self.set_status("Обновление статистики...")
                self.stats_text.delete(1.0, tk.END)

                db_path = self.app_dir / 'pdf_toolkit.db'
                if db_path.exists():
                    manager = PDFDatabaseManager(str(db_path))
                    df = manager.get_all_records()

                    self.stats_text.insert(tk.END, "БАЗА ДАННЫХ\n")
                    self.stats_text.insert(tk.END, "="*50 + "\n")
                    self.stats_text.insert(tk.END, f"Всего записей: {len(df)}\n")
                    self.stats_text.insert(tk.END, f"Уникальных файлов: {df['file_name'].nunique() if not df.empty else 0}\n")
                    self.stats_text.insert(tk.END, f"Всего страниц: {df['pages'].sum() if not df.empty else 0}\n")
                    if not df.empty:
                        self.stats_text.insert(tk.END, f"Общий размер: {df['file_size'].sum() / 1024 / 1024:.2f} MB\n")

                    if not df.empty:
                        self.stats_text.insert(tk.END, "\nТОП-5 ПО РАЗМЕРУ\n")
                        self.stats_text.insert(tk.END, "-"*50 + "\n")
                        for _, row in df.nlargest(5, 'file_size')[['file_name', 'file_size']].iterrows():
                            size_mb = row['file_size'] / 1024 / 1024
                            self.stats_text.insert(tk.END, f"  {row['file_name']}: {size_mb:.2f} MB\n")

                    manager.close()
                else:
                    self.stats_text.insert(tk.END, "База данных не найдена\n")
                    self.stats_text.insert(tk.END, "Запустите индексацию для создания БД")

                self.stop_progress()
                self.set_status("Статистика обновлена")

            except Exception as e:
                self.stop_progress()
                self.set_status(f"Ошибка: {e}", is_error=True)
                self.stats_text.insert(tk.END, f"Ошибка: {e}")

        threading.Thread(target=run, daemon=True).start()


def main():
    root = tk.Tk()
    app = PDFToolkitGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()