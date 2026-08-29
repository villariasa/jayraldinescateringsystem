#!/bin/bash
set -e

PROJECT_DIR="/home/villarias/Projects/jayraldinescateringsystem/Tablet_Android_APK"
rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/app/src/main/java/com/jayraldines/cateringsystem"
mkdir -p "$PROJECT_DIR/app/src/main/assets"
mkdir -p "$PROJECT_DIR/app/src/main/res/values"
mkdir -p "$PROJECT_DIR/app/src/main/res/mipmap-xxhdpi"
mkdir -p "$PROJECT_DIR/gradle/wrapper"

echo "==> Creating Android Gradle Project Configuration..."

# 1. Root settings.gradle
cat << 'EOF' > "$PROJECT_DIR/settings.gradle"
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "JayraldinesCatering"
include ':app'
EOF

# 2. Root build.gradle
cat << 'EOF' > "$PROJECT_DIR/build.gradle"
plugins {
    id 'com.android.application' version '8.2.2' apply false
}
EOF

# 3. gradle.properties
cat << 'EOF' > "$PROJECT_DIR/gradle.properties"
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.enableJetifier=true
EOF

# 4. app/build.gradle
cat << 'EOF' > "$PROJECT_DIR/app/build.gradle"
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.jayraldines.cateringsystem'
    compileSdk 34

    defaultConfig {
        applicationId "com.jayraldines.cateringsystem"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
        debug {
            applicationIdSuffix ""
            debuggable true
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.webkit:webkit:1.10.0'
    implementation 'com.google.android.material:material:1.11.0'
}
EOF

# 5. AndroidManifest.xml
cat << 'EOF' > "$PROJECT_DIR/app/src/main/AndroidManifest.xml"
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="Jayraldine's Catering"
        android:roundIcon="@mipmap/ic_launcher"
        android:supportsRtl="true"
        android:theme="@style/Theme.JayraldinesCatering"
        android:hardwareAccelerated="true"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:theme="@style/Theme.JayraldinesCatering.Fullscreen">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

# 6. res/values/styles.xml
cat << 'EOF' > "$PROJECT_DIR/app/src/main/res/values/styles.xml"
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.JayraldinesCatering" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">#E11D48</item>
        <item name="colorPrimaryVariant">#BE123C</item>
        <item name="colorOnPrimary">#FFFFFF</item>
    </style>
    <style name="Theme.JayraldinesCatering.Fullscreen" parent="Theme.JayraldinesCatering">
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowActionBar">false</item>
        <item name="android:windowFullscreen">true</item>
        <item name="android:windowContentOverlay">@null</item>
    </style>
</resources>
EOF

# 7. MainActivity.java
cat << 'EOF' > "$PROJECT_DIR/app/src/main/java/com/jayraldines/cateringsystem/MainActivity.java"
package com.jayraldines.cateringsystem;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.os.Environment;
import android.util.Base64;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewClientCompat;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

public class MainActivity extends AppCompatActivity {
    private WebView webView;

    @SuppressLint({"SetJavaScriptEnabled"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Hide navigation/status bars for immersive kiosk experience
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );

        webView = new WebView(this);
        setContentView(webView);

        final WebViewAssetLoader assetLoader = new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
            .build();

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebViewClient(new WebViewClientCompat() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }
        });

        // Add native file saving interface for PDF receipts & Excel archives
        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void saveBase64File(String base64Data, String filename, String mimeType) {
                try {
                    byte[] bytes = Base64.decode(base64Data, Base64.DEFAULT);
                    File downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                    File file = new File(downloads, filename);
                    OutputStream os = new FileOutputStream(file);
                    os.write(bytes);
                    os.flush();
                    os.close();
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "Saved to Downloads: " + filename, Toast.LENGTH_LONG).show());
                } catch (Exception e) {
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "Failed to save: " + e.getMessage(), Toast.LENGTH_SHORT).show());
                }
            }
        }, "AndroidNative");

        // Load offline standalone kiosk app
        webView.loadUrl("https://appassets.androidplatform.net/assets/index.html");
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
EOF

# Copy app icon
cp "/home/villarias/Projects/jayraldinescateringsystem/Tablet_PWA/frontend/icons/logo.png" "$PROJECT_DIR/app/src/main/res/mipmap-xxhdpi/ic_launcher.png"

# Copy all offline assets from Tablet_PWA/frontend
cp -r /home/villarias/Projects/jayraldinescateringsystem/Tablet_PWA/frontend/* "$PROJECT_DIR/app/src/main/assets/"

echo "==> Android project created successfully."
