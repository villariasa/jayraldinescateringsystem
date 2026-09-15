# Desktop Application Standalone Launcher & Mutex Lock

## 1. Process Management
- **Single Instance Mutex**: Utilizes `QSharedMemory` and Windows named mutex (`JayraldinesCateringSingleInstanceMutex`) to prevent duplicate application instances.
- **Automatic Wakeup**: If a second instance is launched, sends IPC focus signal to restore the existing primary window.
