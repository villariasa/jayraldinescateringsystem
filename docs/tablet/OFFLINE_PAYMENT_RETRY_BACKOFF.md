# Offline Payment Sync Retry Backoff

Adjusts retry backoff for tablet payment synchronization during unstable ballroom WiFi.
Initial delay 5 seconds with exponential backoff capped at 60 seconds prevents server connection saturation.
