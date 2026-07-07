from __future__ import annotations

from app.services.product.file_analysis import analyze_csv, generate_analysis_report, sanitize_filename


def test_sanitize_filename_removes_path_and_unsafe_chars() -> None:
    assert sanitize_filename("../my report!.csv") == "my_report_.csv"


def test_analyze_csv_summarizes_columns(tmp_path) -> None:
    path = tmp_path / "metrics.csv"
    path.write_text("name,clicks\nA,10\nB,20\nC,\n", encoding="utf-8")

    result = analyze_csv(path)

    assert result["status"] == "analyzed"
    assert result["rows"] == 3
    assert result["columns"] == ["name", "clicks"]
    assert result["column_stats"]["clicks"]["avg"] == 15


def test_generate_analysis_report_contains_summary() -> None:
    report = generate_analysis_report({
        "file_name": "metrics.csv",
        "file_type": "csv",
        "analysis_status": "analyzed",
        "analysis_result": {"rows": 3},
    })

    assert "# File Analysis Report: metrics.csv" in report
    assert '"rows": 3' in report
