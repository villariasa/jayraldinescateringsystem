#!/usr/bin/env bash
# Jayraldine's Catering — Tablet App — Linux setup/run script.
# Creates an isolated environment, installs dependencies, and launches the
# app so you can test the tablet workflow on a regular Linux desktop before
# deploying to an actual Android tablet.
#
# Prefers a conda env when conda is available/active, because `python3 -m
# venv` frequently fails on conda's Python with an ensurepip error (conda
# Pythons often ship without the bundled pip wheels ensurepip needs). Falls
# back to a plain venv (with a manual pip bootstrap) when conda isn't present.
#
# IMPORTANT: we call the target interpreter by its *full path*, never via
# `conda run ... python3` or a bare `python3`/`pip` on PATH. Both `conda run`
# and plain PATH lookups can resolve to a *different* python3 (e.g. a
# pyenv/pipx shim in ~/.local/bin) that shadows the one actually inside the
# env we just created — silently installing packages where the app can
# never see them. A full path can't be shadowed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$APP_DIR/.venv"
CONDA_ENV_NAME="jayraldines_tablet"

cd "$APP_DIR"

run_with_conda() {
    echo "==> Conda detected — using a conda environment (avoids the venv/ensurepip bug on conda Pythons)"
    local conda_base env_prefix py
    conda_base="$(conda info --base)"
    env_prefix="$conda_base/envs/$CONDA_ENV_NAME"

    if [ ! -d "$env_prefix" ]; then
        echo "==> Creating conda environment '$CONDA_ENV_NAME'"
        conda create -n "$CONDA_ENV_NAME" python=3.11 -y
    fi

    py="$env_prefix/bin/python3"
    if [ ! -x "$py" ]; then
        echo "ERROR: expected interpreter not found at $py" >&2
        exit 1
    fi
    echo "==> Using interpreter: $py"

    echo "==> Installing dependencies"
    "$py" -m pip install --upgrade pip >/dev/null
    "$py" -m pip install -r requirements.txt

    echo "==> Verifying PySide6 is importable in the target environment"
    "$py" -c "import PySide6" || {
        echo "ERROR: PySide6 installed but is not importable via $py." >&2
        exit 1
    }

    # Qt's Linux "xcb" backend needs libxcb-cursor.so.0, which many minimal
    # Linux installs don't ship system-wide. Install the conda-forge package
    # (no root needed — it lands inside this env, not system-wide) and point
    # the dynamic linker at this env's own lib/ so Qt finds it there instead
    # of requiring `sudo apt install libxcb-cursor0`.
    if ! ldconfig -p 2>/dev/null | grep -q libxcb-cursor; then
        echo "==> Installing libxcb-cursor (Qt Linux display dependency, no root needed)"
        conda install -n "$CONDA_ENV_NAME" -c conda-forge xcb-util-cursor -y >/dev/null || \
            echo "WARNING: could not auto-install xcb-util-cursor. If the app fails to show a window, run: conda install -n $CONDA_ENV_NAME -c conda-forge xcb-util-cursor -y"
    fi

    echo "==> Launching Tablet App"
    LD_LIBRARY_PATH="$env_prefix/lib:${LD_LIBRARY_PATH:-}" "$py" main.py "$@"
}

run_with_venv() {
    local py
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/python3" ]; then
        rm -rf "$VENV_DIR"
        echo "==> Creating virtual environment at $VENV_DIR"
        # --without-pip sidesteps ensurepip entirely (it's the step that
        # fails on some Python builds); we bootstrap pip manually right after.
        python3 -m venv --copies --without-pip "$VENV_DIR"

        py="$VENV_DIR/bin/python3"
        if ! "$py" -m pip --version >/dev/null 2>&1; then
            echo "==> Bootstrapping pip"
            curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
            "$py" /tmp/get-pip.py
        fi
    fi

    py="$VENV_DIR/bin/python3"
    echo "==> Using interpreter: $py"

    echo "==> Installing dependencies"
    "$py" -m pip install --upgrade pip >/dev/null
    "$py" -m pip install -r requirements.txt

    echo "==> Verifying PySide6 is importable in the target environment"
    "$py" -c "import PySide6" || {
        echo "ERROR: PySide6 installed but is not importable via $py." >&2
        exit 1
    }

    echo "==> Launching Tablet App"
    "$py" main.py "$@"
}

if command -v conda >/dev/null 2>&1; then
    run_with_conda "$@"
else
    run_with_venv "$@"
fi
