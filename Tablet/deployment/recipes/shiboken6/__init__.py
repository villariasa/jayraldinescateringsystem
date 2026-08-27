# Copyright (C) 2023 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from pythonforandroid.logger import info
from pythonforandroid.recipe import PythonRecipe


import os

class ShibokenRecipe(PythonRecipe):
    version = '6.9.3'

    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    @property
    def wheel_path(self):
        env_path = os.environ.get("SHIBOKEN6_ANDROID_WHEEL")
        if env_path and os.path.exists(env_path):
            return env_path
        cache_dir = Path.home() / ".cache" / "pyside6_wheels"
        wheels = list(cache_dir.glob("shiboken6*.whl"))
        if wheels:
            return str(wheels[0])
        return ""

    def build_arch(self, arch):
        ''' Unzip the wheel and copy into site-packages of target'''
        info('Installing {} into site-packages'.format(self.name))
        with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
            info('Unzip wheels and copy into {}'.format(self.ctx.get_python_install_dir(arch.arch)))
            zip_ref.extractall(self.ctx.get_python_install_dir(arch.arch))

        lib_dir = Path(f"{self.ctx.get_python_install_dir(arch.arch)}/shiboken6")
        shutil.copyfile(lib_dir / "libshiboken6.abi3.so",
                        Path(self.ctx.get_libs_dir(arch.arch)) / "libshiboken6.abi3.so")


recipe = ShibokenRecipe()