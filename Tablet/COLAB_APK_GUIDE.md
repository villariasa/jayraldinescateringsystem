# 📱 Google Colab Guide: Build Android APK for Jayraldine's Catering

Follow these steps to build the Android `.apk` installer using **Google Colab** (free cloud Linux environment):

---

### 🚀 Step-by-Step Instructions:

1. Open [Google Colab](https://colab.research.google.com/) and click **"New Notebook"**.
2. Create a new code cell, paste the code below, and click **Play (Run Cell)**:

```python
# ============================================================
# 📱 JAYRALDINE'S CATERING - GOOGLE COLAB APK BUILD SCRIPT
# ============================================================

# 1. Reset working directory to /content first (crucial!)
%cd /content
!rm -rf /content/jayraldinescateringsystem
!git clone https://github.com/villariasa/jayraldinescateringsystem.git
%cd /content/jayraldinescateringsystem/Tablet

# 2. Install Python 3.11, OpenJDK 17, and build utilities
!apt-get update -qq
!apt-get install -y -qq software-properties-common
!add-apt-repository -y ppa:deadsnakes/ppa
!apt-get update -qq
!apt-get install -y -qq build-essential pkg-config libffi-dev cmake git python3.11 python3.11-venv python3.11-dev openjdk-17-jdk autoconf automake libtool zlib1g-dev rsync unzip curl

# 3. Create Python 3.11 Virtual Environment & Install Dependencies
!rm -rf .venv
!python3.11 -m venv --system-site-packages .venv
!.venv/bin/pip install --upgrade pip -q
!.venv/bin/pip install -r requirements.txt -q
!.venv/bin/pip install buildozer==1.5.0 cython==0.29.33 -q

# 4. Download & Setup Android NDK r25b & SDK Commandline Tools (~15 seconds)
!mkdir -p /root/Android/Sdk/ndk /root/Android/Sdk/cmdline-tools
!if [ ! -d "/root/Android/Sdk/ndk/25.2.9519653" ]; then \
    curl -sL -o /tmp/ndk.zip https://dl.google.com/android/repository/android-ndk-r25b-linux.zip && \
    unzip -q -o /tmp/ndk.zip -d /root/Android/Sdk/ndk && \
    mv /root/Android/Sdk/ndk/android-ndk-r25b /root/Android/Sdk/ndk/25.2.9519653 && \
    rm -f /tmp/ndk.zip; \
fi
!if [ ! -d "/root/Android/Sdk/cmdline-tools/latest" ]; then \
    curl -sL -o /tmp/cmdline.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip && \
    unzip -q -o /tmp/cmdline.zip -d /tmp/cmdline && \
    mv /tmp/cmdline/cmdline-tools /root/Android/Sdk/cmdline-tools/latest && \
    rm -rf /tmp/cmdline /tmp/cmdline.zip; \
fi

# 5. Set Environment Variables
import os
os.environ.pop("PIP_USER", None)
os.environ.pop("PIP_NO_USER", None)
os.environ["VIRTUAL_ENV"] = "/content/jayraldinescateringsystem/Tablet/.venv"
os.environ["ANDROID_SDK_ROOT"] = "/root/Android/Sdk"
os.environ["ANDROIDSDK"] = "/root/Android/Sdk"
os.environ["ANDROID_NDK_ROOT"] = "/root/Android/Sdk/ndk/25.2.9519653"
os.environ["ANDROIDNDK"] = "/root/Android/Sdk/ndk/25.2.9519653"
os.environ["ANDROIDMINAPI"] = "24"
os.environ["ANDROID_NDK_API"] = "24"
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
os.environ["PATH"] = f"/root/Android/Sdk/cmdline-tools/latest/bin:/content/jayraldinescateringsystem/Tablet/.venv/bin:/usr/lib/jvm/java-17-openjdk-amd64/bin:{os.environ['PATH']}"

# 6. Clean build cache and build Android APK
!sed -i 's/--name "Jayraldines Catering"/--name "JayraldinesCateringTablet"/g' setup/build_android.sh
!rm -rf /content/jayraldinescateringsystem/Tablet/.buildozer
!bash setup/build_android.sh

# 7. Auto-download the finished APK installer
import glob
from google.colab import files

apks = glob.glob("dist/*.apk") + glob.glob("*.apk") + glob.glob("bin/*.apk")
if apks:
    print(f"\n✅ Build Successful! Downloading APK: {apks[0]}")
    files.download(apks[0])
else:
    print("\n❌ Build finished but APK file was not located.")
```

3. Once the build finishes, your browser will automatically start downloading the `Jayraldines_Catering.apk` installer file!
