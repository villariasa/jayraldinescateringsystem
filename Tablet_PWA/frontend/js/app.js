import { api } from "./api.js";
import { openModal, closeModal, toast, escapeHtml, statusPill } from "./views.js";
import { wizard, peso } from "./state.js";
import { mountWizard } from "./wizard.js";
import { openOwnerSettings, openOrderDetailModal } from "./settings.js";
import { icon } from "./icons.js";
import { mountLandingSlider } from "./slider.js";
import { mountLottie, mountHoverLottie, playTapBurst } from "./lottie-helper.js";

const app = document.getElementById("app");

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
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

      <!-- Split Interactive Hero Stage -->
      <main class="landing-stage">
        <!-- Left: Marketing Showcase & Catering Pitch -->
        <section class="stage-left">
          <div class="hero-badge">
            ${icon("sparkles")} Premium Catering Experience
          </div>
          <h1 class="hero-headline">
            Delightful Bites,<br>
            <span class="text-gold">Unforgettable Memories.</span>
          </h1>
          <p class="hero-lead">
            Welcome to Cebu's premier catering service. Create your custom event package, choose your favorite dishes, and confirm your booking in minutes.
          </p>

          <div class="hero-cta-group">
            <button class="btn btn-cta btn-lg" id="btn-start-order">
              <div class="lottie-icon-container" id="lottie-cloche-idle"></div>
              <span>Start Event Booking</span>
              ${icon("arrowRight")}
            </button>
          </div>

          <div class="hero-perks">
            <div class="perk-pill">
              ${icon("checkCircle")} 100% Offline Standalone
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
  mountHoverLottie(document.getElementById("quick-packages"), document.getElementById("quick-lottie-package"), "box-open");
  mountHoverLottie(document.getElementById("quick-menu"), document.getElementById("quick-lottie-menu"), "utensils-cross");
  mountHoverLottie(document.getElementById("quick-terms"), document.getElementById("quick-lottie-terms"), "signature-draw");

  // Wire CTA buttons
  const startOrderBtn = document.getElementById("btn-start-order");
  startOrderBtn?.addEventListener("click", (e) => {
    playTapBurst(e.clientX, e.clientY);
    wizard.reset();
    showScreen("wizard");
  });

  document.getElementById("landing-theme-toggle")?.addEventListener("click", () => {
    toggleTheme();
  });

  document.getElementById("landing-open-orders")?.addEventListener("click", () => {
    openRecentOrdersModal();
  });

  document.getElementById("landing-open-admin")?.addEventListener("click", () => {
    openOwnerSettings("bookings");
  });

  document.getElementById("quick-packages")?.addEventListener("click", () => {
    openPackagesQuickModal();
  });

  document.getElementById("quick-menu")?.addEventListener("click", () => {
    openMenuQuickModal();
  });

  document.getElementById("quick-terms")?.addEventListener("click", () => {
    openTermsQuickModal();
  });
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
            <div class="pkg-badge">Per Guest</div>
            <h3 class="pkg-name">${escapeHtml(p.name)}</h3>
            <div class="pkg-rate">${peso(p.price_per_pax)}<span class="pkg-unit"> / pax</span></div>
            <p class="pkg-desc">${escapeHtml(p.description || "Complete buffet service with setup, tableware and crew.")}</p>
            <div class="pkg-meta">
              <span>${icon("user")} Minimum ${p.min_pax || 30} pax</span>
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

