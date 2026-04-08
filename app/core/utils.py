import hashlib

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".pptx", ".xlsx", ".csv", ".json"}


def validate_file_extension(filename: str) -> bool:
    if not filename:
        return False
    ext = filename.lower().split('.')[-1]
    return f".{ext}" in ALLOWED_EXTENSIONS


def validate_file_size(size_bytes: int, max_size_mb: int = 100) -> bool:
    max_bytes = max_size_mb * 1024 * 1024
    return size_bytes <= max_bytes


def calculate_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_mime_type_from_extension(filename: str) -> str:
    mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".json": "application/json",
    }
    ext = filename.lower().split('.')[-1]
    return mime_types.get(f".{ext}", "application/octet-stream")
