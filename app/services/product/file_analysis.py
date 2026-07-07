"""File storage and analysis helpers for uploaded brand/report documents."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(file_name: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", Path(file_name).name).strip("._")
    return cleaned or "upload.bin"


def storage_path_for_upload(*, workspace_id: int, file_name: str, content: bytes) -> Path:
    settings = get_settings()
    safe_name = sanitize_filename(file_name)
    digest = hashlib.sha256(content).hexdigest()[:16]
    root = Path(settings.file_upload_dir).resolve()
    folder = root / str(workspace_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{digest}_{safe_name}"


def save_upload(*, workspace_id: int, file_name: str, content: bytes) -> Path:
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise ValueError(f"File is too large. Max upload size is {settings.max_upload_bytes} bytes.")
    path = storage_path_for_upload(workspace_id=workspace_id, file_name=file_name, content=content)
    path.write_bytes(content)
    return path


def analyze_file(path: str | Path, file_type: str | None = None) -> dict[str, Any]:
    file_path = Path(path)
    suffix = (file_type or file_path.suffix.lstrip(".")).lower()
    if suffix == "pdf":
        return analyze_pdf(file_path)
    if suffix in {"csv", "tsv"}:
        return analyze_csv(file_path, delimiter="\t" if suffix == "tsv" else ",")
    if suffix in {"xlsx", "xlsm"}:
        return analyze_xlsx(file_path)
    if suffix in {"txt", "md"}:
        return analyze_text(file_path)
    return {
        "type": suffix or "unknown",
        "status": "unsupported",
        "message": "Supported file types: pdf, csv, tsv, xlsx, xlsm, txt, md.",
    }


def analyze_text(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    words = [word.lower() for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)]
    return {
        "type": path.suffix.lstrip(".").lower() or "text",
        "status": "analyzed",
        "characters": len(text),
        "words": len(words),
        "top_terms": Counter(words).most_common(20),
        "preview": text[:2000],
    }


def analyze_csv(path: Path, *, delimiter: str = ",") -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        headers = list(reader.fieldnames or [])
        for row in reader:
            rows.append({key: value for key, value in row.items()})

    column_stats: dict[str, dict[str, Any]] = {}
    for header in headers:
        values = [row.get(header, "") for row in rows]
        filled = [value for value in values if str(value).strip()]
        numeric_values: list[float] = []
        for value in filled:
            try:
                numeric_values.append(float(str(value).replace(",", "")))
            except ValueError:
                continue
        stat: dict[str, Any] = {
            "non_empty": len(filled),
            "empty": len(values) - len(filled),
            "unique": len(set(filled)),
        }
        if numeric_values and len(numeric_values) == len(filled):
            stat.update({
                "min": min(numeric_values),
                "max": max(numeric_values),
                "avg": sum(numeric_values) / len(numeric_values),
            })
        column_stats[header] = stat

    return {
        "type": "csv" if delimiter == "," else "tsv",
        "status": "analyzed",
        "rows": len(rows),
        "columns": headers,
        "column_stats": column_stats,
        "preview_rows": rows[:10],
    }


def analyze_pdf(path: Path) -> dict[str, Any]:
    try:
        import pypdf
    except ImportError:
        return {
            "type": "pdf",
            "status": "missing_dependency",
            "message": "Install pypdf to enable PDF text extraction.",
        }

    reader = pypdf.PdfReader(str(path))
    page_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(page_text).strip()
    return {
        "type": "pdf",
        "status": "analyzed",
        "pages": len(reader.pages),
        "characters": len(text),
        "preview": text[:3000],
    }


def analyze_xlsx(path: Path) -> dict[str, Any]:
    try:
        import openpyxl
    except ImportError:
        return {
            "type": "xlsx",
            "status": "missing_dependency",
            "message": "Install openpyxl to enable Excel workbook analysis.",
        }

    workbook = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    sheets: list[dict[str, Any]] = []
    for sheet in workbook.worksheets:
        rows = list(sheet.iter_rows(values_only=True))
        headers = [str(value) if value is not None else "" for value in (rows[0] if rows else [])]
        sheets.append({
            "name": sheet.title,
            "rows": max(len(rows) - 1, 0),
            "columns": headers,
            "preview_rows": [
                [cell for cell in row]
                for row in rows[1:6]
            ],
        })
    return {"type": "xlsx", "status": "analyzed", "sheets": sheets}


def generate_analysis_report(file_record: dict[str, Any]) -> str:
    result = file_record.get("analysis_result") or {}
    lines = [
        f"# File Analysis Report: {file_record.get('file_name', 'Uploaded file')}",
        "",
        f"- File type: {file_record.get('file_type', 'unknown')}",
        f"- Analysis status: {file_record.get('analysis_status', 'unknown')}",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(result, indent=2, default=str)[:8000],
        "```",
    ]
    return "\n".join(lines)