// React live when landing images change in settings
window.addEventListener("kiosk:landing-images-changed", () => {
  const sliderContainer = document.getElementById("landing-hero-slider-container");
  if (sliderContainer) {
    mountLandingSlider(sliderContainer);
  }
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
            <div class="lottie-icon-container" id="lottie-nav-theme">${icon("sun")}</div>
          </div>
          <span class="nav-action-label">${currentTheme === "light" ? "Dark Mode" : "Light Mode"}</span>
        </button>
        <button class="nav-action-btn" id="fullscreen-btn" title="Toggle Fullscreen">
          <div class="nav-action-icon" id="fullscreen-icon-wrap">
            <div class="lottie-icon-container" id="lottie-nav-fullscreen">${icon("fullscreen")}</div>
          </div>
          <span class="nav-action-label">Fullscreen</span>
        </button>
        <button class="nav-action-btn" id="owner-settings-btn" title="Admin Settings">
          <div class="nav-action-icon">
            <div class="lottie-icon-container" id="lottie-nav-settings">${icon("settings")}</div>
          </div>
          <span class="nav-action-label">Settings</span>
        </button>
      </div>
    </header>

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

            <button class="quick-option-card" id="quick-addons-btn">
              <div class="quick-opt-icon-circle">
                <div class="lottie-icon-container" id="lottie-quick-addons">${icon("utensils")}</div>
              </div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">Add-ons</span>
                <span class="quick-opt-desc">Customize your menu with extras</span>
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

      </div>
    </main>
  `;

  // Mount Cloche idle in START ORDER button icon only
  const clocheWrap = document.getElementById("cloche-lottie-wrap");
  if (clocheWrap) {
    mountLottie(clocheWrap, "cloche-idle", { loop: true });
  }

  // START ORDER tap with particle burst
  const startOrderBtn = document.getElementById("start-order");
  startOrderBtn?.addEventListener("click", () => {
    playTapBurst(document.getElementById("hero-cloche-icon-box") || startOrderBtn, "cloche-tap-burst");
    setTimeout(() => {
      openTermsModal();
    }, 180);
  });

  // Mount Benefit card icons (constrained icon box divs only)
  mountLottie(document.getElementById("lottie-benefit-booking"), "icon-calendar", { loop: true, speed: 0.75 });
  mountLottie(document.getElementById("lottie-benefit-quality"), "icon-shield-check", { loop: true, speed: 0.75 });
  mountLottie(document.getElementById("lottie-benefit-service"), "icon-users", { loop: true, speed: 0.75 });
  mountLottie(document.getElementById("lottie-benefit-secure"), "icon-lock", { loop: true, speed: 0.75 });

  // Mount Quick Options hover Lottie on each inner .lottie-icon-container
  // (mountHoverLottie clears the static fallback icon before inserting Lottie SVG)
  mountHoverLottie(document.getElementById("lottie-quick-packages"), "icon-package", { speed: 1.2 });
  mountHoverLottie(document.getElementById("lottie-quick-events"), "icon-calendar", { speed: 1.2 });
  mountHoverLottie(document.getElementById("lottie-quick-addons"), "icon-utensils", { speed: 1.2 });
  mountHoverLottie(document.getElementById("lottie-quick-orders"), "icon-filetext", { speed: 1.2 });
  // Mount Header Nav Lottie animated icons (Dark/Light mode, Fullscreen, Settings)
  const navThemeAnim = await mountLottie(document.getElementById("lottie-nav-theme"), "icon-theme-toggle", { loop: true, speed: 0.65 });
  const navFsAnim = await mountLottie(document.getElementById("lottie-nav-fullscreen"), "icon-fullscreen", { loop: true, speed: 0.65 });
  const navSettingsAnim = await mountLottie(document.getElementById("lottie-nav-settings"), "icon-settings-gear", { loop: true, speed: 0.65 });

  document.getElementById("theme-btn")?.addEventListener("mouseenter", () => navThemeAnim?.setSpeed(1.4));
  document.getElementById("theme-btn")?.addEventListener("mouseleave", () => navThemeAnim?.setSpeed(0.65));
  document.getElementById("fullscreen-btn")?.addEventListener("mouseenter", () => navFsAnim?.setSpeed(1.4));
  document.getElementById("fullscreen-btn")?.addEventListener("mouseleave", () => navFsAnim?.setSpeed(0.65));
  document.getElementById("owner-settings-btn")?.addEventListener("mouseenter", () => navSettingsAnim?.setSpeed(1.4));
  document.getElementById("owner-settings-btn")?.addEventListener("mouseleave", () => navSettingsAnim?.setSpeed(0.65));

  // Mount listeners
  document.getElementById("theme-btn").addEventListener("click", () => {
    navThemeAnim?.goToAndPlay?.(0, true);
    toggleTheme();
  });
  document.getElementById("fullscreen-btn").addEventListener("click", toggleFullscreen);
  document.getElementById("owner-settings-btn").addEventListener("click", () => {
    navSettingsAnim?.goToAndPlay?.(0, true);
    openOwnerSettings("bookings");
  });

  // Mount Quick Options clicks
  document.getElementById("quick-packages-btn")?.addEventListener("click", openQuickPackagesModal);
  document.getElementById("quick-events-btn")?.addEventListener("click", openQuickEventTypesModal);
  document.getElementById("quick-addons-btn")?.addEventListener("click", openQuickAddonsModal);
  document.getElementById("quick-orders-btn")?.addEventListener("click", () => openOwnerSettings("bookings"));

  // Mount the Hero Slider
  const sliderContainer = document.getElementById("landing-hero-slider-container");
  if (sliderContainer) {
    mountLandingSlider(sliderContainer);
  }

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
  const packages = await api.getPackages();
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
              <span class="pill pill-partial" style="position:absolute; top:10px; right:10px; font-size:11px; font-weight:700; box-shadow:var(--shadow-sm);">Min ${p.min_pax || 30} Pax</span>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
              <div>
                <h3 style="font-size:17.5px; font-weight:800; color:var(--text); margin:0 0 4px;">${escapeHtml(p.name)}</h3>
              </div>
              <div style="text-align:right;">
                <span style="font-size:20px; font-weight:800; color:var(--gold);">${peso(p.price_per_pax)}</span>
                <span style="font-size:11px; color:var(--text-muted); display:block;">/ guest</span>
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
function openQuickEventTypesModal() {
  const events = [
    { title: "Wedding Reception", icon: "sparkles", desc: "Celebrate eternal love with romantic table setups, gourmet carving stations, and five-star banquet service." },
    { title: "Birthday Party & Milestone", icon: "heart", desc: "From joyful kiddie parties to grand 50th jubilees, delight all your guests with hearty savory feasts." },
    { title: "Debut (18th / 21st)", icon: "sparkles", desc: "Make her once-in-a-lifetime debut magical with stylish themed buffet staging and VIP service." },
    { title: "Corporate Event & Seminar", icon: "clipboardCheck", desc: "Punctual, professional catering for executive conferences, product launches, and annual banquets." },
    { title: "Anniversary Celebration", icon: "calendar", desc: "Honor cherished years together with custom menus tailored to family favorites and loved ones." },
    { title: "Family Reunion & Fiesta", icon: "utensils", desc: "Gather the whole clan for unforgettable Filipino feast spreads, crispy lechon, and refreshing beverages." },
  ];

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

// ── Quick Option: Add-ons & Signature Dishes Modal ───────────────────
async function openQuickAddonsModal() {
  const items = await api.getMenuItems();
  const categories = [...new Set(items.map(i => i.category || "Specialty"))];

  openModal({
    id: "quick-addons-modal",
    title: `${icon("utensils")} Catering Add-ons &amp; Signature Dishes`,
    large: true,
    bodyHtml: `
      <div style="margin-bottom:16px;">
        <p style="font-size:14px; color:var(--text-muted); margin:0;">
          Elevate your event with signature roasted meats, dessert bars, beverage stations, and extra equipment.
        </p>
      </div>
      <div style="max-height:56vh; overflow-y:auto; padding-right:6px;">
        ${categories.map(cat => {
          const catItems = items.filter(i => (i.category || "Specialty") === cat);
          return `
            <div style="margin-bottom:20px;">
              <h4 style="font-size:15px; font-weight:800; color:var(--accent); margin:0 0 10px; border-bottom:1px solid var(--border); padding-bottom:6px;">
                ${escapeHtml(cat)} (${catItems.length})
              </h4>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                ${catItems.map(item => `
                  <div class="card" style="padding:14px; border:1px solid var(--border); border-radius:var(--radius-md);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                      <span style="font-weight:700; font-size:14px; color:var(--text);">${escapeHtml(item.name)}</span>
                      <span style="font-weight:800; font-size:14px; color:var(--gold);">${peso(item.price)}</span>
                    </div>
                    <p style="font-size:12px; color:var(--text-muted); margin:0; line-height:1.4;">${escapeHtml(item.description || "Freshly prepared to order.")}</p>
                  </div>
                `).join("")}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn btn-primary" id="btn-order-with-addons">${icon("cloche")} Start Booking Now</button>
    `,
  });

  document.querySelector("#quick-addons-modal #btn-order-with-addons")?.addEventListener("click", () => {
    closeModal("quick-addons-modal");
    openTermsModal();
  });
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
            <div>📍 <b>Location:</b> Cebu City, Philippines</div>
            <div>📞 <b>Phone:</b> (+63) 912 345 6789 / (032) 412-8899</div>
            <div>✉️ <b>Email:</b> jayraldinescatering@gmail.com</div>
            <div>⏰ <b>Kiosk System:</b> 100% Offline Standalone PWA</div>
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
