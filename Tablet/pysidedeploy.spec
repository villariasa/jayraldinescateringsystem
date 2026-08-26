[app]

# title of your application
title = JayraldinesCateringTablet

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = main.py

# directory where the executable output is generated
exec_directory = dist

# application icon
icon = assets/logo.png

[python]

# python path
python_path = /home/villarias/miniconda3/envs/jayraldines_tablet/bin/python3.11

# python packages to install
packages = reportlab,openpyxl

# buildozer = for deploying Android application
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# paths to required qml files. comma separated
qml_files = 

# excluded qml plugin binaries
excluded_qml_plugins = 

# qt modules used. comma separated
modules = Gui,Widgets,Core

# qt plugins used by the application
plugins = 

[android]

# path to pyside wheel
wheel_pyside = /home/villarias/.cache/pyside6_wheels/PySide6-6.9.3-6.9.3-cp311-cp311-android_aarch64.whl

# path to shiboken wheel
wheel_shiboken = /home/villarias/.cache/pyside6_wheels/shiboken6-6.9.3-6.9.3-cp311-cp311-android_aarch64.whl

# plugins to be copied to libs folder of the packaged application. comma separated
plugins = platforms_qtforandroid

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
macos.permissions = 

# mode of using nuitka
mode = onefile

# specify any extra nuitka arguments
extra_args = --quiet --noinclude-qt-translations

[buildozer]

# build mode
# possible values = ["aarch64", "armv7a", "i686", "x86_64"]
mode = debug

# path to pyside6 and shiboken6 recipe dir
recipe_dir = /home/villarias/Projects/jayraldinescateringsystem/Tablet/deployment/recipes

# path to extra qt android .jar files to be loaded by the application
jars_dir = /home/villarias/Projects/jayraldinescateringsystem/Tablet/deployment/jar/PySide6/jar

# if empty, uses default ndk path downloaded by buildozer
ndk_path = /home/villarias/.pyside6_android_deploy/android-ndk/android-ndk-r27c

# if empty, uses default sdk path downloaded by buildozer
sdk_path = /home/villarias/.buildozer/android/platform/android-sdk

# other libraries to be loaded at app startup. comma separated.
local_libs = plugins_platforms_qtforandroid

# architecture of deployed platform
arch = aarch64

