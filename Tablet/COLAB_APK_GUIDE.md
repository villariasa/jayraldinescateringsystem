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

# 1. Clone the updated repository
!rm -rf jayraldinescateringsystem
!git clone https://github.com/villariasa/jayraldinescateringsystem.git
%cd jayraldinescateringsystem/Tablet

# 2. Install Python 3.11, OpenJDK 17, and build utilities
!apt-get update -qq
!apt-get install -y -qq software-properties-common
!add-apt-repository -y ppa:deadsnakes/ppa
!apt-get update -qq
!apt-get install -y -qq python3.11 python3.11-venv python3.11-dev openjdk-17-jdk autoconf automake libtool zlib1g-dev rsync

# 3. Create Python 3.11 Virtual Environment
!rm -rf .venv
!python3.11 -m venv .venv
!.venv/bin/pip install --upgrade pip -q
!.venv/bin/pip install -r requirements.txt -q
!.venv/bin/pip install buildozer==1.5.0 cython==0.29.33 -q

# 4. Set Environment Variables
import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
os.environ["PATH"] = f"/content/jayraldinescateringsystem/Tablet/.venv/bin:/usr/lib/jvm/java-17-openjdk-amd64/bin:{os.environ['PATH']}"

# 5. Build Android APK
!bash setup/build_android.sh

# 6. Auto-download the finished APK installer to your device
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
