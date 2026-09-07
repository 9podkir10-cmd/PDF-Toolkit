def id_to_lang_string(lang_id: int) -> str:
    mapping = {0: "rus+eng", 1: "rus", 2: "eng"}
    return mapping.get(lang_id, "rus+eng")

def lang_to_id(lang_str: str) -> int:
    mapping = {"rus+eng": 0, "rus": 1, "eng": 2}
    return mapping.get(lang_str, 0)