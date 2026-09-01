import { api } from "./api.js";
import { openModal, closeModal, toast, escapeHtml, statusPill } from "./views.js";
import { peso } from "./state.js";
import { icon } from "./icons.js";
import { mountLottie } from "./lottie-helper.js";
import {
  getLandingImages,
  saveLandingImages,
  resetLandingImages,
  getSliderInterval,
  setSliderInterval,
  mountLandingSlider,
} from "./slider.js";

const MODAL_ID = "owner-settings-modal";
const AUTH_MODAL_ID = "admin-auth-modal";
const DEFAULT_ADMIN_PASS = "12345678";

export function getAdminPassword() {
  return localStorage.getItem("jc_admin_password") || DEFAULT_ADMIN_PASS;
}

export function setAdminPassword(newPass) {
  localStorage.setItem("jc_admin_password", String(newPass).trim());
}

function readAndCompressImage(file, maxWidth = 2560, maxHeight = 1920, quality = 0.98) {
  return new Promise((resolve, reject) => {
    if (!file) {
      return reject(new Error("Please select a valid image file."));
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;

        // Preserve pristine clarity and aspect ratio
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(img, 0, 0, width, height);

        // Export as crisp WebP or high-quality JPEG
        try {
          const dataUrl = canvas.toDataURL("image/webp", quality);
          if (dataUrl.startsWith("data:image/webp")) {
            return resolve(dataUrl);
          }
        } catch (_) {}
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.onerror = () => reject(new Error("Failed to load image."));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error("Failed to read file."));
    reader.readAsDataURL(file);
  });
}

/**
 * Entry point when user clicks "Admin Access" / "Settings".
 * Enforces security password check before granting access.
 */
export function openOwnerSettings(initialTab = "bookings") {
  promptAdminPassword(() => {
    showOwnerSettingsModal(initialTab);
  });
}

function promptAdminPassword(onSuccess) {
  openModal({
    id: AUTH_MODAL_ID,
    title: `${icon("lock")} Admin Security Verification`,
    bodyHtml: `
      <div class="auth-prompt-card" style="text-align:center; padding:12px 16px 20px; max-width:440px; margin:0 auto;">
        <div style="width:60px; height:60px; border-radius:50%; background:rgba(225, 29, 72, 0.12); color:var(--accent); display:inline-flex; align-items:center; justify-content:center; margin-bottom:14px; box-shadow:0 0 25px rgba(225, 29, 72, 0.2);">
          ${icon("lock")}
        </div>
        <h3 style="font-size:20px; font-weight:800; color:var(--text); margin:0 0 6px;">Admin Passcode Required</h3>
        <p style="font-size:13.5px; color:var(--text-muted); margin:0 0 20px; line-height:1.45;">
          Enter the management password to access owner settings, orders, menu controls, and visuals.
        </p>

        <form id="admin-auth-form" onsubmit="return false;" style="margin-bottom:14px;">
          <div style="position:relative; max-width:320px; margin:0 auto 10px;">
            <input 
              type="password" 
              id="admin-pass-input" 
              class="form-control" 
              placeholder="••••••••" 
              autocomplete="off"
              readonly
              inputmode="none"
              tabindex="-1"
              style="font-size:24px; text-align:center; letter-spacing:0.25em; padding-right:44px; height:52px; font-weight:700; border-radius:var(--radius-md); caret-color:transparent; cursor:default; user-select:none;"
            >
            <button 
              type="button" 
              id="toggle-auth-eye" 
              class="icon-btn" 
              style="position:absolute; right:8px; top:50%; transform:translateY(-50%); border:none; background:transparent; width:36px; height:36px; color:var(--text-muted);"
              title="Toggle Visibility"
            >
              ${icon("eye")}
            </button>
          </div>
          <div id="auth-error-msg" style="color:var(--danger); font-size:13px; font-weight:600; min-height:20px; margin-bottom:10px;"></div>

          <!-- Quick Numeric Pin Pad for easy tablet touch input -->
          <div class="pin-pad-grid" style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; max-width:280px; margin:0 auto 16px;">
            ${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => `
              <button type="button" class="btn btn-secondary pin-digit-btn" data-pin="${n}" style="font-size:18px; font-weight:700; height:46px; padding:0; border-radius:var(--radius-md);">${n}</button>
            `).join("")}
            <button type="button" class="btn btn-secondary pin-digit-btn" data-pin="clear" style="font-size:13px; font-weight:700; height:46px; padding:0; color:var(--text-muted); border-radius:var(--radius-md);">CLR</button>
            <button type="button" class="btn btn-secondary pin-digit-btn" data-pin="0" style="font-size:18px; font-weight:700; height:46px; padding:0; border-radius:var(--radius-md);">0</button>
            <button type="button" class="btn btn-secondary pin-digit-btn" data-pin="backspace" style="font-size:16px; font-weight:700; height:46px; padding:0; color:var(--danger); border-radius:var(--radius-md);">${icon("arrowLeft")}</button>
          </div>

          <div style="display:flex; gap:10px; justify-content:center;">
            <button type="button" class="btn btn-secondary" id="btn-cancel-auth" data-close style="min-width:110px;">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-auth" style="min-width:140px;">${icon("check")} Unlock Access</button>
          </div>
        </form>

        <p style="font-size:12px; color:var(--text-faint); margin:14px 0 0;">
          <span style="opacity:0.8;">Default owner password is</span> <b>12345678</b>
        </p>
      </div>
    `,
  });

  const modalEl = document.getElementById(AUTH_MODAL_ID);
  if (!modalEl) return;

  const passInput = modalEl.querySelector("#admin-pass-input");
  const eyeBtn = modalEl.querySelector("#toggle-auth-eye");
  const errorMsg = modalEl.querySelector("#auth-error-msg");
  const submitBtn = modalEl.querySelector("#btn-submit-auth");
  const cancelBtn = modalEl.querySelector("#btn-cancel-auth");
  const form = modalEl.querySelector("#admin-auth-form");

  let isVisible = false;
  eyeBtn?.addEventListener("click", () => {
    isVisible = !isVisible;
    passInput.type = isVisible ? "text" : "password";
    eyeBtn.innerHTML = isVisible ? icon("eyeOff") : icon("eye");
  });

  const cleanup = () => {
    window.removeEventListener("keydown", onKeyDown);
  };

  cancelBtn?.addEventListener("click", cleanup);

  const verify = () => {
    const inputVal = (passInput.value || "").trim();
    const currentPass = getAdminPassword();

    if (inputVal === currentPass) {
      cleanup();
      closeModal(AUTH_MODAL_ID);
      toast("Admin access unlocked", "success");
      onSuccess();
    } else {
      errorMsg.textContent = "Incorrect passcode. Please try again.";
      passInput.classList.add("input-error");
      passInput.style.borderColor = "var(--danger)";
      passInput.style.animation = "shake 0.35s ease";
      setTimeout(() => {
        passInput.style.animation = "";
      }, 400);
    }
  };

  // Process a PIN digit, clear, or backspace
  const handlePinInput = (pin) => {
    if (pin === "clear") {
      passInput.value = "";
      errorMsg.textContent = "";
      return;
    }
    if (pin === "backspace") {
      passInput.value = passInput.value.slice(0, -1);
      errorMsg.textContent = "";
      return;
    }

    // Append digit (up to 20 digits max)
    if (passInput.value.length < 20) {
      passInput.value += pin;
    }
    errorMsg.textContent = "";

    // Auto-proceed immediately once password matches!
    const inputVal = passInput.value.trim();
    const currentPass = getAdminPassword();
    if (inputVal === currentPass) {
      cleanup();
      closeModal(AUTH_MODAL_ID);
      toast("Admin access unlocked", "success");
      onSuccess();
      return;
    }

    // If entered characters equal or exceed current password length and did not match
    if (inputVal.length >= currentPass.length) {
      errorMsg.textContent = "Incorrect passcode. Please try again.";
      passInput.classList.add("input-error");
      passInput.style.borderColor = "var(--danger)";
      passInput.style.animation = "shake 0.35s ease";
      setTimeout(() => {
        passInput.style.animation = "";
      }, 400);
    }
  };

  // Numeric Pin Pad Button Clicks (Zero device keyboard pop up)
  modalEl.querySelectorAll(".pin-digit-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const pin = btn.dataset.pin;
      handlePinInput(pin);
    });
  });

  // Physical Keyboard listener (optional hardware keyboard support without software keyboard pop up)
  const onKeyDown = (e) => {
    if (!document.getElementById(AUTH_MODAL_ID)) {
      cleanup();
      return;
    }
    if (e.key >= "0" && e.key <= "9") {
      e.preventDefault();
      handlePinInput(e.key);
    } else if (e.key === "Backspace") {
      e.preventDefault();
      handlePinInput("backspace");
    } else if (e.key === "Escape") {
      cleanup();
      closeModal(AUTH_MODAL_ID);
    } else if (e.key === "Enter") {
      e.preventDefault();
      verify();
    }
  };
  window.addEventListener("keydown", onKeyDown);

  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    verify();
  });
  submitBtn?.addEventListener("click", verify);
}

