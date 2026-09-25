import { api } from "./api.js";
import { openModal, closeModal, toast, escapeHtml, statusPill } from "./views.js";
import { wizard, peso } from "./state.js";
import { mountWizard, openLightCalendarModal } from "./wizard.js";
import { openOwnerSettings, openOrderDetailModal, openLiveDbConfigModal } from "./settings.js";
import { icon } from "./icons.js";
import { mountLandingSlider } from "./slider.js";
import { mountLottie, mountHoverLottie, playTapBurst } from "./lottie-helper.js";
// Side-effect import: auto-scroll focused inputs/selects above the software keyboard
import "./keyboard-scroll.js";


const app = document.getElementById("app");

if ("serviceWorker" in navigator) {
  if (api.isInstalledApp()) {
    navigator.serviceWorker.getRegistrations().then((regs) => {
      for (const reg of regs) reg.unregister().catch(() => {});
    }).catch(() => {});
  } else {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    });
  }
}

// Mount vibrant catering animation on initial loading screen (no static app logo)
const splashLoader = document.getElementById("splash-lottie-loader");
if (splashLoader) {
  mountLottie(splashLoader, "catering-loading", { loop: true, speed: 1.0 });
}

// Theme management
export function getTheme() {
  return localStorage.getItem("jc_theme") || "light";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("jc_theme", theme);
  document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
    const labelEl = btn.querySelector(".nav-action-label");
    if (labelEl) {
      labelEl.textContent = theme === "light" ? "Dark Mode" : "Light Mode";
    }
    btn.title = theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode";
    // Update static SVG icon in the nav-action-icon wrapper (landing page header)
    const iconWrap = btn.querySelector(".nav-action-icon");
    if (iconWrap && !iconWrap.querySelector(".lottie-icon-container")) {
      // Only update if it's a static icon (no Lottie container inside)
      iconWrap.innerHTML = icon(theme === "light" ? "moon" : "sun");
    }
  });
}

export function toggleTheme() {
  applyTheme(getTheme() === "light" ? "dark" : "light");
}

applyTheme(getTheme());

export function showTransitionLoading(message = "Preparing kiosk for next guest…", duration = 950) {
  let splash = document.getElementById("transition-splash");
  if (!splash) {
    splash = document.createElement("div");
    splash.id = "transition-splash";
    splash.className = "app-splash";
    document.body.appendChild(splash);
  }
  splash.innerHTML = `
    <div class="splash-content">
      <div id="transition-lottie-loader" class="splash-animation-stage"></div>
      <h2 class="splash-title" style="font-size:22px; margin-bottom:6px;">Jayraldine's Catering</h2>
      <p class="splash-subtitle" style="font-size:14px; opacity:0.9;">${escapeHtml(message)}</p>
      <div class="splash-loader-progress">
        <div class="splash-loader-bar"></div>
      </div>
    </div>
  `;
  // Mount vibrant catering animation on transition splash
  const tLoader = splash.querySelector("#transition-lottie-loader");
  if (tLoader) {
    mountLottie(tLoader, "catering-loading", { loop: true, speed: 1.0 });
  }
  splash.classList.remove("hidden");
  splash.style.opacity = "1";
  splash.style.visibility = "visible";

  return new Promise((resolve) => {
    setTimeout(() => {
      splash.style.opacity = "0";
      splash.style.transition = "opacity 0.4s ease, visibility 0.4s ease";
      setTimeout(() => {
        splash.classList.add("hidden");
        splash.style.visibility = "hidden";
        resolve();
      }, 400);
    }, duration);
  });
}

// ── Screen Rendering ─────────────────────────────────────────────────

export function showScreen(screen) {
  if (screen === "wizard") {
    app.innerHTML = "";
    mountWizard(app, () => showScreen("landing"));
  } else {
    mountLanding();
  }
}

function mountLanding() {
  app.innerHTML = `
    <div class="landing-shell">
      <!-- Top Brand Navigation Bar -->
      <header class="landing-header">
        <div class="landing-brand">
          <img src="icons/logo.png" alt="Jayraldine Logo" class="brand-logo" id="landing-brand-logo">
          <div class="brand-text">
            <span class="brand-title">Jayraldine's Catering</span>
            <span class="brand-subtitle">Interactive Tablet Booking Kiosk</span>
          </div>
        </div>

        <div class="landing-nav-actions">
          <button class="nav-action-btn theme-toggle-btn" id="landing-theme-toggle" title="Toggle Dark/Light Mode">
            <div class="nav-icon-container" id="nav-lottie-theme">
              ${icon("sun")}
            </div>
            <span class="nav-action-label">${getTheme() === "light" ? "Dark Mode" : "Light Mode"}</span>
          </button>

          <button class="nav-action-btn" id="landing-open-orders" title="View Recent Bookings">
            <div class="nav-icon-container" id="nav-lottie-orders">
              ${icon("shoppingBag")}
            </div>
            <span class="nav-action-label">Bookings</span>
          </button>

          <button class="nav-action-btn nav-admin-btn" id="landing-open-admin" title="Owner Management &amp; Settings">
            <div class="nav-icon-container" id="nav-lottie-admin">
              ${icon("shield")}
            </div>
            <span class="nav-action-label">Admin</span>
          </button>
        </div>
      </header>

      <!-- Live DB Offline Warning Banner -->
      <div id="live-db-alert-bar" style="display:none; background:linear-gradient(90deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.2) 100%); border-bottom:1.5px solid #F59E0B; padding:10px 24px; color:#FEF3C7; font-size:13px; font-weight:600; align-items:center; justify-content:space-between; gap:12px;">
        <span style="display:flex; align-items:center; gap:8px;">${icon("wifiOff")} <b>Offline Mode Active</b>: Operating with local offline catalog. Bookings will automatically synchronize once reconnected.</span>
        <button id="btn-reconnect-live-db" class="btn btn-sm" style="background:#D97706; color:#fff; border:none; padding:5px 14px; border-radius:6px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">${icon("refresh")} Connect Live DB</button>
      </div>

      <!-- Split Interactive Hero Stage -->
      <main class="landing-stage">
        <!-- Left: Marketing Showcase & Catering Pitch -->
        <section class="stage-left">
          <div class="hero-badge">
            ${icon("sparkles")} Live Centralized Catering System
          </div>
          <h1 class="hero-headline">
            Delightful Bites,<br>
            <span class="text-gold">Unforgettable Memories.</span>
          </h1>
          <p class="hero-lead">
            Welcome to Cebu's premier catering service. Connected directly to the live central database server for real-time dish availability and instant billing.
          </p>

          <div class="hero-cta-group">
            <button class="btn btn-cta btn-lg" id="btn-start-order">
              <div class="lottie-icon-container" id="lottie-cloche-idle"></div>
              <span id="btn-start-order-text">Start Event Booking</span>
              ${icon("arrowRight")}
            </button>
          </div>

          <div class="hero-perks">
            <div class="perk-pill">
              ${icon("checkCircle")} Live LAN Database Sync
            </div>
            <div class="perk-pill">
              ${icon("checkCircle")} Instant PDF Receipt
            </div>
            <div class="perk-pill">
              ${icon("checkCircle")} Flexible Downpayment
            </div>
          </div>
        </section>

        <!-- Right: Dynamic Visual Slider Showcase -->
        <section class="stage-right">
          <div id="landing-slider-mount" class="slider-viewport"></div>
        </section>
      </main>

      <!-- Bottom Quick-Access Bar -->
      <footer class="landing-quick-bar">
        <div class="quick-bar-inner">
          <button class="quick-btn" id="quick-packages">
            <div class="quick-icon-wrap" id="quick-lottie-package">
              ${icon("package")}
            </div>
            <div class="quick-info">
              <span class="quick-title">Buffet Packages</span>
              <span class="quick-sub">Silver, Gold, Platinum &amp; custom pax</span>
            </div>
          </button>

          <button class="quick-btn" id="quick-menu">
            <div class="quick-icon-wrap" id="quick-lottie-menu">
              ${icon("utensils")}
            </div>
            <div class="quick-info">
              <span class="quick-title">Dish Catalog</span>
              <span class="quick-sub">Mains, seafood, desserts &amp; drinks</span>
            </div>
          </button>

          <button class="quick-btn" id="quick-terms">
            <div class="quick-icon-wrap" id="quick-lottie-terms">
              ${icon("fileText")}
            </div>
            <div class="quick-info">
              <span class="quick-title">Catering Terms</span>
              <span class="quick-sub">Policies, deposits &amp; venue rules</span>
            </div>
          </button>
        </div>
      </footer>
    </div>
  `;

  // Initialize interactive dynamic slider
  mountLandingSlider("landing-slider-mount");

  // Mount Lottie animations on Interactive Hero & Nav
  const clocheBtnEl = document.getElementById("lottie-cloche-idle");
  if (clocheBtnEl) {
    mountLottie(clocheBtnEl, "cloche-idle", { loop: true, speed: 0.8 });
  }

  // Setup micro-animations on quick buttons
  mountHoverLottie(document.getElementById("quick-packages"), document.getElementById("quick-lottie-package"), "icon-package");
  mountHoverLottie(document.getElementById("quick-menu"), document.getElementById("quick-lottie-menu"), "icon-utensils");
  mountHoverLottie(document.getElementById("quick-terms"), document.getElementById("quick-lottie-terms"), "icon-filetext");

  // Wire Live DB Reconnect button
  document.getElementById("btn-reconnect-live-db")?.addEventListener("click", async () => {
    toast("Connecting to Central Server & Database…", "info");
    const ok = await api.ensureLiveConnection(true);
    if (ok) {
      toast("Connected to Live Central Database! Loaded live menu & packages.", "success");
      renderHome();
    } else {
      const cur = localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.host : "192.168.1.32:8000");
      toast(`Could not reach server at ${cur}. Ensure desktop app is running.`, "error");
    }
  });

  document.getElementById("nav-live-db-status")?.addEventListener("click", async () => {
    toast("Checking Live Central Database link…", "info");
    const ok = await api.ensureLiveConnection(true);
    if (ok) {
      toast("Live Central Database is connected and synchronized!", "success");
    } else {
      toast("Live Central Database is offline. Ensure server is running.", "error");
    }
  });

  // Wire CTA buttons with Live DB validation
  const startOrderBtn = document.getElementById("btn-start-order");
  startOrderBtn?.addEventListener("click", async (e) => {
    if (!api.isLiveConnected()) {
      api.ensureLiveConnection(false).catch(() => {});
    }
    playTapBurst(e.clientX, e.clientY);
    wizard.reset();
    showScreen("wizard");
  });

  document.getElementById("landing-theme-toggle")?.addEventListener("click", () => {
    toggleTheme();
  });

  document.getElementById("landing-open-orders")?.addEventListener("click", async () => {
    openRecentOrdersModal();
  });

  document.getElementById("landing-open-admin")?.addEventListener("click", () => {
    openOwnerSettings("bookings");
  });

  document.getElementById("quick-packages")?.addEventListener("click", async () => {
    openPackagesQuickModal();
  });

  document.getElementById("quick-menu")?.addEventListener("click", async () => {
    openMenuQuickModal();
  });

  document.getElementById("quick-terms")?.addEventListener("click", () => {
    openTermsQuickModal();
  });
}

