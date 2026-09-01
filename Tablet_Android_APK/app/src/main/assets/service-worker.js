// Cache-first for everything — 100% offline standalone kiosk PWA
const CACHE_NAME = "jc-kiosk-shell-v58";
const SHELL_FILES = [
  "/",
  "/index.html",
  "/css/styles.css",
  "/js/app.js",
  "/js/api.js",
  "/js/icons.js",
  "/js/lottie-helper.js",
  "/js/animations-data.js",
  "/js/slider.js",
  "/js/state.js",
  "/js/views.js",
  "/js/wizard.js",
  "/js/settings.js",
  "/js/sqlite.js",
  "/js/repository.js",
  "/js/importer.js",
  "/js/exporter.js",
  "/js/terms.js",
  "/vendor/lottie.min.js",
  "/vendor/sql-wasm.js",
  "/vendor/sql-wasm.wasm",
  "/vendor/jspdf.umd.min.js",
  "/vendor/xlsx.full.min.js",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/logo.png",
  "/images/hero-buffet-1.jpg",
  "/images/hero-buffet-2.jpg",
  "/images/hero-buffet-3.jpg",
  "/animations/catering-loading.json",
  "/animations/logo-splash.json",
  "/animations/cloche-idle.json",
  "/animations/cloche-tap-burst.json",
  "/animations/icon-package.json",
  "/animations/icon-calendar.json",
  "/animations/icon-utensils.json",
  "/animations/icon-filetext.json",
  "/animations/icon-shield-check.json",
  "/animations/icon-users.json",
  "/animations/icon-lock.json",
  "/animations/icon-theme-toggle.json",
  "/animations/icon-fullscreen.json",
  "/animations/icon-settings-gear.json",
  "/animations/booking-success.json",
  "/animations/empty-plate.json",
  "/animations/toast-success.json",
  "/animations/toast-error.json",
  "/animations/toast-info.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((resp) => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return resp;
      });
    })
  );
});