function showOwnerSettingsModal(initialTab = "bookings") {
  openModal({
    id: MODAL_ID,
    title: `${icon("shield")} Admin &amp; Owner Management Access`,
    large: true,
    bodyHtml: (body) => renderTabs(body, initialTab),
  });
}

async function renderTabs(body, active) {
  let tabsBar = body.querySelector(".settings-tabs-sticky");
  let content = body.querySelector("#tab-content");

  // Create the persistent tabs header once if not already rendered
  if (!tabsBar || !content) {
    body.innerHTML = `
      <div class="settings-tabs-sticky">
        <button class="btn btn-secondary" data-tab="bookings">
          ${icon("shoppingBag")} Recent Bookings
        </button>
        <button class="btn btn-secondary" data-tab="packages">
          ${icon("package")} Buffet Packages
        </button>
        <button class="btn btn-secondary" data-tab="menu">
          ${icon("utensils")} Menu Dishes &amp; Add-ons
        </button>
        <button class="btn btn-secondary" data-tab="customers">
          ${icon("user")} Customer Directory
        </button>
        <button class="btn btn-secondary" data-tab="landing">
          ${icon("image")} Landing &amp; Slider
        </button>
        <button class="btn btn-secondary" data-tab="security">
          ${icon("key")} Passcode Security
        </button>
        <button class="btn btn-secondary" data-tab="database">
          ${icon("database")} Database &amp; Sync
        </button>
      </div>
      <div id="tab-content" style="margin-top:4px;"></div>
    `;

    tabsBar = body.querySelector(".settings-tabs-sticky");
    content = body.querySelector("#tab-content");

    tabsBar.querySelectorAll("[data-tab]").forEach((t) => {
      t.addEventListener("click", () => renderTabs(body, t.dataset.tab));
    });
  }

  // Update active button styling WITHOUT destroying the tab bar DOM or resetting scroll position
  tabsBar.querySelectorAll("[data-tab]").forEach((btn) => {
    if (btn.dataset.tab === active) {
      btn.className = "btn btn-primary";
    } else {
      btn.className = "btn btn-secondary";
    }
  });

  // Directly scroll the tabs container so the active tab is guaranteed to be visible and centered
  const activeBtn = tabsBar.querySelector(`[data-tab="${active}"]`);
  if (activeBtn) {
    requestAnimationFrame(() => {
      const containerWidth = tabsBar.clientWidth;
      const btnLeft = activeBtn.offsetLeft;
      const btnWidth = activeBtn.clientWidth;
      const targetScroll = btnLeft - (containerWidth / 2) + (btnWidth / 2);
      tabsBar.scrollTo({
        left: Math.max(0, targetScroll),
        behavior: "smooth"
      });
    });
  }

  if (active === "bookings") return renderBookingsTab(content);
  if (active === "packages") return renderPackagesTab(content);
  if (active === "menu") return renderMenuTab(content);
  if (active === "customers") return renderCustomersTab(content);
  if (active === "landing") return renderLandingTab(content);
  if (active === "security") return renderSecurityTab(content);
  return renderDatabaseTab(content);
}

// ── Bookings & Orders Tab ────────────────────────────────────────────

