from pathlib import Path


TABLES_SQL_PATH = Path(__file__).resolve().parent / "tables" / "design_tables.txt"


def get_file_operations_tables_sql() -> str:
    """Loads the file, folder, and ACL schema SQL used on startup."""
    return TABLES_SQL_PATH.read_text(encoding="utf-8")
