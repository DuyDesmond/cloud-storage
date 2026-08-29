import re

def sanitize_filename(filename: str) -> str:
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '', cleaned)
    return cleaned.strip() or "unnamed_file"