export function updateLiveDbBadge(connected, server = "") {
  const dot = document.getElementById("live-dot");
  const text = document.getElementById("live-status-text");
  const alertBar = document.getElementById("live-db-alert-bar");
  const startBtn = document.getElementById("btn-start-order");
  const startText = document.getElementById("btn-start-order-text");

  if (dot && text) {
    if (connected) {
      dot.style.background = "#10B981";
      dot.style.boxShadow = "0 0 10px rgba(16, 185, 129, 0.8)";
      text.textContent = "Live DB: Connected";
      text.style.color = "#34D399";
      if (alertBar) alertBar.style.display = "none";
      if (startBtn) {
        startBtn.removeAttribute("disabled");
        startBtn.style.opacity = "1";
        startBtn.style.cursor = "pointer";
      }
      if (startText) startText.textContent = "Start Event Booking";
      const clocheCta = document.getElementById("start-order");
      if (clocheCta) {
        clocheCta.style.opacity = "1";
        clocheCta.style.filter = "none";
      }
    } else {
      dot.style.background = "#F59E0B";
      dot.style.boxShadow = "0 0 10px rgba(245, 158, 11, 0.8)";
      text.textContent = "Offline Mode";
      text.style.color = "#FBBF24";
      if (alertBar) {
        alertBar.style.display = "flex";
        alertBar.style.background = "linear-gradient(90deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.2) 100%)";
        alertBar.style.borderBottom = "1.5px solid #F59E0B";
        alertBar.style.color = "#FEF3C7";
      }
      if (startBtn) {
        startBtn.removeAttribute("disabled");
        startBtn.style.opacity = "1";
        startBtn.style.cursor = "pointer";
      }
      if (startText) startText.textContent = "Start Event Booking (Offline)";
      const clocheCta = document.getElementById("start-order");
      if (clocheCta) {
        clocheCta.style.opacity = "1";
        clocheCta.style.filter = "none";
      }
    }
  }
}

// ── Quick Modals ─────────────────────────────────────────────────────

async function openPackagesQuickModal() {
  const pkgs = await api.getPackages();
  openModal({
    id: "quick-packages-modal",
    title: `${icon("package")} Catering Buffet Packages`,
    large: true,
    bodyHtml: `
      <div class="packages-showcase-grid">
        ${pkgs.map((p) => `
          <div class="pkg-showcase-card">
            ${p.image ? `
              <div style="width:100%; height:140px; border-radius:12px; overflow:hidden; margin-bottom:12px; background:var(--input-bg);">
                <img src="${p.image}" alt="${escapeHtml(p.name)}" style="width:100%; height:100%; object-fit:cover;">
              </div>
            ` : ""}
            <div class="pkg-badge">Per Set</div>
            <h3 class="pkg-name">${escapeHtml(p.name)}</h3>
            <div class="pkg-rate">${peso(p.price_per_pax)}<span class="pkg-unit"> / set</span></div>
            <p class="pkg-desc">${escapeHtml(p.description || "Complete buffet service with setup, tableware and crew.")}</p>
            <div class="pkg-meta">
              <span>${icon("user")} Min 1 Set (4 dishes good for 22 person)</span>
            </div>
            <button class="btn btn-primary btn-block select-pkg-start-btn" data-pkg-id="${p.id}" style="margin-top:14px;">
              Select &amp; Start Booking ${icon("arrowRight")}
            </button>
          </div>
        `).join("")}
      </div>
    `,
  });

  document.querySelectorAll(".select-pkg-start-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pkgId = Number(btn.dataset.pkgId);
      closeModal("quick-packages-modal");
      wizard.reset();
      wizard.draft.package.id = pkgId;
      showScreen("wizard");
    });
  });
}

async function openMenuQuickModal() {
  const grouped = await api.getMenuItemsGrouped();
  const cats = Object.keys(grouped);
  let activeCat = cats[0] || "";

  const renderContent = (body) => {
    body.innerHTML = `
      <div class="modal-category-tabs">
        ${cats.map((c) => `
          <button class="btn ${c === activeCat ? "btn-primary" : "btn-secondary"} cat-filter-btn" data-cat="${escapeHtml(c)}">
            ${escapeHtml(c)} (${grouped[c].length})
          </button>
        `).join("")}
      </div>
      <div class="menu-preview-grid">
        ${(grouped[activeCat] || []).map((m) => `
          <div class="menu-preview-item">
            ${m.image ? `
              <div style="width:100%; height:100px; border-radius:8px; overflow:hidden; margin-bottom:8px; background:var(--input-bg);">
                <img src="${m.image}" alt="${escapeHtml(m.name)}" style="width:100%; height:100%; object-fit:cover;">
              </div>
            ` : ""}
            <div class="menu-preview-title">${escapeHtml(m.name)}</div>
            <div class="menu-preview-category">${escapeHtml(m.category)}</div>
            ${m.price > 0 ? `<div class="menu-preview-price">+ ${peso(m.price)}</div>` : `<div class="menu-preview-included">Included in Package</div>`}
          </div>
        `).join("")}
      </div>
    `;

    body.querySelectorAll(".cat-filter-btn").forEach((b) => {
      b.addEventListener("click", () => {
        activeCat = b.dataset.cat;
        renderContent(body);
      });
    });
  };

  openModal({
    id: "quick-menu-modal",
    title: `${icon("utensils")} Catering Dishes &amp; Specialties`,
    large: true,
    bodyHtml: (body) => renderContent(body),
  });
}

async function openTermsQuickModal() {
  const terms = await api.terms();
  openModal({
    id: "quick-terms-modal",
    title: `${icon("fileText")} Catering Terms, Guidelines &amp; Policies`,
    large: true,
    bodyHtml: `
      <div class="terms-preview-body">
        <div style="font-size:13px; color:var(--text-muted); margin-bottom:14px;">
          Version: <b>${escapeHtml(terms.version)}</b> &bull; Effective for all kiosk bookings
        </div>
        <div class="terms-scroll-area">
          ${terms.html || `<p>${escapeHtml(terms.content)}</p>`}
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn btn-primary" id="btn-terms-start-order">
        I Understand &amp; Agree &bull; Start Booking ${icon("arrowRight")}
      </button>
    `,
  });

  document.getElementById("btn-terms-start-order")?.addEventListener("click", () => {
    closeModal("quick-terms-modal");
    wizard.reset();
    showScreen("wizard");
  });
}

// ── Recent Orders modal ──────────────────────────────────────────────

async function openRecentOrdersModal() {
  const orders = await api.getOrders();
  openModal({
    id: "recent-orders-modal",
    title: `${icon("shoppingBag")} Recent Catering Bookings (${orders.length})`,
    large: true,
    bodyHtml: `
      <div class="orders-card-grid">
        ${orders.map((o) => `
          <div class="order-kiosk-card">
            <div class="order-kiosk-header">
              <span class="order-ref-pill">${escapeHtml(o.booking_ref || `JC-${o.booking_id}`)}</span>
              ${statusPill(o.status || "Confirmed")}
            </div>
            <div class="order-kiosk-customer">${escapeHtml(o.customer || "Walk-in Guest")}</div>
            <div class="order-kiosk-row" style="margin-top:6px; font-size:12.5px; color:var(--text-muted);">
              <span>${icon("calendar")} ${escapeHtml(o.event_date || "TBD")}</span>
              <span>${icon("clock")} ${escapeHtml(o.event_time || "6:00 PM")}</span>
            </div>
            <div class="order-kiosk-row" style="margin-top:4px; font-size:12.5px; color:var(--text-muted);">
              <span>${icon("package")} ${escapeHtml(o.package_name || "Buffet Package")} (${o.pax || 60} pax)</span>
            </div>
            <div class="order-kiosk-row" style="margin-top:8px; border-top:1px dashed var(--border); padding-top:8px;">
              <span style="font-size:12px; color:var(--text-muted);">Total Order Price</span>
              <span style="font-weight:800; font-size:16px; color:var(--gold);">${peso(o.total)}</span>
            </div>
            <div class="order-kiosk-row" style="font-size:12px;">
              <span style="color:var(--success); font-weight:600;">Paid: ${peso(o.paid)}</span>
              <span style="color:var(--accent); font-weight:600;">Bal: ${peso(o.balance)}</span>
            </div>
            <div style="margin-top:12px; display:flex; gap:8px; border-top:1px solid var(--border); padding-top:10px;">
              <button class="btn btn-secondary" style="flex:1; padding:8px 12px; font-size:13px;" data-receipt="${o.booking_id}">
                ${icon("printer")} Receipt PDF
              </button>
              <button class="btn btn-primary" style="padding:8px 14px; font-size:13px;" data-detail="${o.booking_id}">
                ${icon("info")} Details
              </button>
            </div>
          </div>
        `).join("") || `<div style="grid-column: 1 / -1; padding:36px; text-align:center; color:var(--text-muted);">No orders recorded yet.</div>`}
      </div>
    `,
  });

  document.querySelectorAll("#recent-orders-modal [data-receipt]").forEach((el) => {
    el.addEventListener("click", () => api.downloadReceipt(Number(el.dataset.receipt)));
  });

  document.querySelectorAll("#recent-orders-modal [data-detail]").forEach((el) => {
    el.addEventListener("click", () => openOrderDetailModal(Number(el.dataset.detail)));
  });
}

function dismissSplash() {
  const splash = document.getElementById("app-splash");
  if (splash && !splash.classList.contains("hidden")) {
    setTimeout(() => {
      splash.classList.add("hidden");
      setTimeout(() => splash.remove(), 600);
    }, 1100);
  }
}

window.addEventListener("kiosk:home", async (e) => {
  wizard.reset();
  const withTransition = e && e.detail && e.detail.transition;
  if (withTransition) {
    const msg = e.detail.message || "Thank you! Preparing kiosk for the next guest…";
    const p = showTransitionLoading(msg, 950);
    await renderHome();
    await p;
  } else {
    renderHome();
  }
});

