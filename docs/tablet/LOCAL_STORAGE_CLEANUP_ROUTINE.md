# Local Storage Cleanup Routine on Tablet App Exit

## Privacy & Storage Hygiene
- Clears temporary session tokens and uncommitted cart cache on app close.
- Retains offline booking records and printer hardware pairing.
- Prevents IndexedDB storage quota exhaustion on long-running kiosks.
