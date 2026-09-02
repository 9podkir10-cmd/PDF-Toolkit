from pathlib import Path
from typing import Optional

def find_manifest(pdf_path: Path) -> Optional[Path]:
    """
    Ищет manifest.json рядом с PDF или в соответствующей _hardlink папке.
    """
    current_dir = pdf_path.parent
    manifest_path = current_dir / "manifest.json"
    if manifest_path.exists():
        return manifest_path

    parent_dir = current_dir.parent
    hardlink_dir = parent_dir / (current_dir.name + "_hardlink")
    manifest_path = hardlink_dir / "manifest.json"
    if hardlink_dir.exists() and manifest_path.exists():
        return manifest_path

    return None