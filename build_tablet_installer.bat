@echo off
title Jayraldine's Catering - Tablet Installer Builder
cd /d "%~dp0"

call "%~dp0build_apk.bat" %*
