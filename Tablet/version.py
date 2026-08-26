"""
Version metadata for Jayraldine's Catering - Tablet App.

Semantic versioning: MAJOR.MINOR.PATCH
- MAJOR: breaking schema/export-format changes that require a matching PC update.
- MINOR: new tablet features, backward-compatible.
- PATCH: bug fixes only.
"""

APP_NAME = "Jayraldine's Catering - Tablet"
APP_ID = "com.jayraldines.catering.tablet"

VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_PATCH = 0

VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

# Bumped whenever the local SQLite schema changes shape in a way that affects
# compatibility with the PC's merge_database_file() import. The PC's merge
# logic matches on table/column names, not this number directly, but keep it
# in sync with utils/sqlite_schema.py SCHEMA_VERSION for diagnostics.
SCHEMA_VERSION = 1

# Terms & Conditions version currently bundled with this build. Must match
# utils/terms.py CURRENT_TERMS_VERSION - bump both together whenever the
# business changes the Terms and Conditions text.
TERMS_VERSION = "1.0"


def get_version_string() -> str:
    return f"{APP_NAME} v{VERSION} (schema v{SCHEMA_VERSION})"
