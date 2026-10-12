"""Dataset acquisition is disabled for the existing-data release."""


def require_dataset_download():
    raise SystemExit(
        "Dataset downloads are disabled by the user's existing-data-only scope. "
        "Use the existing BRISC, ISLES, UCSF and CHB-MIT pilot files. "
        "No network request or new acquisition is permitted."
    )