// React live when landing images or categories change in settings
window.addEventListener("kiosk:landing-images-changed", () => {
  const sliderContainer = document.getElementById("landing-slider-mount") || document.getElementById("landing-hero-slider-container");
  if (sliderContainer) {
    mountLandingSlider(sliderContainer);
  }
});

window.addEventListener("kiosk:categories-changed", (e) => {
  // Forward the explicit new order so the showcase re-renders immediately
  // without re-reading from SQLite (which may still hold the old server
  // value if the background sync hasn't settled yet).
  const explicitCats = (e && e.detail && Array.isArray(e.detail.categories) && e.detail.categories.length)
    ? e.detail.categories : null;
  mountLandingMenuShowcase(explicitCats);
});

window.addEventListener("jayraldines:sync-completed", () => {
  mountLandingMenuShowcase();
});

renderHome();

async function renderHome() {
  const currentTheme = getTheme();
  app.innerHTML = `
    <header class="header kiosk-header-fixed">
      <div class="brand">
        <div class="brand-avatar-wrap">
          <img src="icons/logo.png" alt="Jayraldine's Catering" class="brand-logo">
        </div>
        <div>
          <h1 class="brand-title">Jayraldine's Catering</h1>
          <p class="brand-subtitle">Delicious Moments, Perfectly Catered</p>
        </div>
      </div>
      <div class="header-nav-actions">
        <button class="nav-action-btn theme-toggle-btn" id="theme-btn" title="Toggle Theme">
          <div class="nav-action-icon">
            ${icon(currentTheme === "light" ? "moon" : "sun")}
          </div>
          <span class="nav-action-label">${currentTheme === "light" ? "Dark Mode" : "Light Mode"}</span>
        </button>
        <button class="nav-action-btn" id="fullscreen-btn" title="Toggle Fullscreen">
          <div class="nav-action-icon" id="fullscreen-icon-wrap">
            ${icon("fullscreen")}
          </div>
          <span class="nav-action-label">Fullscreen</span>
        </button>
        <button class="nav-action-btn" id="calendar-btn" title="Event Calendar">
          <div class="nav-action-icon">
            ${icon("calendar")}
          </div>
          <span class="nav-action-label">Calendar</span>
        </button>
        <button class="nav-action-btn" id="owner-settings-btn" title="Admin Settings">
          <div class="nav-action-icon">
            ${icon("settings")}
          </div>
          <span class="nav-action-label">Settings</span>
        </button>
        <!-- Mobile-only: single toggle button that opens the dropdown -->
        <button class="nav-mobile-toggle" id="nav-mobile-toggle-btn" title="Menu" aria-expanded="false">
          <div class="nav-action-icon">
            ${icon("grid")}
          </div>
        </button>
      </div>
      <!-- Mobile dropdown panel (hidden by default, shown via .open class) -->
      <div class="nav-mobile-dropdown" id="nav-mobile-dropdown" role="menu">
        <button class="nav-dropdown-item" id="connection-btn-mob" title="Database Connection &amp; Credentials">
          <div class="nav-dropdown-item-icon">
            ${icon("database")}
          </div>
          <div class="nav-dropdown-item-text">
            <span class="nav-dropdown-label">Database Connection</span>
            <span class="nav-dropdown-desc">Setup Server IP &amp; Credentials</span>
          </div>
        </button>
        <div class="nav-dropdown-divider"></div>
        <button class="nav-dropdown-item theme-toggle-btn" id="theme-btn-mob" title="Toggle Theme">
          <div class="nav-dropdown-item-icon">
            ${icon(currentTheme === "light" ? "moon" : "sun")}
          </div>
          <div class="nav-dropdown-item-text">
            <span class="nav-dropdown-label">${currentTheme === "light" ? "Dark Mode" : "Light Mode"}</span>
            <span class="nav-dropdown-desc">${currentTheme === "light" ? "Switch to dark theme" : "Switch to light theme"}</span>
          </div>
        </button>
        <div class="nav-dropdown-divider"></div>
        <button class="nav-dropdown-item" id="fullscreen-btn-mob" title="Toggle Fullscreen">
          <div class="nav-dropdown-item-icon">
            ${icon("fullscreen")}
          </div>
          <div class="nav-dropdown-item-text">
            <span class="nav-dropdown-label">Fullscreen</span>
            <span class="nav-dropdown-desc">Expand to full screen</span>
          </div>
        </button>
        <div class="nav-dropdown-divider"></div>
        <button class="nav-dropdown-item" id="calendar-btn-mob" title="Event Calendar">
          <div class="nav-dropdown-item-icon">
            ${icon("calendar")}
          </div>
          <div class="nav-dropdown-item-text">
            <span class="nav-dropdown-label">Calendar</span>
            <span class="nav-dropdown-desc">View upcoming events</span>
          </div>
        </button>
        <div class="nav-dropdown-divider"></div>
        <button class="nav-dropdown-item" id="settings-btn-mob" title="Admin Settings">
          <div class="nav-dropdown-item-icon">
            ${icon("settings")}
          </div>
          <div class="nav-dropdown-item-text">
            <span class="nav-dropdown-label">Settings</span>
            <span class="nav-dropdown-desc">Admin &amp; configuration</span>
          </div>
        </button>
        ${!api.isInstalledApp() ? `
        <div class="nav-dropdown-divider apk-download-only-web"></div>
        <a class="nav-dropdown-item apk-download-only-web" href="/download-apk" id="apk-download-btn-mob" title="Download Tablet Android APK" style="text-decoration:none;">
          <div class="nav-dropdown-item-icon" style="background: rgba(16, 185, 129, 0.15); border: 1.5px solid rgba(16, 185, 129, 0.35); color: #10B981;">
            ${icon("download")}
          </div>
          <div class="nav-dropdown-item-text">
            <span class="nav-dropdown-label" style="color: #10B981; font-weight:800;">Download Tablet APK</span>
            <span class="nav-dropdown-desc">Direct Android App (.apk)</span>
          </div>
        </a>
        ` : ""}
      </div>
    </header>
    <!-- Live DB Offline Warning Banner -->
    <div id="live-db-alert-bar" style="display:none; background:linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.15) 100%); border-bottom:1.5px solid #F59E0B; padding:10px 24px; color:#B45309; font-size:13px; font-weight:600; align-items:center; justify-content:space-between; gap:12px; z-index:99; position:relative; flex-wrap:wrap;">
      <span style="display:flex; align-items:center; gap:8px;">
        ${icon("wifiOff")} <b>Offline Mode Active</b>: Browsing offline menu. Bookings will automatically synchronize once connected to the server.
      </span>
      <div style="display:flex; align-items:center; gap:8px;">
        <button id="btn-setup-live-db" class="btn btn-sm" style="background:#2563EB; color:#fff; border:none; padding:7px 16px; border-radius:8px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">${icon("settings")} Setup IP &amp; Credentials</button>
        <button id="btn-reconnect-live-db" class="btn btn-sm" style="background:#D97706; color:#fff; border:none; padding:7px 16px; border-radius:8px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">${icon("refresh")} Connect Server</button>
      </div>
    </div>

    <main class="main kiosk-landing-main" id="home-main">
      <div class="kiosk-landing-wrapper">
        
        <!-- Hero Split Section (Text & Start Order on Left, Atmospheric Image on Right) -->
        <section class="kiosk-hero-split-section">
          
          <div class="kiosk-hero-content-col">
            <div class="kiosk-hero-intro-text">
              <h2 class="kiosk-hero-title">
                Welcome!<br>
                Let's Create Your<br>
                <span class="kiosk-title-highlight">Perfect Catering</span>
              </h2>
              <div class="kiosk-hero-accent-bar"></div>
              <p class="kiosk-hero-tagline">
                Choose your package, customize your menu, and we'll take care of the rest.
              </p>

              <!-- Start Order CTA Button directly under hero text -->
              <div class="kiosk-cloche-cta-wrapper" id="start-order" role="button" tabindex="0" title="Touch to begin ordering">
                <div class="kiosk-cloche-circle">
                  <div class="kiosk-cloche-icon" id="hero-cloche-icon-box">
                    <div id="cloche-lottie-wrap" class="lottie-icon-container"></div>
                  </div>
                  <div class="kiosk-cloche-text-group">
                    <div class="kiosk-cloche-text-main">START ORDER</div>
                    <div class="kiosk-cloche-text-sub">Tap to begin booking</div>
                  </div>
                  <div class="kiosk-cloche-arrow">${icon("chevronRight")}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Hero Slider / Atmospheric Catering Showcase Right Column -->
          <div class="kiosk-hero-visual-col">
            <div id="landing-hero-slider-container" class="kiosk-slider-outer-frame"></div>
          </div>

        </section>

        <!-- ONE Horizontal White Rounded Card for 4 Benefits in ONE ROW -->
        <section class="kiosk-benefits-card-container">
          <div class="kiosk-pill-highlights">
            
            <div class="kiosk-pill-item" id="benefit-booking">
              <div class="kiosk-pill-icon-box">
                <div class="lottie-icon-container" id="lottie-benefit-booking">${icon("calendar")}</div>
              </div>
              <div class="kiosk-pill-text">
                <span class="kiosk-pill-title">Easy Booking</span>
                <span class="kiosk-pill-desc">Simple steps to book your catering</span>
              </div>
            </div>

            <div class="kiosk-pill-item-divider"></div>

            <div class="kiosk-pill-item" id="benefit-quality">
              <div class="kiosk-pill-icon-box">
                <div class="lottie-icon-container" id="lottie-benefit-quality">${icon("shieldCheck")}</div>
              </div>
              <div class="kiosk-pill-text">
                <span class="kiosk-pill-title">Fresh &amp; Quality</span>
                <span class="kiosk-pill-desc">We serve only the best for you</span>
              </div>
            </div>

            <div class="kiosk-pill-item-divider"></div>

            <div class="kiosk-pill-item" id="benefit-service">
              <div class="kiosk-pill-icon-box">
                <div class="lottie-icon-container" id="lottie-benefit-service">${icon("users")}</div>
              </div>
              <div class="kiosk-pill-text">
                <span class="kiosk-pill-title">Trusted Service</span>
                <span class="kiosk-pill-desc">Many happy events and customers</span>
              </div>
            </div>

            <div class="kiosk-pill-item-divider"></div>

            <div class="kiosk-pill-item" id="benefit-secure">
              <div class="kiosk-pill-icon-box">
                <div class="lottie-icon-container" id="lottie-benefit-secure">${icon("lock")}</div>
              </div>
              <div class="kiosk-pill-text">
                <span class="kiosk-pill-title">Secure &amp; Private</span>
                <span class="kiosk-pill-desc">Your data is safe and protected</span>
              </div>
            </div>

          </div>
        </section>

        <!-- Bottom Quick Options Section -->
        <section class="kiosk-quick-options-section">
          <div class="quick-options-header-wrap">
            <h3 class="quick-options-heading">Quick Options</h3>
            <div class="quick-options-accent-bar"></div>
          </div>
          
          <div class="quick-options-grid">
            
            <button class="quick-option-card" id="quick-packages-btn">
              <div class="quick-opt-icon-circle">
                <div class="lottie-icon-container" id="lottie-quick-packages">${icon("package")}</div>
              </div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">View Packages</span>
                <span class="quick-opt-desc">Browse all available packages</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

            <button class="quick-option-card" id="quick-menu-btn">
              <div class="quick-opt-icon-circle">
                <div class="lottie-icon-container" id="lottie-quick-menu">${icon("utensils")}</div>
              </div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">View Menu</span>
                <span class="quick-opt-desc">Browse all dishes &amp; specialties</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

            <button class="quick-option-card" id="quick-events-btn">
              <div class="quick-opt-icon-circle">
                <div class="lottie-icon-container" id="lottie-quick-events">${icon("calendar")}</div>
              </div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">Event Types</span>
                <span class="quick-opt-desc">Choose your event type</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

            <button class="quick-option-card" id="quick-orders-btn">
              <div class="quick-opt-icon-circle">
                <div class="lottie-icon-container" id="lottie-quick-orders">${icon("fileText")}</div>
              </div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">View Orders</span>
                <span class="quick-opt-desc">Check your order history</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

          </div>
        </section>

        <!-- Live Menu Showcase Section directly on the Dashboard / Landing Page -->
        <section class="kiosk-menu-showcase-section" id="kiosk-menu-showcase">
          <!-- Sticky head: Culinary Showcase heading/search/actions + Category
               Tabs Bar all pin together below the header once scrolled to. -->
          <div class="landing-menu-sticky-head" id="landing-menu-sticky-head">
            <div class="menu-showcase-header">
              <div class="menu-showcase-title-area">
                <div class="menu-showcase-badge">${icon("utensils")} Culinary Showcase</div>
                <h3 class="menu-showcase-heading">Explore Our Catering Menu</h3>
                <p class="menu-showcase-sub">Browse our chef-crafted entrees, specialties, sides, and signature desserts</p>
                <div class="quick-options-accent-bar" style="margin-top:6px;"></div>
              </div>
              <div class="menu-showcase-actions">
                <div class="menu-showcase-search-box">
                  <span class="search-box-icon">${icon("search")}</span>
                  <input type="text" id="landing-menu-search-input" placeholder="Search dishes, beef, pasta..." autocomplete="off" />
                  <button type="button" id="landing-menu-search-clear" class="search-box-clear" style="display:none;" title="Clear search">${icon("close")}</button>
                </div>
              </div>
            </div>

            <!-- Category Tabs Bar -->
            <div class="kiosk-cat-bar" id="landing-menu-categories">
              <button class="kiosk-cat-pill active" data-cat="ALL">
                ${icon("utensils")} All Dishes
              </button>
            </div>
          </div>

          <!-- Dish Cards Grid -->
          <div class="menu-showcase-grid" id="landing-menu-grid">
            <div style="padding:32px 16px; text-align:center; color:var(--text-muted); grid-column:1/-1;">
              Loading catering menu…
            </div>
          </div>

          <div class="menu-showcase-footer-action">
            <button class="btn btn-primary btn-lg" id="btn-landing-menu-start-order">
              ${icon("check")} Start Order &amp; Select Dishes
            </button>
          </div>
        </section>

      </div>
    </main>
  `;

  // Mount Cloche idle in START ORDER button icon only
  const clocheWrap = document.getElementById("cloche-lottie-wrap");
  if (clocheWrap) {
    mountLottie(clocheWrap, "cloche-idle", { loop: true });
  }

  // START ORDER tap with live connection validation and particle burst
  const startOrderBtn = document.getElementById("start-order");
  startOrderBtn?.addEventListener("click", async () => {
    if (!api.isLiveConnected()) {
      api.ensureLiveConnection(false).catch(() => {});
    }
    playTapBurst(document.getElementById("hero-cloche-icon-box") || startOrderBtn, "cloche-tap-burst");
    setTimeout(() => {
      openTermsModal();
    }, 180);
  });

  // Setup Live DB Connection & Credentials button wiring
  document.getElementById("btn-setup-live-db")?.addEventListener("click", () => {
    openLiveDbConfigModal();
  });

  // Reconnect Live DB button wiring in warning banner
  document.getElementById("btn-reconnect-live-db")?.addEventListener("click", async () => {
    toast("Connecting to Live Central Database…", "info");
    const ok = await api.ensureLiveConnection(true);
    if (ok) {
      toast("Connected to Live Central Database! Loaded live packages & dishes.", "success");
      updateLiveDbBadge(true);
      window.dispatchEvent(new CustomEvent("kiosk:home"));
    } else {
      toast("Could not reach Live Central Database (192.168.1.10:8000). Check Wi-Fi.", "error");
      updateLiveDbBadge(false);
      openLiveDbConfigModal();
    }
  });

  // Live DB badge in header click handler opens Setup modal directly
  document.getElementById("nav-live-db-status")?.addEventListener("click", () => {
    openLiveDbConfigModal();
  });

  // Mount Benefit card icons (constrained icon box divs only)
  mountLottie(document.getElementById("lottie-benefit-booking"), "icon-calendar", { loop: true, speed: 0.75 });
  mountLottie(document.getElementById("lottie-benefit-quality"), "icon-shield-check", { loop: true, speed: 0.75 });
  mountLottie(document.getElementById("lottie-benefit-service"), "icon-users", { loop: true, speed: 0.75 });
  mountLottie(document.getElementById("lottie-benefit-secure"), "icon-lock", { loop: true, speed: 0.75 });

  // Mount Quick Options hover Lottie on each inner .lottie-icon-container
  // (mountHoverLottie clears the static fallback icon before inserting Lottie SVG)
  mountHoverLottie(document.getElementById("lottie-quick-packages"), "icon-package", { speed: 1.2 });
  mountHoverLottie(document.getElementById("lottie-quick-menu"), "icon-utensils", { speed: 1.2 });
  mountHoverLottie(document.getElementById("lottie-quick-events"), "icon-calendar", { speed: 1.2 });
  mountHoverLottie(document.getElementById("lottie-quick-orders"), "icon-filetext", { speed: 1.2 });
  // ── Mobile dropdown toggle wiring ──────────────────────────────────────
  const mobileToggleBtn = document.getElementById("nav-mobile-toggle-btn");
  const mobileDropdown = document.getElementById("nav-mobile-dropdown");

  function closeMobileDropdown() {
    mobileDropdown?.classList.remove("open");
    mobileToggleBtn?.setAttribute("aria-expanded", "false");
  }

  mobileToggleBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = mobileDropdown.classList.toggle("open");
    mobileToggleBtn.setAttribute("aria-expanded", String(isOpen));
  });

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    if (!mobileDropdown?.contains(e.target) && e.target !== mobileToggleBtn) {
      closeMobileDropdown();
    }
  });

  // Mobile dropdown: theme
  document.getElementById("theme-btn-mob")?.addEventListener("click", () => {
    toggleTheme();
    const isLight = getTheme() === "light";
    // Sync desktop button icon
    const iconWrap = document.querySelector("#theme-btn .nav-action-icon");
    if (iconWrap) iconWrap.innerHTML = icon(isLight ? "moon" : "sun");
    // Sync mobile dropdown icon + labels
    const mobIcon = document.querySelector("#theme-btn-mob .nav-dropdown-item-icon");
    if (mobIcon) mobIcon.innerHTML = icon(isLight ? "moon" : "sun");
    const mobLabel = document.querySelector("#theme-btn-mob .nav-dropdown-label");
    const mobDesc = document.querySelector("#theme-btn-mob .nav-dropdown-desc");
    if (mobLabel) mobLabel.textContent = isLight ? "Dark Mode" : "Light Mode";
    if (mobDesc) mobDesc.textContent = isLight ? "Switch to dark theme" : "Switch to light theme";
    closeMobileDropdown();
  });

  // Mobile dropdown: fullscreen
  document.getElementById("fullscreen-btn-mob")?.addEventListener("click", () => {
    toggleFullscreen();
    closeMobileDropdown();
  });

  // Mobile dropdown: connection setup
  document.getElementById("connection-btn-mob")?.addEventListener("click", () => {
    openLiveDbConfigModal();
    closeMobileDropdown();
  });

  // Mobile dropdown: calendar
  document.getElementById("calendar-btn-mob")?.addEventListener("click", () => {
    openLightCalendarModal(null, { viewOnly: true });
    closeMobileDropdown();
  });

  // Mobile dropdown: settings
  document.getElementById("settings-btn-mob")?.addEventListener("click", () => {
    openOwnerSettings("bookings");
    closeMobileDropdown();
  });

  // Header Nav buttons (theme/fullscreen/settings) use static SVG icons — no Lottie animation.

  // Update theme icon statically when toggled (desktop buttons)
  document.getElementById("theme-btn").addEventListener("click", () => {
    toggleTheme();
    const isLight = getTheme() === "light";
    const iconWrap = document.querySelector("#theme-btn .nav-action-icon");
    if (iconWrap) iconWrap.innerHTML = icon(isLight ? "moon" : "sun");
  });
  document.getElementById("fullscreen-btn").addEventListener("click", toggleFullscreen);
  document.getElementById("calendar-btn").addEventListener("click", () => {
    openLightCalendarModal(null, { viewOnly: true });
  });
  document.getElementById("owner-settings-btn").addEventListener("click", () => {
    openOwnerSettings("bookings");
  });

  // Mount Quick Options clicks
  document.getElementById("quick-packages-btn")?.addEventListener("click", openQuickPackagesModal);
  document.getElementById("quick-menu-btn")?.addEventListener("click", () => openQuickMenuModal());
  document.getElementById("quick-events-btn")?.addEventListener("click", openQuickEventTypesModal);
  document.getElementById("quick-addons-btn")?.addEventListener("click", openQuickAddonsModal);
  document.getElementById("quick-orders-btn")?.addEventListener("click", () => openOwnerSettings("bookings"));

  // Mount the Hero Slider
  const sliderContainer = document.getElementById("landing-hero-slider-container");
  if (sliderContainer) {
    mountLandingSlider(sliderContainer);
  }

  // Track the fixed header's real height so the Explore Menu category bar
  // (position: sticky) can pin itself directly beneath it, not underneath.
  const kioskHeaderEl = document.querySelector(".kiosk-header-fixed");
  if (kioskHeaderEl) {
    const updateKioskHeaderH = () => {
      const h = kioskHeaderEl.getBoundingClientRect().height || kioskHeaderEl.offsetHeight || 78;
      document.documentElement.style.setProperty("--kiosk-header-h", `${Math.round(h)}px`);
    };
    updateKioskHeaderH();
    requestAnimationFrame(updateKioskHeaderH);
    window.addEventListener("resize", updateKioskHeaderH, { passive: true });
    if (window.ResizeObserver) {
      new ResizeObserver(updateKioskHeaderH).observe(kioskHeaderEl);
    }
  }

  // Mount the Live Menu Showcase on the Landing Page / Dashboard
  mountLandingMenuShowcase();

  dismissSplash();
}

