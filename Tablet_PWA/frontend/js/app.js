import { api } from "./api.js";
import { openModal, closeModal, toast, escapeHtml, statusPill } from "./views.js";
import { wizard, peso } from "./state.js";
import { mountWizard } from "./wizard.js";
import { openOwnerSettings } from "./settings.js";
import { icon } from "./icons.js";
import { mountLandingSlider } from "./slider.js";

const app = document.getElementById("app");

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}

// Theme management
export function getTheme() {
  return localStorage.getItem("jc_theme") || "dark";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("jc_theme", theme);
  document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
    const iconEl = btn.querySelector(".nav-action-icon");
    const labelEl = btn.querySelector(".nav-action-label");
    if (iconEl) {
      iconEl.innerHTML = theme === "light" ? icon("moon") : icon("sun");
    } else {
      btn.innerHTML = theme === "light" ? icon("moon") : icon("sun");
    }
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

export function showTransitionLoading(message = "Preparing kiosk for next guest…", duration = 900) {
  let splash = document.getElementById("transition-splash");
  if (!splash) {
    splash = document.createElement("div");
    splash.id = "transition-splash";
    splash.className = "app-splash";
    document.body.appendChild(splash);
  }
  splash.innerHTML = `
    <div class="splash-content">
      <div class="splash-logo-wrap">
        <div class="splash-glow-ring"></div>
        <img src="icons/logo.png" alt="Jayraldine's Catering" class="splash-logo">
      </div>
      <h2 class="splash-title" style="font-size:22px; margin-bottom:6px;">Jayraldine's Catering</h2>
      <p class="splash-subtitle" style="font-size:14px; opacity:0.9;">${escapeHtml(message)}</p>
      <div class="splash-loader-bar"><div class="splash-loader-progress"></div></div>
    </div>
  `;
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

function dismissSplash() {
  const splash = document.getElementById("app-splash");
  if (splash && !splash.classList.contains("hidden")) {
    setTimeout(() => {
      splash.classList.add("hidden");
      setTimeout(() => splash.remove(), 600);
    }, 400);
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
          <img src="icons/logo.png" alt="logo" class="brand-logo">
        </div>
        <div>
          <h1 class="brand-title">Jayraldine's Catering</h1>
          <p class="brand-subtitle">Delicious Moments, Perfectly Catered</p>
        </div>
      </div>
      <div class="header-nav-actions">
        <button class="nav-action-btn theme-toggle-btn" id="theme-btn" title="Toggle Theme">
          <div class="nav-action-icon">${currentTheme === "light" ? icon("moon") : icon("sun")}</div>
          <span class="nav-action-label">${currentTheme === "light" ? "Dark Mode" : "Light Mode"}</span>
        </button>
        <button class="nav-action-btn" id="fullscreen-btn" title="Toggle Fullscreen">
          <div class="nav-action-icon">${icon("fullscreen")}</div>
          <span class="nav-action-label">Fullscreen</span>
        </button>
        <button class="nav-action-btn" id="owner-settings-btn" title="Admin Settings">
          <div class="nav-action-icon">${icon("settings")}</div>
          <span class="nav-action-label">Settings</span>
        </button>
      </div>
    </header>

    <main class="main kiosk-landing-main" id="home-main">
      <div class="kiosk-landing-wrapper">
        
        <!-- Hero Split Section (Text & Action on Left, Slider on Right) -->
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
            </div>

            <!-- Elevated Action Pill Container with Glowing Start Cloche & Highlights -->
            <div class="kiosk-action-pill-card">
              
              <!-- Start Order Circle CTA (Landscape) / Full-width Button (Portrait) -->
              <div class="kiosk-cloche-cta-wrapper" id="start-order" role="button" tabindex="0" title="Touch to begin ordering">
                <div class="kiosk-cloche-glow-pulse"></div>
                <div class="kiosk-cloche-circle">
                  <div class="kiosk-cloche-icon">${icon("cloche")}</div>
                  <div class="kiosk-cloche-text-group">
                    <div class="kiosk-cloche-text-main">START ORDER</div>
                    <div class="kiosk-cloche-text-sub">Tap to begin booking</div>
                  </div>
                  <div class="kiosk-cloche-arrow">${icon("chevronRight")}</div>
                </div>
              </div>

              <!-- Service Highlights (3 in landscape, 2x2 grid in portrait) -->
              <div class="kiosk-pill-highlights">
                
                <div class="kiosk-pill-item">
                  <div class="kiosk-pill-icon-box">
                    ${icon("calendar")}
                  </div>
                  <div class="kiosk-pill-text">
                    <span class="kiosk-pill-title">Easy Booking</span>
                    <span class="kiosk-pill-desc">Simple steps to book your catering</span>
                  </div>
                </div>

                <div class="kiosk-pill-item-divider"></div>

                <div class="kiosk-pill-item">
                  <div class="kiosk-pill-icon-box">
                    ${icon("shieldCheck")}
                  </div>
                  <div class="kiosk-pill-text">
                    <span class="kiosk-pill-title">Fresh &amp; Quality</span>
                    <span class="kiosk-pill-desc">We serve only the best for you</span>
                  </div>
                </div>

                <div class="kiosk-pill-item-divider"></div>

                <div class="kiosk-pill-item">
                  <div class="kiosk-pill-icon-box">
                    ${icon("users")}
                  </div>
                  <div class="kiosk-pill-text">
                    <span class="kiosk-pill-title">Trusted Service</span>
                    <span class="kiosk-pill-desc">Many happy events and customers</span>
                  </div>
                </div>

                <div class="kiosk-pill-item-divider divider-4"></div>

                <div class="kiosk-pill-item pill-item-4">
                  <div class="kiosk-pill-icon-box">
                    ${icon("lock")}
                  </div>
                  <div class="kiosk-pill-text">
                    <span class="kiosk-pill-title">Secure &amp; Private</span>
                    <span class="kiosk-pill-desc">Your data is safe and protected</span>
                  </div>
                </div>

              </div>

            </div>
          </div>

          <!-- Hero Slider / Cinematic Blended Catering Showcase Right Column -->
          <div class="kiosk-hero-visual-col">
            <div id="landing-hero-slider-container" class="kiosk-slider-outer-frame"></div>
          </div>

        </section>

        <!-- Bottom Quick Options Section -->
        <section class="kiosk-quick-options-section">
          <h3 class="quick-options-heading">Quick Options</h3>
          
          <div class="quick-options-grid">
            
            <button class="quick-option-card" id="quick-packages-btn">
              <div class="quick-opt-icon-circle">${icon("package")}</div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">View Packages</span>
                <span class="quick-opt-desc">Browse all available packages</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

            <button class="quick-option-card" id="quick-events-btn">
              <div class="quick-opt-icon-circle">${icon("calendar")}</div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">Event Types</span>
                <span class="quick-opt-desc">Choose your event type</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

            <button class="quick-option-card" id="quick-addons-btn">
              <div class="quick-opt-icon-circle">${icon("utensils")}</div>
              <div class="quick-opt-info">
                <span class="quick-opt-title">Add-ons</span>
                <span class="quick-opt-desc">Customize your menu with extras</span>
              </div>
              <div class="quick-opt-arrow">${icon("chevronRight")}</div>
            </button>

            <button class="quick-option-card" id="quick-orders-btn">
              <div class="quick-opt-icon-circle">${icon("fileText")}</div>
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

  // Mount listeners
  document.getElementById("theme-btn").addEventListener("click", toggleTheme);
  document.getElementById("fullscreen-btn").addEventListener("click", toggleFullscreen);
  document.getElementById("owner-settings-btn").addEventListener("click", () => openOwnerSettings("bookings"));
  document.getElementById("start-order").addEventListener("click", openTermsModal);

  // Mount Quick Options
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
    const iconEl = btn.querySelector(".nav-action-icon");
    if (iconEl) {
      iconEl.innerHTML = isFullscreen ? icon("minimize") : icon("fullscreen");
    } else {
      btn.innerHTML = isFullscreen ? icon("minimize") : icon("fullscreen");
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

// ── Recent Orders modal ──────────────────────────────────────────────

async function openRecentOrdersModal() {
  const orders = await api.getOrders();
  openModal({
    id: "recent-orders-modal",
    title: `${icon("shoppingBag")} Recent Catering Orders (${orders.length})`,
    large: true,
    bodyHtml: `
      <div class="orders-card-grid">
        ${orders.map((o) => `
          <div class="order-kiosk-card">
            <div class="order-kiosk-header">
              <span class="order-ref-pill">${escapeHtml(o.booking_ref)}</span>
              ${statusPill(o.status)}
            </div>
            <div class="order-kiosk-customer">${escapeHtml(o.customer)}</div>
            <div class="order-kiosk-row">
              <span>${icon("calendar")} ${escapeHtml(o.event_date)}</span>
              <span style="font-weight:800; font-size:16px; color:var(--gold);">${peso(o.total)}</span>
            </div>
            <div style="margin-top:auto; border-top:1px solid var(--border); padding-top:10px;">
              <button class="btn btn-secondary btn-block" data-receipt="${o.booking_id}">
                ${icon("download")} PDF Receipt
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