async function renderBookingsTab(content) {
  content.innerHTML = `<p style="color:var(--text-muted); padding:30px; text-align:center;">Loading recent bookings…</p>`;
  const orders = await api.getOrders();

  let filtered = [...orders];

  const renderList = () => {
    const totalRev = filtered.reduce((sum, o) => sum + (o.total || 0), 0);
    const totalDown = filtered.reduce((sum, o) => sum + (o.downpayment || 0), 0);
    const totalBal = filtered.reduce((sum, o) => sum + (o.balance || 0), 0);

    content.innerHTML = `
      <!-- Summary Metrics Row -->
      <div class="grid-3" style="margin-bottom:20px;">
        <div class="kpi-card" style="background:var(--card-elevated); border:1px solid var(--border); border-radius:var(--radius-md); padding:16px;">
          <div class="kpi-label" style="font-size:12px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Total Bookings Volume</div>
          <div class="kpi-value" style="font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; color:var(--text); margin-top:4px;">${peso(totalRev)}</div>
          <div class="kpi-sub" style="font-size:12px; color:var(--text-muted); margin-top:2px;">Across ${filtered.length} recorded events</div>
        </div>
        <div class="kpi-card" style="background:var(--card-elevated); border:1px solid var(--border); border-radius:var(--radius-md); padding:16px;">
          <div class="kpi-label" style="font-size:12px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Downpayments Collected</div>
          <div class="kpi-value" style="font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; color:var(--success); margin-top:4px;">${peso(totalDown)}</div>
          <div class="kpi-sub" style="font-size:12px; color:var(--text-muted); margin-top:2px;">Cash, GCash, Bank Deposits</div>
        </div>
        <div class="kpi-card" style="background:var(--card-elevated); border:1px solid var(--border); border-radius:var(--radius-md); padding:16px;">
          <div class="kpi-label" style="font-size:12px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Pending Balances Due</div>
          <div class="kpi-value" style="font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; color:var(--accent); margin-top:4px;">${peso(totalBal)}</div>
          <div class="kpi-sub" style="font-size:12px; color:var(--text-muted); margin-top:2px;">Collectible on event days</div>
        </div>
      </div>

      <!-- Action & Search Bar -->
      <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
        <div style="position:relative; flex:1; min-width:240px;">
          <input type="text" id="search-orders-input" class="form-control" placeholder="Search by customer name, ref code, or date…" style="padding-left:36px;">
          <div style="position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--text-muted); pointer-events:none;">
            ${icon("search")}
          </div>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-secondary" id="export-orders-btn">
            ${icon("download")} Export Excel (.xlsx)
          </button>
        </div>
      </div>

      <!-- Bookings Table -->
      <div class="table-wrap" style="background:var(--card-elevated); border:1px solid var(--border); border-radius:var(--radius-md); overflow-x:auto;">
        <table class="table" style="width:100%; border-collapse:collapse; text-align:left; font-size:13.5px;">
          <thead>
            <tr style="border-bottom:1.5px solid var(--border); background:rgba(0,0,0,0.03);">
              <th style="padding:12px 16px;">Ref #</th>
              <th style="padding:12px 16px;">Customer</th>
              <th style="padding:12px 16px;">Event Date</th>
              <th style="padding:12px 16px;">Total</th>
              <th style="padding:12px 16px;">Paid</th>
              <th style="padding:12px 16px;">Balance</th>
              <th style="padding:12px 16px;">Status</th>
              <th style="padding:12px 16px; text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filtered.length === 0 ? `
              <tr>
                <td colspan="8" style="text-align:center; padding:40px 20px; color:var(--text-muted);">
                  <div class="lottie-icon-container" id="lottie-empty-bookings" style="width:72px; height:72px; margin:0 auto 12px;"></div>
                  <div style="font-weight:700; font-size:15px; color:var(--text);">No bookings found</div>
                  <div style="font-size:13px; margin-top:4px;">No events match your current search or date filter.</div>
                </td>
              </tr>
            ` : filtered.map((o) => `
              <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:12px 16px; font-weight:700; font-family:monospace; color:var(--accent);">${escapeHtml(o.booking_ref || `JC-${o.booking_id}`)}</td>
                <td style="padding:12px 16px; font-weight:600;">${escapeHtml(o.customer || "Walk-in Guest")}</td>
                <td style="padding:12px 16px; color:var(--text-muted);">${escapeHtml(o.event_date || "—")}</td>
                <td style="padding:12px 16px; font-weight:700;">${peso(o.total)}</td>
                <td style="padding:12px 16px; color:var(--success); font-weight:600;">${peso(o.paid)}</td>
                <td style="padding:12px 16px; color:var(--accent); font-weight:600;">${peso(o.balance)}</td>
                <td style="padding:12px 16px;">${statusPill(o.status || "Confirmed")}</td>
                <td style="padding:12px 16px; text-align:right;">
                  <div style="display:inline-flex; gap:6px;">
                    <button class="btn btn-sm btn-secondary" data-detail="${o.booking_id}" title="View Details">
                      ${icon("eye")} Details
                    </button>
                    <button class="btn btn-sm btn-secondary" data-receipt="${o.booking_id}" title="Print Receipt">
                      ${icon("printer")}
                    </button>
                  </div>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

    // Mount empty plate animation if no bookings found
    if (filtered.length === 0) {
      const emptyEl = content.querySelector("#lottie-empty-bookings");
      if (emptyEl) mountLottie(emptyEl, "empty-plate", { loop: true, speed: 0.8 });
    }

    const searchInput = content.querySelector("#search-orders-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const q = e.target.value.toLowerCase().trim();
        filtered = orders.filter((o) =>
          (o.customer || "").toLowerCase().includes(q) ||
          (o.booking_ref || "").toLowerCase().includes(q) ||
          (o.event_date || "").toLowerCase().includes(q) ||
          (o.package_name || "").toLowerCase().includes(q)
        );
        renderList();
        const nextInput = content.querySelector("#search-orders-input");
        if (nextInput) {
          nextInput.value = q;
          nextInput.focus();
        }
      });
    }

    content.querySelector("#export-orders-btn")?.addEventListener("click", () => api.downloadOrdersExcel());

    content.querySelectorAll("[data-receipt]").forEach((btn) => {
      btn.addEventListener("click", () => api.downloadReceipt(Number(btn.dataset.receipt)));
    });

    content.querySelectorAll("[data-detail]").forEach((btn) => {
      btn.addEventListener("click", () => openOrderDetailModal(Number(btn.dataset.detail)));
    });
  };

  renderList();
}