function toggleFullscreen() {
  const btn = document.getElementById("fullscreen-btn");
  const updateFullscreenBtn = (isFullscreen) => {
    if (!btn) return;
    const labelEl = btn.querySelector(".nav-action-label");
    if (labelEl) {
      labelEl.textContent = isFullscreen ? "Exit Full" : "Fullscreen";
    }
  };

  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.().then(() => {
      updateFullscreenBtn(true);
    }).catch(() => {});
  } else {
    document.exitFullscreen?.().then(() => {
      updateFullscreenBtn(false);
    }).catch(() => {});
  }
}

// ── Terms & Conditions modal ─────────────────────────────────────────

async function openTermsModal() {
  const terms = await api.terms();
  const modalId = "terms-modal";
  openModal({
    id: modalId,
    title: `${icon("fileText")} ${escapeHtml(terms.title)}`,
    large: true,
    bodyHtml: `
      <div class="terms-text" id="terms-scroll-box" style="max-height:48vh; overflow-y:auto; -webkit-overflow-scrolling:touch; padding:18px 20px; border-radius:var(--radius);">${terms.html || escapeHtml(terms.text)}</div>
      <div style="margin-top:16px; background:var(--card-elevated); padding:16px 20px; border-radius:var(--radius-md); border:1.5px solid var(--border); box-shadow:var(--shadow-sm);">
        <label style="display:flex; align-items:center; gap:12px; cursor:pointer; font-weight:700; font-size:14px; color:var(--text);" id="terms-ack-label">
          <input type="checkbox" id="terms-ack" disabled style="width:22px; height:22px; accent-color:var(--accent); cursor:pointer;">
          <span>${escapeHtml(terms.acknowledgement_label)}</span>
        </label>
        <p id="scroll-hint" style="color:var(--gold); font-size:12.5px; font-weight:600; margin:8px 0 0 34px; display:flex; align-items:center; gap:6px;">
          ${icon("info")} Please scroll to the very bottom of the terms above to unlock the agreement checkbox.
        </p>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Cancel</button>
      <button class="btn btn-primary" id="agree-btn" disabled>${icon("check")} I Agree &amp; Start Order</button>
    `,
  });

  const body = document.querySelector(`#${modalId}-body`);
  const scrollBox = body?.querySelector("#terms-scroll-box");
  const ackBox = body?.querySelector("#terms-ack");
  const hint = body?.querySelector("#scroll-hint");
  const agreeBtn = document.querySelector(`#${modalId} #agree-btn`);

  const checkScrolledToBottom = () => {
    if (!scrollBox || !ackBox) return;
    const isAtBottom = scrollBox.scrollHeight - scrollBox.scrollTop <= scrollBox.clientHeight + 40;
    if (isAtBottom && ackBox.disabled) {
      ackBox.disabled = false;
      hint.style.color = "var(--success)";
      hint.innerHTML = `${icon("checkCircle")} Terms fully reviewed! You may now check the box above to proceed.`;
      toast("Terms reviewed! Check the box to start order.", "success");
    }
  };

  scrollBox?.addEventListener("scroll", checkScrolledToBottom);
  body?.addEventListener("scroll", checkScrolledToBottom);
  setTimeout(checkScrolledToBottom, 400);

  ackBox?.addEventListener("change", () => {
    agreeBtn.disabled = !ackBox.checked;
    if (ackBox.checked) {
      hint.innerHTML = `<span style="color:var(--success); font-weight:700;">${icon("checkCircle")} Agreement confirmed. Click below to start your order!</span>`;
    } else {
      hint.innerHTML = `${icon("checkCircle")} Terms fully reviewed! You may now check the box above to proceed.`;
    }
  });

  agreeBtn?.addEventListener("click", () => {
    closeModal(modalId);
    startOrderWizard();
  });
}

