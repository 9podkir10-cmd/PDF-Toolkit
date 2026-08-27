import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from PIL import Image, ImageEnhance

from backend.barcodes import process_single_pdf_file
from backend.config import get_scan_profiles
from backend.scanning.twain_scanner import TwainScanner, Scanner
# MOCK: импортируем мок-сканер
from backend.scanning.mock_scanner import MockScanner

try:
    import twain
except ImportError:
    twain = None


class ScannerBackend:
    # MOCK: добавили параметр use_mock
    def __init__(self, profile_name: str = None, use_mock: bool = False):
        self.profile = None
        if profile_name:
            profiles = get_scan_profiles()
            for p in profiles:
                if p.get("name") == profile_name:
                    self.profile = p
                    break
        if self.profile is None:
            self.profile = {
                "name": "default",
                "dpi": 300,
                "color_mode": "color",
                "page_size": "A4",
                "file_format": "pdf",
                "brightness": 0,
                "contrast": 0,
                "duplex": False,
            }
        # Используем абстракцию Scanner (может быть TwainScanner или MockScanner)
        self.scanner: Optional[Scanner] = None
        self._selected_scanner_name: Optional[str] = None
        self._temp_dir = None
        # MOCK: сохраняем флаг
        self.use_mock = use_mock

    # ----- Вспомогательные методы для работы со сканером -----

    def _ensure_scanner(self) -> None:
        """Создаёт экземпляр сканера, если его ещё нет."""
        if self.scanner is None:
            # MOCK: если включён мок – создаём MockScanner
            if self.use_mock:
                # Можно передать количество страниц или папку с изображениями
                # Для примера – 10 страниц
                self.scanner = MockScanner(num_pages=10)
            else:
                self.scanner = TwainScanner()

    def _close_scanner(self) -> None:
        """Закрывает текущий сканер, если он открыт."""
        if self.scanner is not None and self.scanner.is_open:
            try:
                self.scanner.close()
            except Exception:
                pass

    # ----- Публичные методы для управления сканером -----

    def select_scanner_interactive(self) -> bool:
        """
        Открывает диалог выбора сканера (через TWAIN) или выбирает мок.
        Возвращает True, если сканер выбран успешно.
        """
        # MOCK: если используется мок – просто выбираем его
        if self.use_mock:
            self._ensure_scanner()
            self._close_scanner()
            self.scanner.open("Mock Scanner")
            self._selected_scanner_name = "Mock Scanner (тестовый)"
            return True

        # Обычная логика для TWAIN
        if twain is None:
            raise RuntimeError("Библиотека TWAIN не установлена.")

        sm = None
        src = None
        try:
            sm = twain.SourceManager()
            src = sm.open_source()  # показывает диалог выбора
            if src is None:
                return False
            selected_name = src.name
            src.close()
            sm.close()
            self._ensure_scanner()
            self._close_scanner()
            self.scanner.open(selected_name)
            self._selected_scanner_name = selected_name
            return True
        except Exception as e:
            if src is not None:
                try:
                    src.close()
                except Exception:
                    pass
            if sm is not None:
                try:
                    sm.close()
                except Exception:
                    pass
            raise RuntimeError(f"Ошибка выбора сканера: {e}")

    def open_device_by_name(self, name: str) -> bool:
        """Открывает сканер по указанному имени (или мок, если включён)."""
        try:
            self._ensure_scanner()
            self._close_scanner()
            # MOCK: если мок – открываем с любым именем (игнорируем)
            if self.use_mock:
                self.scanner.open("Mock Scanner")
                self._selected_scanner_name = "Mock Scanner (тестовый)"
                return True
            # Обычный случай
            self.scanner.open(name)
            self._selected_scanner_name = name
            return True
        except Exception as e:
            raise RuntimeError(f"Ошибка открытия сканера: {e}")

    def get_selected_scanner_name(self) -> Optional[str]:
        """Возвращает имя открытого сканера или None."""
        if self.scanner is not None and self.scanner.is_open:
            return self.scanner.device_name
        return self._selected_scanner_name

    # ----- Основной процесс сканирования -----

    def scan_pages(self) -> List[Image.Image]:
        """
        Выполняет сканирование страниц с применением настроек профиля.
        Возвращает список PIL.Image.
        """
        if self.scanner is None or not self.scanner.is_open:
            raise RuntimeError("Сканер не выбран или не открыт.")

        # Применяем настройки из профиля
        settings = {
            "dpi": self.profile.get("dpi", 300),
            "color_mode": self.profile.get("color_mode", "color"),
            "duplex": self.profile.get("duplex", False),
        }
        self.scanner.configure(settings)

        images = []
        try:
            for page in self.scanner.acquire():
                img = page.image
                # Применяем коррекцию яркости/контраста
                img = self._apply_image_adjustments(img)
                images.append(img)
        finally:
            # Закрываем сканер после захвата всех страниц
            self._close_scanner()

        return images

    def _apply_image_adjustments(self, image: Image.Image) -> Image.Image:
        """Применяет настройки яркости и контраста из профиля."""
        brightness = self.profile.get("brightness", 0)
        contrast = self.profile.get("contrast", 0)

        if brightness != 0:
            enhancer = ImageEnhance.Brightness(image)
            factor = 1.0 + brightness / 100.0
            image = enhancer.enhance(factor)

        if contrast != 0:
            enhancer = ImageEnhance.Contrast(image)
            factor = 1.0 + contrast / 100.0
            image = enhancer.enhance(factor)

        return image

    def _create_temp_pdf(self, images: List[Image.Image]) -> str:
        """Создаёт временный PDF из списка изображений."""
        if not images:
            raise RuntimeError("Нет изображений для сохранения.")

        temp_dir = tempfile.mkdtemp()
        self._temp_dir = temp_dir
        pdf_path = os.path.join(temp_dir, "temp_scan.pdf")

        images[0].save(
            pdf_path,
            save_all=True,
            append_images=images[1:],
            format="PDF",
            resolution=100.0
        )
        return pdf_path

    # ----- Публичный метод создания PDF (с разделением) -----

    def scan_to_pdf(
        self,
        output_folder: str,
        base_filename: str = "scan",
        split_by_barcode: bool = False,
        barcode_modes: Optional[List[str]] = None,
        split_by_count: Optional[int] = None,
    ) -> List[str]:
        """
        Сканирует и сохраняет результат в PDF.
        Если split_by_barcode=True – разделяет по штрих-кодам.
        Если split_by_count задан – разбивает на части по указанному числу страниц.
        """
        if barcode_modes is None:
            barcode_modes = ["patch1", "patch2", "patch3", "patch4", "patchT"]

        images = self.scan_pages()
        if not images:
            return []

        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Если включено разделение по количеству страниц
        if split_by_count and split_by_count > 0:
            chunks = [images[i:i + split_by_count] for i in range(0, len(images), split_by_count)]
            final_paths = []
            for idx, chunk in enumerate(chunks):
                temp_pdf = self._create_temp_pdf(chunk)
                dest_name = f"{base_filename}_part{idx + 1:02d}.pdf"
                dest_path = output_dir / dest_name
                shutil.copy(temp_pdf, dest_path)
                final_paths.append(str(dest_path))
            return final_paths

        # Если включено разделение по штрих-кодам – используем существующую логику
        if split_by_barcode:
            temp_pdf = self._create_temp_pdf(images)
            temp_out_dir = Path(tempfile.mkdtemp())
            try:
                created_files = process_single_pdf_file(
                    temp_pdf,
                    barcode_modes,
                    str(temp_out_dir)
                )
                if not created_files:
                    # Если разделение не дало результатов – сохраняем целый PDF
                    target_path = output_dir / f"{base_filename}.pdf"
                    shutil.copy(temp_pdf, target_path)
                    return [str(target_path)]

                final_paths = []
                for i, src_path in enumerate(created_files):
                    stem = f"{base_filename}_part{i + 1:02d}"
                    ext = Path(src_path).suffix
                    dest_path = output_dir / f"{stem}{ext}"
                    shutil.move(src_path, dest_path)
                    final_paths.append(str(dest_path))
                return final_paths
            finally:
                shutil.rmtree(temp_out_dir, ignore_errors=True)

        # Без разделения – один PDF
        temp_pdf = self._create_temp_pdf(images)
        target_path = output_dir / f"{base_filename}.pdf"
        shutil.copy(temp_pdf, target_path)
        return [str(target_path)]

    def cleanup_temp(self):
        """Удаляет временные файлы."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    # ----- Деструктор (для надёжности) -----
    def __del__(self):
        try:
            self._close_scanner()
            self.cleanup_temp()
        except Exception:
            pass


# ---- Глобальные функции для работы с профилями (без изменений) ----

def get_scanner_profile(profile_name: str) -> Optional[Dict[str, Any]]:
    profiles = get_scan_profiles()
    for p in profiles:
        if p.get("name") == profile_name:
            return p
    return None


def list_scan_profiles() -> List[str]:
    return [p.get("name", "unnamed") for p in get_scan_profiles()]