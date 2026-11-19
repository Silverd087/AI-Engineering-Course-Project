from pathlib import Path

from reports.paths import ensure_report_dir, extension, report_exists, report_path


def test_report_path_is_a_pathlib_path(tmp_path):
    assert isinstance(report_path(tmp_path, "sales"), Path)


def test_report_path_points_into_reports_folder(tmp_path):
    assert report_path(tmp_path, "sales") == tmp_path / "reports" / "sales.csv"


def test_ensure_report_dir_creates_folder_and_returns_path(tmp_path):
    result = ensure_report_dir(tmp_path)
    assert isinstance(result, Path)
    assert (tmp_path / "reports").is_dir()


def test_report_exists_after_writing_the_file(tmp_path):
    ensure_report_dir(tmp_path)
    report_path(tmp_path, "sales").write_text("a,b\n", encoding="utf-8")
    assert report_exists(tmp_path, "sales")


def test_extension_is_the_dot_suffix():
    assert extension("data.csv") == ".csv"