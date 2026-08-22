import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from PIL import Image, ImageEnhance

from backend.barcodes import process_single_pdf_file
from backend.config import get_scan_profiles

try:
    import twain
except ImportError:
    twain = None


class ScannerBackend:
    def __init__(self, profile_name: str = None):
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
        self.device = None
        self.source_manager = None
        self._temp_dir = None
        self._selected_scanner_name = None

    def select_scanner_interactive(self) -> bool:
        if twain is None:
            raise RuntimeError("Библиотека TWAIN не установлена.")
        try:
            sm = twain.SourceManager()
            try:
                src = sm.open_source()
            except Exception as e:
                if "ConditionCode = 0" in str(e):
                    src = None
                else:
                    raise RuntimeError(f"Ошибка TWAIN: {e}")
            if src:
                self.source_manager = sm
                self.device = src
                self._selected_scanner_name = src.name
                return True
            else:
                sm.close()
                self.source_manager = None
                self.device = None
                self._selected_scanner_name = None
                return False
        except Exception as e:
            raise RuntimeError(f"Ошибка выбора сканера: {e}")

    def open_device_by_name(self, name: str) -> bool:
        if twain is None:
            raise RuntimeError("Библиотека TWAIN не установлена.")
        try:
            sm = twain.SourceManager()
            src = sm.open_source(name)
            if src:
                self.source_manager = sm
                self.device = src
                self._selected_scanner_name = name
                return True
            else:
                sm.close()
                return False
        except Exception as e:
            raise RuntimeError(f"Ошибка открытия сканера: {e}")

    def get_selected_scanner_name(self) -> Optional[str]:
        return self._selected_scanner_name

    def scan_pages(self) -> List[Image.Image]:
        if not self.device:
            raise RuntimeError("Сканер не выбран.")
        images = []
        try:
            caps = self.device.capabilities
            caps.ICAP_PIXELTYPE.set(
                twain.PixelType.RGB if self.profile.get("color_mode") == "color"
                else twain.PixelType.GRAY if self.profile.get("color_mode") == "gray"
                else twain.PixelType.BW
            )
            caps.ICAP_XRESOLUTION.set(self.profile.get("dpi", 300))
            caps.ICAP_YRESOLUTION.set(self.profile.get("dpi", 300))
            if self.profile.get("duplex", False):
                caps.ICAP_DUPLEX.set(True)

            self.device.request_acquire()
            while True:
                rv = self.device.xfer_image_native()
                if rv is None:
                    break
                if isinstance(rv, twain.Image):
                    pil_img = self._twain_to_pil(rv)
                    images.append(pil_img)
                elif isinstance(rv, (list, tuple)):
                    for img in rv:
                        pil_img = self._twain_to_pil(img)
                        images.append(pil_img)
        except Exception as e:
            raise RuntimeError(f"Ошибка сканирования: {e}")
        finally:
            if self.device:
                self.device.close()
            if self.source_manager:
                self.source_manager.close()
        return images

    def _twain_to_pil(self, twain_image) -> Image.Image:
        if hasattr(twain_image, 'bits_per_pixel') and twain_image.bits_per_pixel == 1:
            mode = '1'
        elif hasattr(twain_image, 'bits_per_pixel') and twain_image.bits_per_pixel == 8:
            mode = 'L'
        else:
            mode = 'RGB'
        data = getattr(twain_image, 'data', None)
        if data is None:
            raise ValueError("Нет данных изображения")
        if not isinstance(data, bytes):
            data = bytes(data)
        return Image.frombytes(mode, (twain_image.columns, twain_image.rows), data)

    def _apply_image_adjustments(self, image: Image.Image) -> Image.Image:
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

    def scan_to_pdf(
        self,
        output_folder: str,
        base_filename: str = "scan",
        split_by_barcode: bool = False,
        barcode_modes: Optional[List[str]] = None,
    ) -> List[str]:
        if barcode_modes is None:
            barcode_modes = ["patch1", "patch2", "patch3", "patch4", "patchT"]

        images = self.scan_pages()
        if not images:
            return []

        temp_pdf = self._create_temp_pdf(images)

        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not split_by_barcode:
            target_name = f"{base_filename}.pdf"
            target_path = output_dir / target_name
            shutil.copy(temp_pdf, target_path)
            return [str(target_path)]
        else:
            temp_out_dir = Path(tempfile.mkdtemp())
            try:
                created_files = process_single_pdf_file(
                    temp_pdf,
                    barcode_modes,
                    str(temp_out_dir)
                )
                if not created_files:
                    target_name = f"{base_filename}.pdf"
                    target_path = output_dir / target_name
                    shutil.copy(temp_pdf, target_path)
                    return [str(target_path)]

                final_paths = []
                for i, src_path in enumerate(created_files):
                    stem = f"{base_filename}_part{i+1:02d}"
                    ext = Path(src_path).suffix
                    dest_path = output_dir / f"{stem}{ext}"
                    shutil.move(src_path, dest_path)
                    final_paths.append(str(dest_path))
                return final_paths
            finally:
                shutil.rmtree(temp_out_dir, ignore_errors=True)

    def cleanup_temp(self):
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None


def get_scanner_profile(profile_name: str) -> Optional[Dict[str, Any]]:
    profiles = get_scan_profiles()
    for p in profiles:
        if p.get("name") == profile_name:
            return p
    return None


def list_scan_profiles() -> List[str]:
    return [p.get("name", "unnamed") for p in get_scan_profiles()]