function startOrderWizard() {
  mountWizard(app);
}

// ── Quick Option: View Packages Modal ────────────────────────────────
async function openQuickPackagesModal() {
  if (!api.isLiveConnected()) {
    api.ensureLiveConnection(false).catch(() => {});
  }
  let packages = [];
  try {
    packages = await api.getPackages();
  } catch (err) {
    toast(err.message, "error");
    return;
  }
  openModal({
    id: "quick-packages-modal",
    title: `${icon("package")} Catering Buffet Packages (${packages.length})`,
    large: true,
    bodyHtml: `
      <div style="margin-bottom:16px;">
        <p style="font-size:14px; color:var(--text-muted); margin:0;">
          Explore our handcrafted buffet packages. Each package includes an elegant buffet setup, food warmers, chafing dishes, and professional banquet service.
        </p>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:18px;">
        ${packages.map(p => `
          <div class="card" style="padding:16px; display:flex; flex-direction:column; gap:12px; border:1.5px solid var(--border); border-radius:var(--radius-lg); overflow:hidden;">
            <div style="width:100%; height:140px; border-radius:var(--radius-md); overflow:hidden; background:var(--input-bg); position:relative;">
              ${p.image ? `<img src="${p.image}" alt="${escapeHtml(p.name)}" style="width:100%; height:100%; object-fit:cover;">` : `
                <div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:linear-gradient(135deg, rgba(225,29,72,0.15) 0%, rgba(16,26,54,0.4) 100%); color:var(--accent);">
                  ${icon("package")}
                  <span style="font-size:12px; font-weight:700; color:var(--text-muted); margin-top:4px;">Buffet Tier</span>
                </div>
              `}
              <span class="pill pill-partial" style="position:absolute; top:10px; right:10px; font-size:11px; font-weight:700; box-shadow:var(--shadow-sm);">Min 1 Set (4 dishes good for 22 person)</span>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
              <div>
                <h3 style="font-size:17.5px; font-weight:800; color:var(--text); margin:0 0 4px;">${escapeHtml(p.name)}</h3>
              </div>
              <div style="text-align:right;">
                <span style="font-size:20px; font-weight:800; color:var(--gold);">${peso(p.price_per_pax)}</span>
                <span style="font-size:11px; color:var(--text-muted); display:block;">/ set</span>
              </div>
            </div>
            
            <p style="font-size:13px; color:var(--text-muted); line-height:1.5; margin:0; flex:1;">
              ${escapeHtml(p.description || "A sumptuous selection of main entrees, rice, desserts, and bottomless iced tea.")}
            </p>

            <button class="btn btn-primary btn-block select-quick-pkg-btn" data-pkg-id="${p.id}" data-pkg-name="${escapeHtml(p.name)}" data-pkg-price="${p.price_per_pax}" data-pkg-min="${p.min_pax}" style="margin-top:auto; font-weight:700;">
              ${icon("check")} Select This Package &amp; Book
            </button>
          </div>
        `).join("")}
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
    `,
  });

  document.querySelectorAll("#quick-packages-modal .select-quick-pkg-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const pkgId = Number(btn.dataset.pkgId);
      const pkgName = btn.dataset.pkgName;
      const pricePerPax = Number(btn.dataset.pkgPrice);
      const minPax = Number(btn.dataset.pkgMin) || 30;
      const foundPkg = packages.find(pkg => Number(pkg.id) === pkgId);

      wizard.reset();
      wizard.draft.package.id = pkgId;
      wizard.draft.package.name = pkgName;
      wizard.draft.package.pricePerPax = pricePerPax;
      wizard.draft.package.minPax = minPax;
      wizard.draft.package.description = foundPkg ? foundPkg.description : "";
      wizard.draft.package.image = foundPkg ? foundPkg.image : "";
      wizard.draft.package.baseTotal = pricePerPax * (wizard.draft.event.pax || 60);

      closeModal("quick-packages-modal");
      openTermsModal();
    });
  });
}

// ── Quick Option: Event Types Modal ──────────────────────────────────
// Description/icon copy for known occasion names - purely cosmetic. The
// actual LIST of occasions itself must come from the real `occasions` table
// (catering.db, synced down via /api/sync/lan-sync) so it reflects whatever
// Admin has configured in Settings > Occasion Types, instead of a fixed
// 6-item array baked into this file that never matched what's actually
// manageable on the desktop app.
const _EVENT_TYPE_COPY = {
  "wedding": { icon: "sparkles", desc: "Celebrate eternal love with romantic table setups, gourmet carving stations, and five-star banquet service." },
  "birthday": { icon: "heart", desc: "From joyful kiddie parties to grand milestone jubilees, delight all your guests with hearty savory feasts." },
  "debut": { icon: "sparkles", desc: "Make her once-in-a-lifetime debut magical with stylish themed buffet staging and VIP service." },
  "corporate event": { icon: "clipboardCheck", desc: "Punctual, professional catering for executive conferences, product launches, and annual banquets." },
  "anniversary": { icon: "calendar", desc: "Honor cherished years together with custom menus tailored to family favorites and loved ones." },
  "christening": { icon: "heart", desc: "Welcome the newest member of the family with a warm, joyful celebration spread." },
  "graduation": { icon: "sparkles", desc: "Celebrate every milestone achievement with a feast worthy of the occasion." },
  "holiday party": { icon: "calendar", desc: "Gather everyone together for a festive, memorable holiday celebration." },
};
const _DEFAULT_EVENT_TYPE_COPY = { icon: "utensils", desc: "Let us tailor a personalized catering package for your upcoming celebration." };

