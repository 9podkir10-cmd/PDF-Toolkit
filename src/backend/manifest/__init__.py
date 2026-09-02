from pathlib import Path
from .repository import ManifestRepository
from .service import ManifestService

def get_manifest_service(manifest_path: str = "manifest.json") -> ManifestService:
    repo = ManifestRepository(Path(manifest_path))
    return ManifestService(repo)