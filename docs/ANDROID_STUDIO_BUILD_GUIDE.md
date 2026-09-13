# Android Studio Gradle Build & Release Packaging Guide

## 1. Build Environment
- **JDK Version**: OpenJDK 17 LTS.
- **Gradle Version**: 8.5.
- **Compile SDK**: API 34 (Android 14).
- **Target SDK**: API 34.
- **Min SDK**: API 24 (Android 7.0 Nougat).

## 2. Release Command
```bash
./gradlew assembleRelease
```
Outputs standalone signed APK in `Tablet_Android_APK/app/build/outputs/apk/release/`.