async function openQuickEventTypesModal() {
  let occasions = [];
  try {
    occasions = await api.getOccasions();
  } catch (err) {
    console.warn("[app] getOccasions failed, using fallback list:", err);
  }
  const events = (occasions && occasions.length ? occasions : [{ name: "Wedding" }, { name: "Birthday" }, { name: "Debut" }])
    .map(o => {
      const copy = _EVENT_TYPE_COPY[String(o.name || "").trim().toLowerCase()] || _DEFAULT_EVENT_TYPE_COPY;
      return { title: o.name, icon: copy.icon, desc: copy.desc };
    });

  openModal({
    id: "quick-events-modal",
    title: `${icon("calendar")} Choose Your Occasion / Event Type`,
    large: true,
    bodyHtml: `
      <div style="margin-bottom:18px;">
        <p style="font-size:14px; color:var(--text-muted); margin:0;">
          Select your upcoming celebration to begin planning your personalized catering package.
        </p>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:16px;">
        ${events.map(ev => `
          <div class="card" style="padding:20px; display:flex; flex-direction:column; gap:10px; border:1.5px solid var(--border); border-radius:var(--radius-lg);">
            <div style="width:44px; height:44px; border-radius:var(--radius-md); background:rgba(225, 29, 72, 0.12); color:var(--accent); display:flex; align-items:center; justify-content:center;">
              ${icon(ev.icon)}
            </div>
            <h3 style="font-size:16.5px; font-weight:800; color:var(--text); margin:0;">${ev.title}</h3>
            <p style="font-size:13px; color:var(--text-muted); line-height:1.45; margin:0; flex:1;">${ev.desc}</p>
            <button class="btn btn-primary btn-block select-quick-event-btn" data-occasion="${ev.title}" style="margin-top:auto;">
              ${icon("arrowRight")} Plan ${ev.title}
            </button>
          </div>
        `).join("")}
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
    `,
  });

  document.querySelectorAll("#quick-events-modal .select-quick-event-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const occasion = btn.dataset.occasion;
      wizard.reset();
      wizard.draft.event.occasion = occasion;
      closeModal("quick-events-modal");
      openTermsModal();
    });
  });
}

// ── Landing Page Live Menu Showcase ──────────────────────────────────
// Sorts a set/array of category names by the admin-defined order from
// Settings > Menu Categories (mc_sort), falling back to alphabetical for any
// category not yet known to that order (e.g. freshly imported data).
async function _sortCategoriesByAdminOrder(cats) {
  let adminOrder = [];
  try {
    adminOrder = await api.getMenuCategories();
  } catch (err) {
    console.warn("[app] Failed to fetch admin category order, falling back to alphabetical:", err);
  }
  const rank = new Map(adminOrder.map((name, i) => [String(name).toLowerCase().trim(), i]));
  return Array.from(cats).sort((a, b) => {
    const keyA = String(a).toLowerCase().trim();
    const keyB = String(b).toLowerCase().trim();
    const ra = rank.has(keyA) ? rank.get(keyA) : 999;
    const rb = rank.has(keyB) ? rank.get(keyB) : 999;
    if (ra !== rb) return ra - rb;
    return String(a).localeCompare(String(b));
  });
}

// explicitCategories: when the caller already knows the new order (e.g. right
// after a drag-and-drop reorder save) it passes the array directly so we
// never hit the race where a background sync returns the *old* server order
// and overwrites SQLite before we read it.
async function mountLandingMenuShowcase(explicitCategories = null) {
  const container = document.getElementById("kiosk-menu-showcase");
  if (!container) return;

  let allMenuItems = [];
  try {
    allMenuItems = await api.getMenuItems();
  } catch (err) {
    console.warn("[app] Failed to fetch menu items for landing showcase:", err);
  }

  const stickyHead = container.querySelector("#landing-menu-sticky-head");
  const catBar = container.querySelector("#landing-menu-categories");
  const grid = container.querySelector("#landing-menu-grid");
  const searchInput = container.querySelector("#landing-menu-search-input");
  const clearBtn = container.querySelector("#landing-menu-search-clear");
  const startOrderBtn = container.querySelector("#btn-landing-menu-start-order");

  // Use the caller-supplied list when available (avoids SQLite round-trip race);
  // otherwise fall back to the authoritative DB query.
  let adminCategories;
  if (explicitCategories && Array.isArray(explicitCategories) && explicitCategories.length > 0) {
    adminCategories = explicitCategories;
  } else {
    adminCategories = await api.getMenuCategories();
  }
  let categories = adminCategories.filter(cat =>
    allMenuItems.some(it => (it.category || "").trim().toLowerCase() === cat.trim().toLowerCase())
  );
  if (!categories.length) {
    const fallbackSet = new Set();
    allMenuItems.forEach(it => { if (it.category) fallbackSet.add(it.category.trim()); });
    categories = Array.from(fallbackSet).sort();
  }
  const catRankMap = new Map(categories.map((c, idx) => [String(c).toLowerCase().trim(), idx]));

  const activePill = catBar ? catBar.querySelector(".kiosk-cat-pill.active") : null;
  const prevCat = activePill ? activePill.dataset.cat : null;
  let selectedCat = (prevCat && (prevCat === "ALL" || categories.some(c => c.toLowerCase() === prevCat.toLowerCase()))) ? prevCat : "ALL";
  let searchQuery = searchInput?.value || "";

  // Toggle a `.is-stuck` class on the sticky showcase head (heading/search/
  // actions + category bar) once it has actually pinned to the top, so it
  // can pick up a subtle shadow/border.
  if (stickyHead && !stickyHead._stickyWatcherMounted) {
    stickyHead._stickyWatcherMounted = true;
    let stuckRaf = null;
    const checkStuck = () => {
      stuckRaf = null;
      const topOffset = parseFloat(getComputedStyle(stickyHead).top) || 0;
      const isStuck = stickyHead.getBoundingClientRect().top <= topOffset + 0.5;
      stickyHead.classList.toggle("is-stuck", isStuck);
    };
    window.addEventListener("scroll", () => {
      if (stuckRaf) return;
      stuckRaf = requestAnimationFrame(checkStuck);
    }, { passive: true });
    checkStuck();
  }

  // Render category chips
  if (catBar) {
    catBar.innerHTML = `
      <button class="kiosk-cat-pill ${selectedCat === 'ALL' ? 'active' : ''}" data-cat="ALL">
        ${icon("utensils")} All Dishes (${allMenuItems.length})
      </button>
      ${categories.map((cat, idx) => {
        const count = allMenuItems.filter(it => (it.category || "").trim().toLowerCase() === cat.toLowerCase()).length;
        const isActive = selectedCat.toLowerCase() === cat.toLowerCase();
        return `
          <button class="kiosk-cat-pill ${isActive ? 'active' : ''}" data-cat="${escapeHtml(cat)}">
            <span class="cat-pill-order-badge" style="display:inline-flex; align-items:center; justify-content:center; min-width:20px; height:20px; padding:0 5px; border-radius:10px; background:${isActive ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.08)'}; font-size:11px; font-weight:800; margin-right:6px;">${idx + 1}</span>
            ${escapeHtml(cat)} (${count})
          </button>
        `;
      }).join("")}
    `;

    catBar.querySelectorAll(".kiosk-cat-pill").forEach(pill => {
      pill.addEventListener("click", () => {
        catBar.querySelectorAll(".kiosk-cat-pill").forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        selectedCat = pill.dataset.cat || "ALL";
        renderDishes();
      });
    });
  }

  function renderDishes() {
    if (!grid) return;
    const q = (searchQuery || "").trim().toLowerCase();
    const filtered = allMenuItems.filter(it => {
      const matchCat = selectedCat === "ALL" || (it.category || "").trim().toLowerCase() === selectedCat.toLowerCase();
      if (!matchCat) return false;
      if (!q) return true;
      const name = (it.name || "").toLowerCase();
      const desc = (it.description || "").toLowerCase();
      const cat = (it.category || "").toLowerCase();
      return name.includes(q) || desc.includes(q) || cat.includes(q);
    });

    if (selectedCat === "ALL") {
      filtered.sort((a, b) => {
        const catA = String(a.category || "").toLowerCase().trim();
        const catB = String(b.category || "").toLowerCase().trim();
        const ra = catRankMap.has(catA) ? catRankMap.get(catA) : 999;
        const rb = catRankMap.has(catB) ? catRankMap.get(catB) : 999;
        if (ra !== rb) return ra - rb;
        return String(a.name || "").localeCompare(String(b.name || ""));
      });
    }

    if (!filtered.length) {
      grid.innerHTML = `
        <div class="menu-showcase-empty" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
          <div style="display:inline-flex; align-items:center; justify-content:center; width:52px; height:52px; border-radius:50%; background:var(--input-bg); margin-bottom:8px; color:var(--text-muted);">${icon("utensils")}</div>
          <h4 style="font-size: 16px; font-weight: 700; color: var(--text); margin: 0 0 6px;">No dishes found</h4>
          <p style="font-size: 13px; color: var(--text-muted); margin: 0 0 14px;">
            ${q ? `No menu item matched "${escapeHtml(searchQuery)}".` : "No dishes available in this category."}
          </p>
          ${q ? `<button class="btn btn-secondary btn-sm" id="btn-showcase-reset-search">${icon("close")} Clear Filter</button>` : ""}
        </div>
      `;
      grid.querySelector("#btn-showcase-reset-search")?.addEventListener("click", () => {
        if (searchInput) searchInput.value = "";
        searchQuery = "";
        if (clearBtn) clearBtn.style.display = "none";
        renderDishes();
      });
      return;
    }

    grid.innerHTML = filtered.map(it => {
      const catKey = String(it.category || "").toLowerCase().trim();
      const catOrderPrefix = catRankMap.has(catKey) ? `${catRankMap.get(catKey) + 1}. ` : "";
      return `
      <div class="card showcase-dish-card" data-dish-id="${it.id}">
        <div class="showcase-card-img-wrap">
          ${it.image ? `
            <img src="${it.image}" alt="${escapeHtml(it.name)}" class="showcase-card-img" loading="lazy">
          ` : `
            <div class="showcase-card-placeholder">
              ${icon("utensils")}
              <span class="placeholder-cat">${escapeHtml(it.category || "Specialty")}</span>
            </div>
          `}
          <span class="showcase-card-badge">${catOrderPrefix}${escapeHtml(it.category || "Main Dish")}</span>
          ${it.price > 0 ? `
            <span class="showcase-card-price">${peso(it.price)}</span>
          ` : `
            <span class="showcase-card-price included">Buffet Included</span>
          `}
        </div>
        <div class="showcase-card-body">
          <h4 class="showcase-card-title">${escapeHtml(it.name)}</h4>
          <p class="showcase-card-desc">${escapeHtml(it.description || "Freshly cooked catering specialty prepared to perfection.")}</p>
          <div class="showcase-card-footer">
            <button class="btn btn-ghost btn-sm btn-dish-detail" data-dish-id="${it.id}">
              ${icon("info")} View Details
            </button>
            <button class="btn btn-primary btn-sm btn-dish-book">
              ${icon("arrowRight")} Order
            </button>
          </div>
        </div>
      </div>
    `;
    }).join("");

    grid.querySelectorAll(".btn-dish-detail").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const dId = btn.dataset.dishId;
        const item = allMenuItems.find(x => String(x.id) === String(dId));
        if (item) openDishDetailModal(item);
      });
    });

    grid.querySelectorAll(".showcase-dish-card").forEach(card => {
      card.addEventListener("click", () => {
        const dId = card.dataset.dishId;
        const item = allMenuItems.find(x => String(x.id) === String(dId));
        if (item) openDishDetailModal(item);
      });
    });

    grid.querySelectorAll(".btn-dish-book").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openTermsModal();
      });
    });
  }

  renderDishes();

  if (!container._searchWired) {
    container._searchWired = true;
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        searchQuery = searchInput.value;
        if (clearBtn) {
          clearBtn.style.display = searchQuery ? "flex" : "none";
        }
        renderDishes();
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (searchInput) {
          searchInput.value = "";
          searchInput.focus();
        }
        searchQuery = "";
        clearBtn.style.display = "none";
        renderDishes();
      });
    }

    if (startOrderBtn) {
      startOrderBtn.addEventListener("click", () => {
        openTermsModal();
      });
    }
  }
}
window.mountLandingMenuShowcase = mountLandingMenuShowcase; // accepts optional explicitCategories[]


