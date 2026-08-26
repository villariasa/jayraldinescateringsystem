@echo off
title Jayraldine's Catering - Tablet Installer Builder
cd /d "%~dp0Tablet"

call "%~dp0Tablet\build_installer.bat" %*
