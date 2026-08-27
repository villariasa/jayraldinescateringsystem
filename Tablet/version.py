"""
Version metadata for Jayraldine's Catering - Tablet App.

Semantic versioning: MAJOR.MINOR.PATCH
- MAJOR: breaking schema/export-format changes that require a matching PC update.
- MINOR: new tablet features, backward-compatible.
- PATCH: bug fixes only.
"""

APP_NAME = "Jayraldines Catering"
APP_ID = "com.jayraldines.catering"

VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_PATCH = 1

VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
BUILD_CODE = 101

# Bumped whenever the local SQLite schema changes shape in a way that affects
# compatibility with the PC's merge_database_file() import.
SCHEMA_VERSION = 1

# Terms & Conditions version currently bundled with this build.
TERMS_VERSION = "1.0"


def get_version_string() -> str:
    return f"{APP_NAME} v{VERSION} (schema v{SCHEMA_VERSION})"