// ── Quick Option: Menu Viewing Modal ──────────────────────────────────
async function openQuickMenuModal({ initialCategory = "ALL", initialSearch = "" } = {}) {
  if (!api.isLiveConnected()) {
    api.ensureLiveConnection(false).catch(() => {});
  }
  let items = [];
  try {
    items = await api.getMenuItems();
  } catch (err) {
    toast(err.message, "error");
    return;
  }

  const categoriesSet = new Set();
  items.forEach(i => {
    if (i.category) categoriesSet.add(i.category.trim());
  });
  const categories = await _sortCategoriesByAdminOrder(categoriesSet);

  openModal({
    id: "quick-menu-modal",
    title: `${icon("utensils")} Catering Menu &amp; Dishes (${items.length})`,
    large: true,
    allowSwipeUpFullscreen: true,
    bodyHtml: (bodyEl) => {
      let activeCat = initialCategory || "ALL";
      let filterText = initialSearch || "";

      bodyEl.innerHTML = `
        <div style="margin-bottom:16px;">
          <p style="font-size:14px; color:var(--text-muted); margin:0 0 12px;">
            Explore our complete catering catalog: savory entrees, roasted meats, pasta, seafood, and decadent desserts.
          </p>
          <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
            <div style="flex:1; min-width:240px; position:relative;">
              <input type="text" id="modal-menu-search" class="input" placeholder="Search menu dishes, beef, chicken..." value="${escapeHtml(filterText)}" style="padding-left:36px; width:100%; border-radius:24px;">
              <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--text-muted); display:flex;">
                ${icon("search")}
              </span>
              <button id="modal-menu-clear-search" style="position:absolute; right:10px; top:50%; transform:translateY(-50%); background:transparent; border:none; color:var(--text-muted); cursor:pointer; display:${filterText ? 'flex' : 'none'}; padding:4px;">
                ${icon("close")}
              </button>
            </div>
          </div>
        </div>

        <div class="kiosk-cat-bar" id="modal-cat-bar" style="margin-bottom:16px; padding-bottom:6px;">
          <button class="kiosk-cat-pill ${activeCat === 'ALL' ? 'active' : ''}" data-cat="ALL">
            ${icon("utensils")} All Dishes (${items.length})
          </button>
          ${categories.map(cat => {
            const count = items.filter(it => (it.category || "").trim().toLowerCase() === cat.toLowerCase()).length;
            return `
              <button class="kiosk-cat-pill ${activeCat.toLowerCase() === cat.toLowerCase() ? 'active' : ''}" data-cat="${escapeHtml(cat)}">
                ${escapeHtml(cat)} (${count})
              </button>
            `;
          }).join("")}
        </div>

        <div id="modal-dishes-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr)); gap:16px; max-height:55vh; overflow-y:auto; padding-right:4px;">
        </div>
      `;

      const gridEl = bodyEl.querySelector("#modal-dishes-grid");
      const searchEl = bodyEl.querySelector("#modal-menu-search");
      const clearSearchEl = bodyEl.querySelector("#modal-menu-clear-search");
      const catBarEl = bodyEl.querySelector("#modal-cat-bar");

      function refreshGrid() {
        const q = filterText.trim().toLowerCase();
        const filtered = items.filter(it => {
          const matchCat = activeCat === "ALL" || (it.category || "").trim().toLowerCase() === activeCat.toLowerCase();
          if (!matchCat) return false;
          if (!q) return true;
          return (it.name || "").toLowerCase().includes(q) ||
                 (it.description || "").toLowerCase().includes(q) ||
                 (it.category || "").toLowerCase().includes(q);
        });

        if (!filtered.length) {
          gridEl.innerHTML = `
            <div style="grid-column:1/-1; padding:48px 16px; text-align:center; color:var(--text-muted);">
              <div style="display:inline-flex; align-items:center; justify-content:center; width:52px; height:52px; border-radius:50%; background:var(--input-bg); margin-bottom:8px; color:var(--text-muted);">${icon("search")}</div>
              <h4 style="margin:0 0 6px; color:var(--text);">No dishes match your filter</h4>
              <p style="font-size:13px; margin:0;">Try a different keyword or select another category above.</p>
            </div>
          `;
          return;
        }

        gridEl.innerHTML = filtered.map(it => `
          <div class="card showcase-dish-card" data-dish-id="${it.id}" style="border:1.5px solid var(--border); border-radius:var(--radius-lg); overflow:hidden; display:flex; flex-direction:column; cursor:pointer;">
            <div class="showcase-card-img-wrap" style="height:140px; position:relative; overflow:hidden; background:var(--input-bg);">
              ${it.image ? `
                <img src="${it.image}" alt="${escapeHtml(it.name)}" class="showcase-card-img" style="width:100%; height:100%; object-fit:cover;">
              ` : `
                <div class="showcase-card-placeholder" style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; background:linear-gradient(135deg, rgba(225, 29, 72, 0.12) 0%, rgba(20, 30, 51, 0.5) 100%); color:var(--gold);">
                  ${icon("utensils")}
                  <span style="font-size:11px; font-weight:700;">${escapeHtml(it.category || "Specialty")}</span>
                </div>
              `}
              <span class="showcase-card-badge" style="position:absolute; top:8px; left:8px; font-size:11px; font-weight:700; background:rgba(15,23,42,0.85); color:#FFF; padding:3px 8px; border-radius:12px; backdrop-filter:blur(4px);">${escapeHtml(it.category || "Specialty")}</span>
              ${it.price > 0 ? `
                <span class="showcase-card-price" style="position:absolute; top:8px; right:8px; font-size:12px; font-weight:800; background:var(--gold); color:#111; padding:3px 8px; border-radius:12px;">${peso(it.price)}</span>
              ` : `
                <span class="showcase-card-price" style="position:absolute; top:8px; right:8px; font-size:11px; font-weight:700; background:rgba(16,185,129,0.9); color:#FFF; padding:3px 8px; border-radius:12px;">Buffet Included</span>
              `}
            </div>
            <div style="padding:12px 14px; display:flex; flex-direction:column; flex:1; gap:6px;">
              <h4 style="font-size:15px; font-weight:800; color:var(--text); margin:0;">${escapeHtml(it.name)}</h4>
              <p style="font-size:12.5px; color:var(--text-muted); line-height:1.45; margin:0; flex:1;">${escapeHtml(it.description || "Prepared fresh to order with authentic seasonings.")}</p>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:8px; border-top:1px solid var(--border);">
                <button class="btn btn-ghost btn-sm btn-modal-dish-detail" data-dish-id="${it.id}" style="padding:4px 8px; font-size:11px;">
                  ${icon("info")} View Details
                </button>
                <button class="btn btn-primary btn-sm btn-modal-dish-select" style="padding:4px 10px; font-size:11px; font-weight:700;">
                  ${icon("check")} Select &amp; Book
                </button>
              </div>
            </div>
          </div>
        `).join("");

        gridEl.querySelectorAll(".btn-modal-dish-detail").forEach(btn => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const itm = items.find(x => String(x.id) === String(btn.dataset.dishId));
            if (itm) openDishDetailModal(itm);
          });
        });

        gridEl.querySelectorAll(".showcase-dish-card").forEach(card => {
          card.addEventListener("click", () => {
            const itm = items.find(x => String(x.id) === String(card.dataset.dishId));
            if (itm) openDishDetailModal(itm);
          });
        });

        gridEl.querySelectorAll(".btn-modal-dish-select").forEach(btn => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            closeModal("quick-menu-modal");
            openTermsModal();
          });
        });
      }

      catBarEl.querySelectorAll(".kiosk-cat-pill").forEach(btn => {
        btn.addEventListener("click", () => {
          catBarEl.querySelectorAll(".kiosk-cat-pill").forEach(p => p.classList.remove("active"));
          btn.classList.add("active");
          activeCat = btn.dataset.cat || "ALL";
          refreshGrid();
        });
      });

      searchEl.addEventListener("input", () => {
        filterText = searchEl.value;
        clearSearchEl.style.display = filterText ? "flex" : "none";
        refreshGrid();
      });

      clearSearchEl.addEventListener("click", () => {
        searchEl.value = "";
        filterText = "";
        clearSearchEl.style.display = "none";
        searchEl.focus();
        refreshGrid();
      });

      refreshGrid();
    },
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn btn-primary" id="btn-quick-menu-start-booking">
        ${icon("cloche")} Start Booking Now
      </button>
    `,
  });

  document.querySelector("#quick-menu-modal #btn-quick-menu-start-booking")?.addEventListener("click", () => {
    closeModal("quick-menu-modal");
    openTermsModal();
  });
}

// ── Quick Option: Dish Detail Modal ──────────────────────────────────
function openDishDetailModal(item) {
  openModal({
    id: "dish-details-modal",
    title: `${icon("utensils")} ${escapeHtml(item.name)}`,
    bodyHtml: `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="width:100%; height:230px; border-radius:var(--radius-md); overflow:hidden; background:var(--input-bg); border:1.5px solid var(--border); display:flex; align-items:center; justify-content:center; position:relative;">
          ${item.image ? `
            <img src="${item.image}" alt="${escapeHtml(item.name)}" style="width:100%; height:100%; object-fit:cover;">
          ` : `
            <div style="display:flex; flex-direction:column; align-items:center; gap:8px; color:var(--text-muted);">
              ${icon("utensils")}
              <span style="font-size:14px; font-weight:700;">${escapeHtml(item.name)}</span>
            </div>
          `}
          <span style="position:absolute; top:12px; left:12px; font-size:11px; font-weight:800; background:rgba(15,23,42,0.85); color:#FFF; padding:4px 10px; border-radius:20px; backdrop-filter:blur(4px); text-transform:uppercase; letter-spacing:0.04em;">
            ${escapeHtml(item.category || "Main Entree")}
          </span>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; background:var(--card-elevated); padding:14px 18px; border-radius:var(--radius-md); border:1.5px solid var(--border);">
          <div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Course / Category</div>
            <div style="font-size:17px; font-weight:800; color:var(--text);">${escapeHtml(item.category || "Main Entree")}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Pricing Tier</div>
            <div style="font-family:'Outfit',sans-serif; font-size:20px; font-weight:800; color:${item.price > 0 ? "var(--gold)" : "var(--success)"};">
              ${item.price > 0 ? peso(item.price) : "Buffet Included"}
            </div>
          </div>
        </div>

        <div>
          <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin:0 0 6px; letter-spacing:0.04em;">Dish Description &amp; Preparation</h4>
          <p style="font-size:14px; line-height:1.6; color:var(--text); margin:0; background:var(--input-bg); padding:14px 16px; border-radius:var(--radius-sm); border:1px solid var(--border);">
            ${escapeHtml(item.description || "Prepared fresh with premium ingredients seasoned to culinary perfection by Jayraldine's kitchen team.")}
          </p>
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn btn-primary" id="btn-dish-detail-book-now">
        ${icon("cloche")} Book With This Dish
      </button>
    `,
  });

  document.querySelector("#dish-details-modal #btn-dish-detail-book-now")?.addEventListener("click", () => {
    closeModal("dish-details-modal");
    openTermsModal();
  });
}

// ── Quick Option: Add-ons & Signature Dishes Modal (Alias) ───────────
async function openQuickAddonsModal() {
  return openQuickMenuModal({ initialCategory: "Add-ons" });
}

// ── Quick Option: About Us Modal ─────────────────────────────────────
function openQuickAboutUsModal() {
  openModal({
    id: "quick-about-modal",
    title: `${icon("info")} About Jayraldine's Catering`,
    large: false,
    bodyHtml: `
      <div style="padding:8px 6px;">
        <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px; padding-bottom:16px; border-bottom:1.5px solid var(--border);">
          <img src="icons/logo.png" alt="logo" style="width:68px; height:68px; border-radius:50%; box-shadow:var(--shadow-sm); border:2px solid var(--accent);">
          <div>
            <h3 style="font-size:19px; font-weight:800; color:var(--text); margin:0 0 4px;">Jayraldine's Catering</h3>
            <p style="font-size:13px; color:var(--text-muted); margin:0;">Delicious Moments, Perfectly Catered</p>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:14px; font-size:13.5px; line-height:1.5; color:var(--text-muted);">
          <p style="margin:0;">
            <b>Jayraldine's Catering</b> is a premier full-service catering company dedicated to creating memorable culinary experiences for weddings, birthdays, corporate gatherings, and festive celebrations.
          </p>
          <p style="margin:0;">
            Every dish is cooked fresh with authentic recipes, quality cuts of meat, vibrant vegetables, and warm Filipino hospitality.
          </p>

          <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-md); padding:14px; display:flex; flex-direction:column; gap:8px;">
            <div style="font-weight:700; color:var(--text); font-size:13px; margin-bottom:2px;">Contact &amp; Location:</div>
            <div style="display:flex; align-items:center; gap:8px;">${icon("mapPin")} <b>Location:</b> Cebu City, Philippines</div>
            <div style="display:flex; align-items:center; gap:8px;">${icon("phone")} <b>Phone:</b> (+63) 912 345 6789 / (032) 412-8899</div>
            <div style="display:flex; align-items:center; gap:8px;">${icon("mail")} <b>Email:</b> jayraldinescatering@gmail.com</div>
            <div style="display:flex; align-items:center; gap:8px;">${icon("clock")} <b>Kiosk System:</b> 100% Offline Standalone PWA</div>
          </div>
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn btn-primary" id="btn-start-order-about">${icon("check")} Book Catering</button>
    `,
  });

  document.querySelector("#quick-about-modal #btn-start-order-about")?.addEventListener("click", () => {
    closeModal("quick-about-modal");
    openTermsModal();
  });
}



