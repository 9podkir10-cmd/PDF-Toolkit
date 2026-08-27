from dataclasses import dataclass, field
from typing import List, Optional
from backend.services.box_to_img import Region

@dataclass
class OCRSession:
    pdf_path: Optional[str] = None
    zones: List[Region] = field(default_factory=list)
    zone_texts: List[str] = field(default_factory=list)
    zone_ids: List[Optional[str]] = field(default_factory=list)
    queue: List[str] = field(default_factory=list)
    current_index: int = -1
    input_mode: Optional[str] = None
    locked: bool = False
    locked_rects: List[Region] = field(default_factory=list)