function openOrderDetailModal(bookingId) {
  api.getOrder(bookingId).then((order) => {
    if (!order) {
      toast("Booking record details not found.", "error");
      return;
    }
    const modalId = "booking-detail-modal";
    const custName = order.customer || order.customer_name || "Guest";
    const custContact = order.contact || "No contact provided";
    const custEmail = order.email || "No email provided";
    const custAddress = order.customer_address || order.address || "No address on file";
    const eventOccasion = order.occasion || "Catering Event";
    const eventVenue = order.venue || "Location TBD";
    const hasAddons = Array.isArray(order.additional_charges) && order.additional_charges.length > 0;
    const hasMenu = Array.isArray(order.menu_selections) && order.menu_selections.length > 0;
    const hasNotes = Boolean(order.notes && order.notes.trim());

    openModal({
      id: modalId,
      title: `${icon("fileText")} Booking Reference: ${escapeHtml(order.booking_ref || `JC-${order.booking_id}`)}`,
      large: true,
      bodyHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <!-- Top Customer Profile Card -->
          <div style="display:flex; justify-content:space-between; align-items:flex-start; background:var(--card-elevated); padding:16px 20px; border-radius:var(--radius-md); border:1.5px solid var(--border); box-shadow:var(--shadow-sm); flex-wrap:wrap; gap:12px;">
            <div style="display:flex; gap:14px; align-items:center;">
              <div style="width:48px; height:48px; border-radius:50%; background:var(--accent-glow); color:var(--accent); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:20px; flex-shrink:0;">
                ${escapeHtml((custName[0] || "C").toUpperCase())}
              </div>
              <div>
                <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Customer Information</div>
                <div style="font-size:18px; font-weight:800; color:var(--text); margin-top:1px;">${escapeHtml(custName)}</div>
                <div style="font-size:13px; color:var(--text-muted); margin-top:3px; display:flex; gap:14px; flex-wrap:wrap;">
                  <span><b>Phone:</b> ${escapeHtml(custContact)}</span>
                  <span><b>Email:</b> ${escapeHtml(custEmail)}</span>
                </div>
                ${custAddress ? `<div style="font-size:12.5px; color:var(--text-muted); margin-top:3px;"><b>Address:</b> ${escapeHtml(custAddress)}</div>` : ""}
              </div>
            </div>
            <div style="text-align:right;">
              ${statusPill(order.status || "Confirmed")}
              <div style="font-size:11.5px; color:var(--text-muted); margin-top:6px;">Mode: <b>${escapeHtml(order.payment_method || "Cash")}</b></div>
            </div>
          </div>

          <!-- Event Schedule & Venue Grid -->
          <div class="grid-2" style="gap:12px;">
            <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:var(--radius-sm); padding:12px 16px;">
              <div style="font-size:11px; color:var(--text-muted); font-weight:700; text-transform:uppercase; display:flex; align-items:center; gap:6px;">
                ${icon("calendar")} Event Schedule &amp; Occasion
              </div>
              <div style="font-size:14.5px; font-weight:700; margin-top:4px; color:var(--text);">
                ${escapeHtml(eventOccasion)} &bull; ${order.pax} Guests
              </div>
              <div style="font-size:13px; color:var(--text-muted); margin-top:2px;">
                ${escapeHtml(order.event_date || "—")} at ${escapeHtml(order.event_time || "18:00")}
              </div>
            </div>

            <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:var(--radius-sm); padding:12px 16px;">
              <div style="font-size:11px; color:var(--text-muted); font-weight:700; text-transform:uppercase; display:flex; align-items:center; gap:6px;">
                ${icon("mapPin")} Event Venue &amp; Location
              </div>
              <div style="font-size:14.5px; font-weight:700; margin-top:4px; color:var(--text);">
                ${escapeHtml(eventVenue)}
              </div>
              <div style="font-size:13px; color:var(--text-muted); margin-top:2px;">
                Catering on-site buffet arrangement
              </div>
            </div>
          </div>

          <!-- Add-ons & Special Equipment Chosen (Itemized) -->
          ${hasAddons ? `
            <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:var(--radius-md); padding:14px 18px;">
              <div style="font-size:11px; color:var(--text-muted); font-weight:700; text-transform:uppercase; margin-bottom:10px; display:flex; align-items:center; gap:6px;">
                ${icon("package")} Selected Add-ons &amp; Custom Equipment (${order.additional_charges.length})
              </div>
              <div style="display:flex; flex-direction:column; gap:6px;">
                ${order.additional_charges.map((c) => `
                  <div style="display:flex; justify-content:space-between; align-items:center; font-size:13.5px; border-bottom:1px dashed var(--border); padding-bottom:6px;">
                    <span style="font-weight:600; color:var(--text);">&bull; ${escapeHtml(c.description)}</span>
                    <span style="font-weight:700; color:var(--gold);">${peso(c.amount)}</span>
                  </div>
                `).join("")}
              </div>
            </div>
          ` : ""}

          <!-- Special Event Notes / Customer Instructions -->
          ${hasNotes ? `
            <div style="background:rgba(245, 158, 11, 0.08); border:1.5px solid rgba(245, 158, 11, 0.35); border-radius:var(--radius-md); padding:14px 18px;">
              <div style="font-size:11.5px; color:var(--gold); font-weight:800; text-transform:uppercase; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                ${icon("info")} Special Instructions &amp; Setup Notes
              </div>
              <div style="font-size:13.5px; color:var(--text); line-height:1.5; white-space:pre-wrap; font-weight:500;">${escapeHtml(order.notes)}</div>
            </div>
          ` : ""}

          <!-- Selected Menu Buffet Items -->
          ${hasMenu ? `
            <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:var(--radius-md); padding:14px 18px;">
              <div style="font-size:11px; color:var(--text-muted); font-weight:700; text-transform:uppercase; margin-bottom:10px; display:flex; align-items:center; gap:6px;">
                ${icon("utensils")} Buffet Dishes Chosen (${order.menu_selections.length})
              </div>
              <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:8px;">
                ${order.menu_selections.map((m) => `
                  <div style="background:var(--card-elevated); padding:8px 12px; border-radius:var(--radius-sm); border:1px solid var(--border); font-size:12.5px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:600; color:var(--text);">${escapeHtml(m.item_name)}</span>
                    <span style="font-size:11px; color:var(--text-muted);">${escapeHtml(m.category || "")}</span>
                  </div>
                `).join("")}
              </div>
            </div>
          ` : ""}

          <!-- Financial Breakdown -->
          <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:var(--radius-md); padding:16px;">
            <div style="font-size:11px; color:var(--text-muted); font-weight:700; text-transform:uppercase; margin-bottom:10px;">Financial &amp; Billing Breakdown</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13.5px;">
              <span>Package (${escapeHtml(order.package_name || "Buffet")}) &times; ${order.pax} pax</span>
              <span style="font-weight:700;">${peso(order.package_subtotal || order.base_total || order.total)}</span>
            </div>
            ${(order.addons_subtotal || 0) > 0 ? `
              <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13.5px;">
                <span>Add-ons &amp; Custom Equipment Subtotal</span>
                <span style="font-weight:700; color:var(--gold);">+ ${peso(order.addons_subtotal)}</span>
              </div>
            ` : ""}
            <div style="display:flex; justify-content:space-between; margin-top:8px; padding-top:10px; border-top:1.5px solid var(--border); font-size:16px; font-weight:800;">
              <span>Grand Total</span>
              <span style="font-family:'Outfit',sans-serif; color:var(--gold); font-size:20px;">${peso(order.total)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:13px;">
              <span style="color:var(--success); font-weight:700;">Downpayment Paid (Deposit)</span>
              <span style="color:var(--success); font-weight:700;">${peso(order.downpayment || order.paid)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:3px; font-size:13px;">
              <span style="color:var(--accent); font-weight:700;">Balance Due on Event Day</span>
              <span style="color:var(--accent); font-weight:700;">${peso(order.balance)}</span>
            </div>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary" data-close>Close</button>
        <button class="btn btn-primary" id="modal-download-receipt-btn">${icon("printer")} Download Receipt PDF</button>
      `,
    });

    document.querySelector(`#${modalId} #modal-download-receipt-btn`)?.addEventListener("click", () => {
      api.downloadReceipt(Number(bookingId));
    });
  }).catch((err) => toast("Failed to load details: " + err.message, "error"));
}

// ── Packages tab ─────────────────────────────────────────────────────

async function renderPackagesTab(content) {
  content.innerHTML = `<p style="color:var(--text-muted); padding:20px; text-align:center;">Loading packages…</p>`;
  const packages = await api.getPackages();
  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <div style="font-size:14px; color:var(--text-muted); font-weight:600;">Configured Buffet Packages (${packages.length})</div>
      <button class="btn btn-primary" id="add-pkg">
        ${icon("plus")} Add New Package
      </button>
    </div>
    <div class="settings-card-grid">
      ${packages.map((p) => `
        <div class="management-card">
          <div class="management-card-top">
            ${p.image ? `<img src="${p.image}" alt="pkg" class="management-card-thumb">` : `<div class="management-card-thumb-placeholder">${icon("package")}</div>`}
            <div class="management-card-info">
              <h4 class="management-card-title">${escapeHtml(p.name)}</h4>
              <p class="management-card-desc">${escapeHtml(p.description || "Standard buffet catering setup.")}</p>
            </div>
          </div>
          <div class="management-card-meta">
            <span class="management-price-badge">${peso(p.price_per_pax)}<span style="font-size:12px; font-weight:600; color:var(--text-muted);"> / pax</span></span>
            <span class="pill pill-partial">Min ${p.min_pax} pax</span>
          </div>
          <div class="management-card-actions">
            <button class="btn btn-secondary" data-edit="${p.id}">
              ${icon("edit")} Edit
            </button>
            <button class="btn btn-danger" data-del="${p.id}">
              ${icon("trash")} Delete
            </button>
          </div>
        </div>
      `).join("") || `<div style="grid-column: 1 / -1; padding:32px; text-align:center; color:var(--text-muted);">No packages configured.</div>`}
    </div>
  `;
  content.querySelector("#add-pkg").addEventListener("click", () => openPackageForm(content, null));
  content.querySelectorAll("[data-edit]").forEach((el) => el.addEventListener("click", () => {
    openPackageForm(content, packages.find((p) => String(p.id) === el.dataset.edit));
  }));
  content.querySelectorAll("[data-del]").forEach((el) => el.addEventListener("click", async () => {
    if (!confirm("Delete this package?")) return;
    await api.deletePackage(el.dataset.del);
    toast("Package deleted.", "success");
    renderPackagesTab(content);
  }));
}

function openPackageForm(content, pkg) {
  const formId = "pkg-form-modal";
  let currentImage = pkg?.image || null;

  openModal({
    id: formId,
    title: pkg ? `${icon("edit")} Edit Package` : `${icon("plus")} Add New Package`,
    bodyHtml: `
      <div class="form-group">
        <label>Package Name *</label>
        <input type="text" class="form-control" id="f-name" value="${escapeHtml(pkg?.name || "")}">
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea class="form-control" id="f-desc" rows="2">${escapeHtml(pkg?.description || "")}</textarea>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Price Per Pax (₱)</label>
          <input type="number" class="form-control" id="f-price" step="0.01" value="${pkg?.price_per_pax ?? 350}">
        </div>
        <div class="form-group">
          <label>Minimum Pax</label>
          <input type="number" class="form-control" id="f-min" value="${pkg?.min_pax ?? 30}">
        </div>
      </div>
      <div class="form-group">
        <label>Package Photo (Device Camera or Gallery)</label>
        <div class="image-uploader-box">
          <div class="image-preview-wrap" id="pkg-img-preview-wrap">
            ${currentImage ? `<img src="${currentImage}" alt="preview" class="image-preview">` : `<div class="image-placeholder-icon">${icon("package")}<span>No photo chosen</span></div>`}
          </div>
          <div class="image-upload-actions">
            <input type="file" id="f-pkg-image-file" accept="image/*" style="display:none;">
            <button type="button" class="btn btn-secondary" id="choose-pkg-img-btn">${icon("upload")} Take / Choose Photo</button>
            <button type="button" class="btn btn-ghost" id="remove-pkg-img-btn" style="${currentImage ? "" : "display:none;"}">${icon("trash")} Remove</button>
          </div>
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Cancel</button>
      <button class="btn btn-primary" id="save-pkg">${icon("check")} Save Package</button>
    `,
  });

  const modal = document.getElementById(formId);
  const fileInput = modal.querySelector("#f-pkg-image-file");
  const chooseBtn = modal.querySelector("#choose-pkg-img-btn");
  const removeBtn = modal.querySelector("#remove-pkg-img-btn");
  const previewWrap = modal.querySelector("#pkg-img-preview-wrap");

  chooseBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      toast("Processing photo…", "info");
      currentImage = await readAndCompressImage(file, 1920, 1440, 0.95);
      previewWrap.innerHTML = `<img src="${currentImage}" alt="preview" class="image-preview">`;
      removeBtn.style.display = "inline-flex";
      toast("Photo loaded successfully!", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  removeBtn.addEventListener("click", () => {
    currentImage = null;
    fileInput.value = "";
    previewWrap.innerHTML = `<div class="image-placeholder-icon">${icon("package")}<span>No photo chosen</span></div>`;
    removeBtn.style.display = "none";
  });

  modal.querySelector("#save-pkg").addEventListener("click", async () => {
    const payload = {
      name: modal.querySelector("#f-name").value.trim(),
      description: modal.querySelector("#f-desc").value,
      price_per_pax: Number(modal.querySelector("#f-price").value || 0),
      min_pax: Number(modal.querySelector("#f-min").value || 30),
      image: currentImage,
    };
    if (!payload.name) { toast("Package Name is required.", "error"); return; }
    try {
      if (pkg) await api.updatePackage(pkg.id, payload);
      else await api.createPackage(payload);
      toast("Package saved successfully!", "success");
      closeModal(formId);
      renderPackagesTab(content);
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

// ── Menu tab ─────────────────────────────────────────────────────────

async function renderMenuTab(content) {
  content.innerHTML = `<p style="color:var(--text-muted); padding:20px; text-align:center;">Loading menu…</p>`;
  const [items, categories] = await Promise.all([api.getMenuItems(), api.getMenuCategories()]);
  content.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; gap:12px;">
      <select id="cat-filter" class="form-control" style="max-width:220px;">
        <option value="">All Categories (${items.length})</option>
        ${categories.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("")}
      </select>
      <button class="btn btn-primary" id="add-item">
        ${icon("plus")} Add Menu Item
      </button>
    </div>
    <div class="settings-card-grid" id="menu-rows"></div>
  `;

  function renderRows() {
    const filter = content.querySelector("#cat-filter").value;
    const rows = items.filter((it) => !filter || it.category === filter);
    content.querySelector("#menu-rows").innerHTML = rows.map((it) => `
      <div class="management-card">
        <div class="management-card-top">
          ${it.image ? `<img src="${it.image}" alt="dish" class="management-card-thumb">` : `<div class="management-card-thumb-placeholder">${icon("utensils")}</div>`}
          <div class="management-card-info">
            <h4 class="management-card-title">${escapeHtml(it.name)}</h4>
            <p class="management-card-desc">${escapeHtml(it.description || "Fresh specialty.")}</p>
          </div>
        </div>
        <div class="management-card-meta">
          <span class="pill pill-partial">${escapeHtml(it.category)}</span>
          <span class="management-price-badge">${it.price ? `+ ${peso(it.price)}` : `<span style="font-size:13px; color:var(--success); font-weight:700;">Included</span>`}</span>
          <span class="pill ${it.status === "Available" ? "pill-paid" : "pill-unpaid"}">${escapeHtml(it.status)}</span>
        </div>
        <div class="management-card-actions">
          <button class="btn btn-secondary" data-edit="${it.id}">
            ${icon("edit")} Edit
          </button>
          <button class="btn btn-danger" data-del="${it.id}">
            ${icon("trash")} Delete
          </button>
        </div>
      </div>
    `).join("") || `<div style="grid-column: 1 / -1; padding:32px; text-align:center; color:var(--text-muted);">No items in this category.</div>`;

    content.querySelectorAll("[data-edit]").forEach((el) => el.addEventListener("click", () => {
      openMenuItemForm(content, items.find((it) => String(it.id) === el.dataset.edit), categories);
    }));
    content.querySelectorAll("[data-del]").forEach((el) => el.addEventListener("click", async () => {
      if (!confirm("Delete this menu item?")) return;
      await api.deleteMenuItem(el.dataset.del);
      toast("Menu item deleted.", "success");
      renderMenuTab(content);
    }));
  }
  content.querySelector("#cat-filter").addEventListener("change", renderRows);
  content.querySelector("#add-item").addEventListener("click", () => openMenuItemForm(content, null, categories));
  renderRows();
}

function openMenuItemForm(content, item, categories) {
  const formId = "menu-form-modal";
  let currentImage = item?.image || null;

  openModal({
    id: formId,
    title: item ? `${icon("edit")} Edit Menu Item` : `${icon("plus")} Add Menu Item`,
    bodyHtml: `
      <div class="form-group">
        <label>Item Name *</label>
        <input type="text" class="form-control" id="f-name" value="${escapeHtml(item?.name || "")}">
      </div>
      <div class="form-group">
        <label>Category</label>
        <input type="text" class="form-control" id="f-category" list="cat-datalist" value="${escapeHtml(item?.category || "")}">
        <datalist id="cat-datalist">${categories.map((c) => `<option value="${escapeHtml(c)}">`).join("")}</datalist>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Add-on / Extra Price (₱)</label>
          <input type="number" class="form-control" id="f-price" step="0.01" value="${item?.price ?? 0}">
        </div>
        <div class="form-group">
          <label>Availability Status</label>
          <select id="f-status" class="form-control">
            <option value="Available" ${item?.status === "Available" ? "selected" : ""}>Available</option>
            <option value="Unavailable" ${item?.status === "Unavailable" ? "selected" : ""}>Unavailable</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Dish Photo (Device Camera or Gallery)</label>
        <div class="image-uploader-box">
          <div class="image-preview-wrap" id="dish-img-preview-wrap">
            ${currentImage ? `<img src="${currentImage}" alt="preview" class="image-preview">` : `<div class="image-placeholder-icon">${icon("utensils")}<span>No photo chosen</span></div>`}
          </div>
          <div class="image-upload-actions">
            <input type="file" id="f-dish-image-file" accept="image/*" style="display:none;">
            <button type="button" class="btn btn-secondary" id="choose-dish-img-btn">${icon("upload")} Take / Choose Photo</button>
            <button type="button" class="btn btn-ghost" id="remove-dish-img-btn" style="${currentImage ? "" : "display:none;"}">${icon("trash")} Remove</button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea class="form-control" id="f-desc" rows="2">${escapeHtml(item?.description || "")}</textarea>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Cancel</button>
      <button class="btn btn-primary" id="save-item">${icon("check")} Save Item</button>
    `,
  });

  const modal = document.getElementById(formId);
  const fileInput = modal.querySelector("#f-dish-image-file");
  const chooseBtn = modal.querySelector("#choose-dish-img-btn");
  const removeBtn = modal.querySelector("#remove-dish-img-btn");
  const previewWrap = modal.querySelector("#dish-img-preview-wrap");

  chooseBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      toast("Processing photo…", "info");
      currentImage = await readAndCompressImage(file, 1920, 1440, 0.95);
      previewWrap.innerHTML = `<img src="${currentImage}" alt="preview" class="image-preview">`;
      removeBtn.style.display = "inline-flex";
      toast("Photo loaded successfully!", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  removeBtn.addEventListener("click", () => {
    currentImage = null;
    fileInput.value = "";
    previewWrap.innerHTML = `<div class="image-placeholder-icon">${icon("utensils")}<span>No photo chosen</span></div>`;
    removeBtn.style.display = "none";
  });

  modal.querySelector("#save-item").addEventListener("click", async () => {
    const payload = {
      name: modal.querySelector("#f-name").value.trim(),
      category: modal.querySelector("#f-category").value.trim() || "Other",
      price: Number(modal.querySelector("#f-price").value || 0),
      status: modal.querySelector("#f-status").value,
      description: modal.querySelector("#f-desc").value,
      image: currentImage,
    };
    if (!payload.name) { toast("Item Name is required.", "error"); return; }
    try {
      if (item) await api.updateMenuItem(item.id, payload);
      else await api.createMenuItem(payload);
      toast("Menu item saved!", "success");
      closeModal(formId);
      renderMenuTab(content);
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

// ── Customers tab ────────────────────────────────────────────────────

async function renderCustomersTab(content) {
  content.innerHTML = `
    <div class="form-group">
      <div style="position:relative;">
        <input type="text" class="form-control" id="cust-search" placeholder="Search customers by name, phone or address…">
      </div>
    </div>
    <div class="settings-card-grid" id="cust-rows"></div>
  `;
  let customers = [];
  async function load(q = "") {
    customers = await api.searchCustomers(q);
    content.querySelector("#cust-rows").innerHTML = customers.map((c) => `
      <div class="management-card">
        <div class="customer-card-header">
          <div class="customer-avatar">${escapeHtml((c.name || "U")[0].toUpperCase())}</div>
          <div class="management-card-info">
            <h4 class="management-card-title">${escapeHtml(c.name)}</h4>
            <span style="font-size:12px; color:var(--text-muted);">ID #${c.id}</span>
          </div>
        </div>
        <div class="customer-detail-list">
          <div class="customer-detail-item">
            ${icon("phone")}
            <span>${escapeHtml(c.contact || "—")}</span>
          </div>
          <div class="customer-detail-item">
            ${icon("mapPin")}
            <span>${escapeHtml(c.address || "—")}</span>
          </div>
          ${c.email ? `
            <div class="customer-detail-item">
              ${icon("mail")}
              <span>${escapeHtml(c.email)}</span>
            </div>
          ` : ""}
        </div>
        <div class="management-card-actions">
          <button class="btn btn-secondary" data-edit="${c.id}">
            ${icon("edit")} Edit
          </button>
          <button class="btn btn-danger" data-del="${c.id}">
            ${icon("trash")} Delete
          </button>
        </div>
      </div>
    `).join("") || `<div style="grid-column: 1 / -1; padding:32px; text-align:center; color:var(--text-muted);">No matching customers found.</div>`;
    
    content.querySelectorAll("[data-edit]").forEach((el) => el.addEventListener("click", () => {
      openCustomerForm(content, customers.find((c) => String(c.id) === el.dataset.edit), () => load(content.querySelector("#cust-search").value));
    }));
    content.querySelectorAll("[data-del]").forEach((el) => el.addEventListener("click", async () => {
      if (!confirm("Delete this customer record?")) return;
      await api.deleteCustomer(el.dataset.del);
      toast("Customer deleted.", "success");
      load(content.querySelector("#cust-search").value);
    }));
  }
  let timer = null;
  content.querySelector("#cust-search").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => load(e.target.value), 250);
  });
  load();
}

function openCustomerForm(content, customer, onSaved) {
  const formId = "cust-form-modal";
  openModal({
    id: formId,
    title: `${icon("edit")} Edit Customer Record`,
    bodyHtml: `
      <div class="form-group">
        <label>Full Name *</label>
        <input type="text" class="form-control" id="f-name" value="${escapeHtml(customer?.name || "")}">
      </div>
      <div class="form-group">
        <label>Contact Number</label>
        <input type="text" class="form-control" id="f-contact" value="${escapeHtml(customer?.contact || "")}">
      </div>
      <div class="form-group">
        <label>Email Address</label>
        <input type="email" class="form-control" id="f-email" value="${escapeHtml(customer?.email || "")}">
      </div>
      <div class="form-group">
        <label>Delivery / Billing Address</label>
        <input type="text" class="form-control" id="f-address" value="${escapeHtml(customer?.address || "")}">
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Cancel</button>
      <button class="btn btn-primary" id="save-cust">${icon("check")} Save Customer</button>
    `,
  });
  document.querySelector(`#${formId} #save-cust`).addEventListener("click", async () => {
    const payload = {
      name: document.querySelector(`#${formId} #f-name`).value.trim(),
      contact: document.querySelector(`#${formId} #f-contact`).value,
      email: document.querySelector(`#${formId} #f-email`).value,
      address: document.querySelector(`#${formId} #f-address`).value,
    };
    if (!payload.name) { toast("Customer Name is required.", "error"); return; }
    try {
      await api.updateCustomer(customer.id, payload);
      toast("Customer updated!", "success");
      closeModal(formId);
      onSaved();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

// ── Database & Sync Tab ──────────────────────────────────────────────

async function renderDatabaseTab(content) {
  content.innerHTML = `<p style="color:var(--text-muted); padding:30px; text-align:center;">Checking database storage &amp; metrics…</p>`;
  const sync = await api.syncStatus();
  const orders = await api.getOrders();

  content.innerHTML = `
    <!-- Top Database Metrics Row -->
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; margin-bottom:24px;">
      <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-md); padding:16px;">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Local Bookings</div>
        <div style="font-size:24px; font-weight:800; color:var(--gold);">${orders.length}</div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">Stored in SQLite</div>
      </div>
      <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-md); padding:16px;">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Buffet Packages</div>
        <div style="font-size:24px; font-weight:800; color:var(--success);">${sync.packages_count}</div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">Active Catalog</div>
      </div>
      <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-md); padding:16px;">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Menu Dishes</div>
        <div style="font-size:24px; font-weight:800; color:var(--accent);">${sync.menu_items_count}</div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">Item Catalog</div>
      </div>
      <div style="background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-md); padding:16px;">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Sync Engine</div>
        <div style="font-size:18px; font-weight:800; color:var(--info);">${sync.last_sync ? "Custom Import" : "Standalone Seed"}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${sync.last_sync ? escapeHtml(sync.last_sync.tms_imported_at) : "100% Offline"}</div>
      </div>
    </div>

    <!-- Data Management Actions Section -->
    <div style="display:flex; flex-direction:column; gap:16px;">
      
      <!-- Backup & Export -->
      <div class="card" style="padding:20px;">
        <h4 style="margin:0 0 4px; font-size:16px; display:flex; align-items:center; gap:8px;">
          ${icon("database")} Database Backup &amp; Excel Exports
        </h4>
        <p style="font-size:13px; color:var(--text-muted); margin:0 0 16px;">
          Create offline backups and export spreadsheets for accounting, billing and kitchen reports.
        </p>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
          <button class="btn btn-secondary" id="btn-export-db">
            ${icon("database")} Backup SQLite Database (.db)
          </button>
          <button class="btn btn-secondary" id="btn-export-orders">
            ${icon("download")} Export Orders (.xlsx)
          </button>
          <button class="btn btn-secondary" id="btn-download-template">
            ${icon("fileText")} Download Excel Menu Template
          </button>
        </div>
      </div>

      <!-- Import Master Data -->
      <div class="card" style="padding:20px;">
        <h4 style="margin:0 0 4px; font-size:16px; display:flex; align-items:center; gap:8px;">
          ${icon("upload")} Import Master Data &amp; Menu Catalog
        </h4>
        <p style="font-size:13px; color:var(--text-muted); margin:0 0 16px;">
          Import dishes, packages, and prices from Excel (.xlsx) or restore from database backup (.db).
        </p>
        <div>
          <label class="btn btn-primary" style="cursor:pointer; display:inline-flex;">
            ${icon("upload")} Select Master File (.xlsx / .db)
            <input type="file" id="f-import-master" accept=".db,.xlsx,.xlsm" style="display:none;">
          </label>
        </div>
      </div>

      <!-- Maintenance & Clear DB -->
      <div class="card" style="padding:20px; border-color:rgba(239, 68, 68, 0.35);">
        <h4 style="margin:0 0 4px; font-size:16px; color:var(--danger); display:flex; align-items:center; gap:8px;">
          ${icon("alertTriangle")} Database Maintenance &amp; Clear
        </h4>
        <p style="font-size:13px; color:var(--text-muted); margin:0 0 16px;">
          Archive orders to Excel before clearing local transaction records.
        </p>
        <div style="display:flex; gap:12px; flex-wrap:wrap;">
          <button class="btn btn-danger" id="btn-archive-clear">
            ${icon("trash")} Archive &amp; Clear Local Orders
          </button>
        </div>
      </div>

    </div>
  `;

  content.querySelector("#btn-export-db")?.addEventListener("click", () => api.downloadDatabase());
  content.querySelector("#btn-export-orders")?.addEventListener("click", () => api.downloadOrdersExcel());
  content.querySelector("#btn-download-template")?.addEventListener("click", () => api.downloadTemplate());

  content.querySelector("#f-import-master")?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      toast("Importing master data…", "info");
      const stats = await api.importMasterData(file);
      toast(`Imported ${stats.packages} packages, ${stats.menu_items} menu items!`, "success");
      renderDatabaseTab(content);
    } catch (err) {
      toast("Import failed: " + err.message, "error");
    }
  });

  content.querySelector("#btn-archive-clear")?.addEventListener("click", async () => {
    if (!confirm("This will download an Excel archive of all orders and clear the local orders database. Continue?")) return;
    try {
      const res = await api.archiveAndClear();
      toast(`Archived ${res.archived_orders} orders and cleared local database.`, "success");
      renderDatabaseTab(content);
    } catch (err) {
      toast("Error: " + err.message, "error");
    }
  });
}

// ── Landing & Slider Management Tab ─────────────────────────────────

function renderLandingTab(content) {
  const images = getLandingImages();
  const interval = getSliderInterval();

  content.innerHTML = `
    <div style="display:flex; flex-direction:column; gap:20px;">
      
      <!-- Intro Card -->
      <div class="card" style="padding:22px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap;">
          <div>
            <h3 style="margin:0 0 6px; font-size:18px; font-weight:800; color:var(--text); display:flex; align-items:center; gap:8px;">
              ${icon("image")} Landing Hero Visuals &amp; Slider
            </h3>
            <p style="margin:0; font-size:13.5px; color:var(--text-muted); line-height:1.5;">
              Customize the images showcased on the tablet kiosk landing page. You can add up to <b>3 showcase images</b>.<br>
              When multiple images are added, the kiosk turns them into an automated smooth-swiping slider.
            </p>
          </div>
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <button class="btn btn-secondary" id="btn-reset-slider">
              ${icon("refresh")} Reset Default Photos
            </button>
            <label class="btn btn-primary ${images.length >= 3 ? "disabled" : ""}" style="cursor:${images.length >= 3 ? "not-allowed" : "pointer"}; display:inline-flex; align-items:center; gap:6px;">
              ${icon("plus")} Add Slide (${images.length}/3)
              <input type="file" id="input-add-slide" accept="image/*" style="display:none;" ${images.length >= 3 ? "disabled" : ""}>
            </label>
          </div>
        </div>
      </div>

      <!-- Slide Image Cards Grid -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px;">
        ${images.map((imgSrc, idx) => `
          <div class="card" style="padding:16px; display:flex; flex-direction:column; gap:12px; position:relative; overflow:hidden;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="pill pill-paid" style="font-weight:700; font-size:12px;">
                ${idx === 0 ? "★ Slide #1 (Main Hero)" : `Slide #${idx + 1}`}
              </span>
              <span style="font-size:12px; color:var(--text-muted);">Active Showcase</span>
            </div>

            <div style="width:100%; height:170px; border-radius:var(--radius-md); overflow:hidden; background:var(--input-bg); border:1.5px solid var(--border); position:relative;">
              <img src="${imgSrc}" alt="Slide ${idx + 1}" style="width:100%; height:100%; object-fit:cover; display:block;">
            </div>

            <div style="display:flex; gap:10px; margin-top:auto;">
              <label class="btn btn-secondary btn-block" style="cursor:pointer; font-size:12.5px; padding:8px 10px; display:inline-flex; align-items:center; justify-content:center; gap:6px;">
                ${icon("edit")} Replace
                <input type="file" class="input-replace-slide" data-index="${idx}" accept="image/*" style="display:none;">
              </label>
              <button 
                class="btn btn-danger btn-delete-slide" 
                data-index="${idx}" 
                style="padding:8px 12px; font-size:12.5px;" 
                title="Remove this image"
                ${images.length <= 1 ? "disabled" : ""}
              >
                ${icon("trash")}
              </button>
            </div>
          </div>
        `).join("")}
      </div>

      <!-- Auto-Swipe Settings & Info -->
      <div class="card" style="padding:20px;">
        <h4 style="margin:0 0 12px; font-size:15px; font-weight:700; color:var(--text); display:flex; align-items:center; gap:8px;">
          ${icon("clock")} Auto-Swipe Duration
        </h4>
        <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
          <p style="margin:0; font-size:13px; color:var(--text-muted); flex:1; min-width:240px;">
            Choose how long each food photo stays on screen before automatically transitioning to the next.
          </p>
          <div style="display:flex; gap:8px;">
            ${[3000, 5000, 7000, 10000].map(ms => `
              <button class="btn ${interval === ms ? "btn-primary" : "btn-secondary"} btn-interval" data-interval="${ms}" style="font-size:13px; padding:6px 14px;">
                ${ms / 1000}s
              </button>
            `).join("")}
          </div>
        </div>
      </div>

      <!-- Live Preview Container -->
      <div class="card" style="padding:20px;">
        <h4 style="margin:0 0 12px; font-size:15px; font-weight:700; color:var(--text); display:flex; align-items:center; gap:8px;">
          ${icon("sparkles")} Live Showcase Preview
        </h4>
        <div id="settings-slider-preview" style="max-width:680px; margin:0 auto; border-radius:var(--radius-xl); overflow:hidden; box-shadow:var(--shadow-md);"></div>
      </div>

    </div>
  `;

  // Mount Live Preview
  const previewBox = content.querySelector("#settings-slider-preview");
  if (previewBox) {
    mountLandingSlider(previewBox);
  }

  // Add Slide
  content.querySelector("#input-add-slide")?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      toast("Optimizing and uploading image…", "info");
      const compressed = await readAndCompressImage(file, 1920, 1280, 0.94);
      const current = getLandingImages();
      if (current.length < 3) {
        current.push(compressed);
        saveLandingImages(current);
        toast("New showcase image added!", "success");
        renderLandingTab(content);
      }
    } catch (err) {
      toast("Image error: " + err.message, "error");
    }
  });

  // Replace Slide
  content.querySelectorAll(".input-replace-slide").forEach((inp) => {
    inp.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      const idx = parseInt(inp.dataset.index, 10);
      if (!file || isNaN(idx)) return;
      try {
        toast("Replacing showcase image…", "info");
        const compressed = await readAndCompressImage(file, 1920, 1280, 0.94);
        const current = getLandingImages();
        current[idx] = compressed;
        saveLandingImages(current);
        toast(`Slide #${idx + 1} updated!`, "success");
        renderLandingTab(content);
      } catch (err) {
        toast("Image error: " + err.message, "error");
      }
    });
  });

  // Delete Slide
  content.querySelectorAll(".btn-delete-slide").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.dataset.index, 10);
      const current = getLandingImages();
      if (current.length <= 1) {
        toast("At least 1 showcase image is required.", "error");
        return;
      }
      current.splice(idx, 1);
      saveLandingImages(current);
      toast("Showcase image removed.", "success");
      renderLandingTab(content);
    });
  });

  // Reset Default Images
  content.querySelector("#btn-reset-slider")?.addEventListener("click", () => {
    if (!confirm("Reset the landing showcase photos to Jayraldine's default banquet images?")) return;
    resetLandingImages();
    toast("Restored default banquet photos!", "success");
    renderLandingTab(content);
  });

  // Interval Change
  content.querySelectorAll(".btn-interval").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ms = parseInt(btn.dataset.interval, 10);
      setSliderInterval(ms);
      toast(`Slide interval set to ${ms / 1000} seconds`, "success");
      renderLandingTab(content);
    });
  });
}

