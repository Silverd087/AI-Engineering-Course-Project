"""Path helpers for report files."""

import os

REPORT_FOLDER = "reports"


def report_path(base, name):
    return os.path.join(base, REPORT_FOLDER, name + ".csv")


def ensure_report_dir(base):
    path = os.path.join(base, REPORT_FOLDER)
    os.makedirs(path, exist_ok=True)
    return path


def report_exists(base, name):
    return os.path.exists(report_path(base, name))


def extension(name):
    return os.path.splitext(name)[1]