// ── Data Sync modal ──────────────────────────────────────────────────

async function openDataSyncModal() {
  const sync = await api.syncStatus();
  openModal({
    id: "data-sync-modal",
    title: `${icon("database")} Data Sync &amp; Backups`,
    bodyHtml: `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:20px;">
        <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-sm); padding:14px;">
          <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Packages</div>
          <div style="font-size:22px; font-weight:800; color:var(--gold);">${sync.packages_count}</div>
        </div>
        <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-sm); padding:14px;">
          <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Menu Items</div>
          <div style="font-size:22px; font-weight:800; color:var(--accent);">${sync.menu_items_count}</div>
        </div>
      </div>

      <p style="font-size:13px; color:var(--text-muted); margin-bottom:18px;">
        <b>Last Master Import:</b> ${sync.last_sync ? escapeHtml(sync.last_sync.tms_imported_at) : "Using Default Seed Data"}
      </p>

      <div style="display:flex; flex-direction:column; gap:12px;">
        <label class="btn btn-secondary btn-block" style="cursor:pointer;">
          ${icon("upload")} Import Master Data (.db / .xlsx)
          <input type="file" id="import-file" accept=".db,.xlsx,.xlsm" style="display:none;">
        </label>
        <button class="btn btn-secondary" id="download-template">
          ${icon("download")} Download Excel Menu Template
        </button>
        <button class="btn btn-secondary" id="export-orders">
          ${icon("download")} Export Orders (.xlsx)
        </button>
        <button class="btn btn-secondary" id="export-db">
          ${icon("database")} Export Local Database (.db)
        </button>
        <button class="btn btn-danger" id="archive-clear" style="margin-top:8px;">
          ${icon("trash")} Archive &amp; Clear Local Orders
        </button>
      </div>
    `,
  });

  const modal = document.getElementById("data-sync-modal");
  modal.querySelector("#import-file").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const stats = await api.importMasterData(file);
      toast(`Imported ${stats.packages} packages, ${stats.menu_items} menu items!`, "success");
      closeModal("data-sync-modal");
      openDataSyncModal();
    } catch (err) {
      toast("Import failed: " + err.message, "error");
    }
  });
  modal.querySelector("#download-template").addEventListener("click", () => api.downloadTemplate());
  modal.querySelector("#export-orders").addEventListener("click", () => api.downloadOrdersExcel());
  modal.querySelector("#export-db").addEventListener("click", () => api.downloadDatabase());
  modal.querySelector("#archive-clear").addEventListener("click", async () => {
    if (!confirm("This will export all orders to an Excel backup, then clear them from this device. Continue?")) return;
    try {
      const result = await api.archiveAndClear();
      toast(`Archived ${result.archived_orders} orders successfully.`, "success");
      closeModal("data-sync-modal");
      renderHome();
    } catch (err) {
      toast("Archive & Clear failed: " + err.message, "error");
    }
  });
}

// Immediate auto-discovery and live sync on tablet startup
(async function initStartupSync() {
  try {
    const isLive = await api.ensureLiveConnection(true);
    if (isLive) {
      console.log("[LiveDB] Live PostgreSQL Central Database connected!");
      const landing = document.querySelector(".landing-shell");
      if (landing && !document.querySelector(".wizard-container")) {
        renderHome();
      }
    } else {
      console.warn("[LiveDB] Central Server offline. Local data blocked.");
      updateLiveDbBadge(false);
    }
  } catch (e) {
    console.warn("[LiveDB] Startup connection note:", e);
    updateLiveDbBadge(false);
  }
})();

// Listen for sync completion and live connection status events
if (typeof window !== "undefined") {
  window.addEventListener("jayraldines:live-status", (e) => {
    updateLiveDbBadge(!!e.detail?.connected, e.detail?.server || "");
  });

  window.addEventListener("jayraldines:sync-completed", (e) => {
    console.log("[LiveDB] Live data refreshed from PostgreSQL:", e.detail);
    const landing = document.querySelector(".landing-shell");
    if (landing && !document.querySelector(".wizard-container")) {
      renderHome();
    }
  });

  // Auto-sync whenever network re-connects or tab becomes active
  window.addEventListener("online", () => {
    console.log("[LiveDB] Network online - connecting to Live Central Database...");
    api.ensureLiveConnection(true).catch(() => {});
  });

  window.addEventListener("focus", () => {
    api.ensureLiveConnection().catch(() => {});
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      api.ensureLiveConnection().catch(() => {});
    }
  });
}

// Periodically check live connection every 15 seconds
setInterval(() => {
  api.ensureLiveConnection().catch(() => {});
}, 15000);

// Periodically pull fresh master data (menu items, packages, occasions,
// customers) from the central server every 60 seconds while connected, so
// changes made on the desktop app (or any other tablet/laptop) show up here
// without requiring a manual "Sync Now" or app restart. This is a DEDICATED
// timer, deliberately separate from the connection-heartbeat interval above
// - the two used to share the same 15000ms constant as ensureLiveConnection's
// own internal "already synced recently" cache guard, which made a real data
// pull happen only as an accidental, unreliable side effect of timing (real
// pulls landed roughly every OTHER 15s tick, or less often under network
// latency/backgrounded-tab timer throttling) rather than on any predictable
// schedule.
setInterval(() => {
  if (api.isLiveConnected()) {
    api.syncWithServer().catch(() => {});
  }
}, 60000);