// ── Passcode Security Tab ───────────────────────────────────────────

function renderSecurityTab(content) {
  content.innerHTML = `
    <div style="max-width:540px; margin:10px auto;">
      <div class="card" style="padding:28px 24px;">
        <div style="text-align:center; margin-bottom:24px;">
          <div style="width:58px; height:58px; border-radius:50%; background:rgba(225, 29, 72, 0.12); color:var(--accent); display:inline-flex; align-items:center; justify-content:center; margin-bottom:12px;">
            ${icon("key")}
          </div>
          <h3 style="font-size:20px; font-weight:800; color:var(--text); margin:0 0 6px;">Manage Admin Passcode</h3>
          <p style="font-size:13.5px; color:var(--text-muted); margin:0; line-height:1.45;">
            Change the password used to lock Owner Settings, Booking Records, and visual configuration.
          </p>
        </div>

        <form id="change-pass-form" onsubmit="return false;" style="display:flex; flex-direction:column; gap:16px;">
          <div>
            <label style="display:block; font-size:13px; font-weight:700; color:var(--text); margin-bottom:6px;">Current Passcode</label>
            <div style="position:relative;">
              <input type="password" id="cur-pass" class="form-control" placeholder="Enter current passcode" required style="padding-right:42px;">
              <button type="button" class="icon-btn toggle-eye" data-target="cur-pass" style="position:absolute; right:8px; top:50%; transform:translateY(-50%); border:none; background:transparent; width:34px; height:34px; color:var(--text-muted);">
                ${icon("eye")}
              </button>
            </div>
          </div>

          <div>
            <label style="display:block; font-size:13px; font-weight:700; color:var(--text); margin-bottom:6px;">New Passcode</label>
            <div style="position:relative;">
              <input type="password" id="new-pass" class="form-control" placeholder="Enter new passcode (min 4 characters)" minlength="4" required style="padding-right:42px;">
              <button type="button" class="icon-btn toggle-eye" data-target="new-pass" style="position:absolute; right:8px; top:50%; transform:translateY(-50%); border:none; background:transparent; width:34px; height:34px; color:var(--text-muted);">
                ${icon("eye")}
              </button>
            </div>
          </div>

          <div>
            <label style="display:block; font-size:13px; font-weight:700; color:var(--text); margin-bottom:6px;">Confirm New Passcode</label>
            <div style="position:relative;">
              <input type="password" id="confirm-pass" class="form-control" placeholder="Re-enter new passcode" minlength="4" required style="padding-right:42px;">
              <button type="button" class="icon-btn toggle-eye" data-target="confirm-pass" style="position:absolute; right:8px; top:50%; transform:translateY(-50%); border:none; background:transparent; width:34px; height:34px; color:var(--text-muted);">
                ${icon("eye")}
              </button>
            </div>
          </div>

          <div id="pass-feedback" style="min-height:20px; font-size:13px; font-weight:600; text-align:center;"></div>

          <button type="submit" class="btn btn-primary btn-block" id="btn-save-pass" style="height:48px; font-size:15px; font-weight:700; margin-top:8px;">
            ${icon("check")} Update Admin Passcode
          </button>
        </form>

        <div style="margin-top:20px; padding:14px; background:var(--input-bg); border:1.5px solid var(--border); border-radius:var(--radius-md); font-size:12.5px; color:var(--text-faint); line-height:1.45;">
          ${icon("info")} <b>Tip:</b> Keep your passcode memorable. The default factory passcode is <code>12345678</code>.
        </div>
      </div>
    </div>
  `;

  const form = content.querySelector("#change-pass-form");
  const curPassInp = content.querySelector("#cur-pass");
  const newPassInp = content.querySelector("#new-pass");
  const confPassInp = content.querySelector("#confirm-pass");
  const feedback = content.querySelector("#pass-feedback");

  // Eye toggles
  content.querySelectorAll(".toggle-eye").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetInp = content.querySelector(`#${btn.dataset.target}`);
      if (!targetInp) return;
      const isPass = targetInp.type === "password";
      targetInp.type = isPass ? "text" : "password";
      btn.innerHTML = isPass ? icon("eyeOff") : icon("eye");
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    feedback.textContent = "";
    feedback.style.color = "var(--danger)";

    const cur = (curPassInp.value || "").trim();
    const next = (newPassInp.value || "").trim();
    const conf = (confPassInp.value || "").trim();

    const actualPass = getAdminPassword();
    if (cur !== actualPass) {
      feedback.textContent = "Current passcode does not match.";
      curPassInp.focus();
      return;
    }

    if (next.length < 4) {
      feedback.textContent = "New passcode must be at least 4 characters long.";
      newPassInp.focus();
      return;
    }

    if (next !== conf) {
      feedback.textContent = "New passcode and confirmation do not match.";
      confPassInp.focus();
      return;
    }

    setAdminPassword(next);
    feedback.style.color = "var(--success)";
    feedback.innerHTML = `${icon("checkCircle")} Passcode updated successfully!`;
    toast("Admin passcode updated successfully!", "success");

    curPassInp.value = "";
    newPassInp.value = "";
    confPassInp.value = "";
  });
}

