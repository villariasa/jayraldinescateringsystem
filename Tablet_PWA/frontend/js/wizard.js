import { api } from "./api.js";
import { wizard, chargesTotal, grandTotal, peso } from "./state.js";
import { toast, escapeHtml, statusPill, openModal, closeModal } from "./views.js";
import { icon } from "./icons.js";
import { getTheme, toggleTheme } from "./app.js";

const STEPS = [
  { step: 1, label: "Customer", title: "Customer Info", subtitle: "Enter client contact details" },
  { step: 2, label: "Event & Package", title: "Event & Package", subtitle: "Set event schedule, guest count & choose package" },
  { step: 3, label: "Menu", title: "Menu", subtitle: "Mix & match buffet menu items" },
  { step: 4, label: "Charges", title: "Add-ons & Charges", subtitle: "Select optional equipment & adjustments" },
  { step: 5, label: "Billing", title: "Billing & Payment", subtitle: "Set down payment & payment method" },
  { step: 6, label: "Preview", title: "Preview & Confirm", subtitle: "Review and place booking" },
];

const OCCASIONS = [
  "Birthday Party",
  "Wedding Reception",
  "Debut (18th / 21st)",
  "Anniversary Celebration",
  "Corporate Event / Seminar",
  "Christening / Baptism",
  "Graduation Party",
  "Thanksgiving Gathering",
  "Holiday / Christmas Party",
  "Family Reunion",
  "Funeral / Wake Service",
  "Other Special Event",
];

const UPSELLS = [
  { name: "Lechon Platter", price: 6500 },
  { name: "Dessert Bar", price: 3500 },
  { name: "Juice / Iced-tea Station", price: 2000 },
  { name: "Floral Backdrop", price: 4500 },
  { name: "Sound System", price: 3000 },
];

let root = null;
let packagesCache = [];
let menuGroupedCache = {};
let lastCreatedOrder = null;

function mergeAddress(currentInput, selectedSuggestion) {
  const input = (currentInput || "").trim();
  if (!input) return selectedSuggestion;

  if (input.toLowerCase().includes(selectedSuggestion.toLowerCase())) {
    return input;
  }

  const tokens = selectedSuggestion.split(",").map((t) => t.trim().toLowerCase());
  let streetPart = input;
  for (const token of tokens) {
    const idx = streetPart.toLowerCase().indexOf(token);
    if (idx !== -1) {
      streetPart = streetPart.substring(0, idx).trim();
      break;
    }
  }

  streetPart = streetPart.replace(/[,/\-]+$/, "").trim();

  if (streetPart && streetPart.length > 1) {
    return `${streetPart}, ${selectedSuggestion}`;
  }

  return selectedSuggestion;
}

export function mountWizard(container) {
  root = container;
  wizard.reset();
  render();
}

function confirmCancelOrder() {
  openModal({
    id: "cancel-order-modal",
    title: `${icon("alertTriangle")} Discard Draft Order?`,
    bodyHtml: `
      <div style="text-align:center; padding:16px 8px 10px;">
        <div style="width:58px; height:58px; border-radius:50%; background:rgba(239, 68, 68, 0.15); color:var(--danger); display:inline-flex; align-items:center; justify-content:center; margin-bottom:16px;">
          ${icon("trash")}
        </div>
        <p style="font-size:16px; font-weight:700; color:var(--text); margin:0 0 8px;">Are you sure you want to discard this order?</p>
        <p style="font-size:13.5px; color:var(--text-muted); line-height:1.5; margin:0;">
          All current customer information, package choices, and custom menu dishes will be reset.
        </p>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Keep Editing</button>
      <button class="btn btn-danger" id="modal-confirm-discard">${icon("trash")} Yes, Discard Order</button>
    `,
  });

  const modal = document.getElementById("cancel-order-modal");
  modal.querySelector("#modal-confirm-discard").addEventListener("click", () => {
    closeModal("cancel-order-modal");
    window.dispatchEvent(new CustomEvent("kiosk:home"));
  });
}

function render() {
  const currentStep = STEPS.find((s) => s.step === wizard.step) || STEPS[0];
  const currentTheme = getTheme();

  root.innerHTML = `
    <header class="wizard-sticky-header">
      <div class="wizard-top-nav">
        <div class="wizard-brand-wrap">
          <img src="icons/logo.png" alt="Jayraldine's Catering" class="wizard-brand-logo" style="width:48px; height:48px; min-width:48px; border-radius:10px; object-fit:cover; border:1.5px solid rgba(255,255,255,0.4); box-shadow:0 4px 12px rgba(0,0,0,0.25); display:block;" title="Jayraldine's Catering">
          <div class="wizard-step-info">
            <h2>Step ${wizard.step} — ${escapeHtml(currentStep.title)}</h2>
            <p>${escapeHtml(currentStep.subtitle)}</p>
          </div>
        </div>
        <div class="wizard-top-actions">
          <button class="icon-btn theme-toggle-btn" id="wiz-theme-btn" title="${currentTheme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}">
            ${currentTheme === "light" ? icon("moon") : icon("sun")}
          </button>
          <button class="icon-btn" id="wiz-fullscreen-btn" title="Toggle Fullscreen">${icon("fullscreen")}</button>
          <button class="btn btn-danger" id="wiz-cancel-btn">Cancel Order</button>
        </div>
      </div>
      <div class="timeline-stepper">
        ${STEPS.map((s, i) => {
          const isActive = s.step === wizard.step;
          const isDone = s.step < wizard.step;
          const cls = isActive ? "active" : isDone ? "done" : "";
          const circleContent = isDone ? icon("check") : s.step;
          return `
            <div class="timeline-step ${cls}" data-goto-step="${s.step}">
              <div class="timeline-node">
                <div class="timeline-circle">${circleContent}</div>
              </div>
              <div class="timeline-label">${escapeHtml(s.label)}</div>
            </div>
            ${i < STEPS.length - 1 ? `<div class="timeline-connector ${isDone ? "done" : ""}"></div>` : ""}
          `;
        }).join("")}
      </div>
    </header>

    <div class="wizard-content-wrap">
      <div class="wizard-grid-layout">
        <div class="card" id="wizard-step-card" style="animation: slideUpFade 0.3s cubic-bezier(0.16,1,0.3,1);"></div>
        <div class="card card-elevated" id="wizard-cart"></div>
      </div>
    </div>
  `;

  document.getElementById("wiz-theme-btn").addEventListener("click", () => {
    toggleTheme();
    const isLight = getTheme() === "light";
    document.getElementById("wiz-theme-btn").innerHTML = isLight ? icon("moon") : icon("sun");
  });

  document.getElementById("wiz-fullscreen-btn").addEventListener("click", () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  });

  document.getElementById("wiz-cancel-btn").addEventListener("click", confirmCancelOrder);

  root.querySelectorAll("[data-goto-step]").forEach((el) => {
    el.addEventListener("click", () => {
      const targetStep = Number(el.dataset.gotoStep);
      if (targetStep < wizard.step) {
        wizard.step = targetStep;
        render();
      }
    });
  });

  const headerEl = root.querySelector(".wizard-sticky-header");
  if (headerEl) {
    const updateHeaderH = () => {
      const h = headerEl.getBoundingClientRect().height || headerEl.offsetHeight || 132;
      document.documentElement.style.setProperty("--wiz-header-h", `${Math.round(h)}px`);
    };
    updateHeaderH();
    requestAnimationFrame(updateHeaderH);
    window.addEventListener("resize", updateHeaderH, { passive: true });
  }

  renderStep();
  renderCart();

  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

function renderCart() {
  const d = wizard.draft;
  const cart = document.getElementById("wizard-cart");
  if (!cart) return;

  const menuLines = d.menuSelections.map(
    (m) => `<div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px;"><span style="color:var(--text-muted);">${escapeHtml(m.item_name)}</span><span style="font-weight:600;">${m.price ? peso(m.price) : "Included"}</span></div>`
  ).join("");
  const chargeLines = d.additionalCharges.map(
    (c) => `<div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px;"><span style="color:var(--text-muted);">${escapeHtml(c.description)}</span><span style="font-weight:600; color:var(--gold);">${peso(c.amount)}</span></div>`
  ).join("");
  const total = grandTotal(d);
  const downPct = total > 0 ? Math.round(((d.downPayment || 0) / total) * 100) : 0;

  cart.innerHTML = `
    <h3 style="font-size:16px; margin:0 0 14px; display:flex; align-items:center; gap:8px;">
      ${icon("shoppingBag")} Live Event Summary
    </h3>
    <div style="border-bottom:1.5px solid var(--border); padding-bottom:10px; margin-bottom:10px;">
      <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:6px;">
        <span style="color:var(--text-muted);">Package</span>
        <span style="font-weight:700; color:var(--text);">${escapeHtml(d.package.name || "None")}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:14px;">
        <span style="color:var(--text-muted);">Guest Count</span>
        <span style="font-weight:700; color:var(--gold);">${d.event.pax || 0} pax</span>
      </div>
    </div>
    
    ${menuLines ? `<div style="border-bottom:1.5px solid var(--border); padding-bottom:10px; margin-bottom:10px;">${menuLines}</div>` : ""}
    ${chargeLines ? `<div style="border-bottom:1.5px solid var(--border); padding-bottom:10px; margin-bottom:10px;">${chargeLines}</div>` : ""}

    <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:12px;">
      <span style="font-size:15px; font-weight:700;">Grand Total</span>
      <span style="font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; color:var(--gold);">${peso(total)}</span>
    </div>
    <div style="color:var(--text-muted); font-size:12px; margin-top:4px;">
      Down payment: <b style="color:var(--text);">${peso(d.downPayment)}</b> (${downPct}%)
    </div>
    ${wizard.step < 6 ? `
      <button class="btn btn-primary btn-block" id="cart-quick-next" style="margin-top:14px; font-weight:800; padding:12px; font-size:14px; box-shadow:0 4px 14px var(--accent-glow);">
        Next Step ${icon("arrowRight")}
      </button>
    ` : ""}
    <button class="btn btn-ghost btn-block" id="cancel-order" style="margin-top:10px; font-size:12.5px;">
      ${icon("trash")} Discard Order
    </button>
  `;
  cart.querySelector("#cart-quick-next")?.addEventListener("click", () => {
    if (wizard.step < 6) { wizard.step++; render(); }
  });
  cart.querySelector("#cancel-order").addEventListener("click", confirmCancelOrder);
}

function stepCard() {
  return document.getElementById("wizard-step-card");
}

function footer(nextLabel, onNext, backEnabled = true) {
  const card = stepCard();
  const wrap = document.createElement("div");
  wrap.style.cssText = "display:flex; justify-content:space-between; align-items:center; margin-top:28px; border-top:1.5px solid var(--border); padding-top:20px;";
  wrap.innerHTML = `
    <button class="btn btn-secondary" id="wiz-back" ${backEnabled ? "" : "disabled"}>
      ${icon("arrowLeft")} Back
    </button>
    <button class="btn btn-primary" id="wiz-next">
      ${nextLabel} ${icon("arrowRight")}
    </button>
  `;
  card.appendChild(wrap);
  wrap.querySelector("#wiz-back").addEventListener("click", () => {
    if (wizard.step > 1) { wizard.step--; render(); }
  });
  wrap.querySelector("#wiz-next").addEventListener("click", onNext);
}

async function renderStep() {
  const card = stepCard();
  switch (wizard.step) {
    case 1: return renderStepCustomer(card);
    case 2: return renderStepPackage(card);
    case 3: return renderStepMenu(card);
    case 4: return renderStepAddons(card);
    case 5: return renderStepBilling(card);
    case 6: return renderStepPreview(card);
  }
}

// ── Step 1: Customer ─────────────────────────────────────────────────

function renderStepCustomer(card) {
  const d = wizard.draft;
  card.innerHTML = `
    <h2 style="margin:0 0 8px; display:flex; align-items:center; gap:10px;">
      ${icon("user")} Customer Information
    </h2>
    <p style="color:var(--text-muted); margin:0 0 20px; font-size:14px;">
      Enter the customer's contact details or look up an existing record.
    </p>

    <div style="display:flex; gap:10px; margin-bottom:20px;">
      <button class="btn btn-secondary" id="tab-new" style="flex:1;">
        ${icon("plus")} New Customer
      </button>
      <button class="btn btn-secondary" id="tab-search" style="flex:1;">
        ${icon("search")} Search Directory
      </button>
    </div>
    <div id="customer-panel"></div>
  `;
  const panel = card.querySelector("#customer-panel");

  function proceedToStep2() {
    if (!d.customer.id) {
      d.customer.name = (panel.querySelector("#c-name")?.value || "").trim();
      d.customer.contact = panel.querySelector("#c-contact")?.value || "";
      d.customer.email = panel.querySelector("#c-email")?.value || "";
      d.customer.street = (panel.querySelector("#c-street")?.value || "").trim();
      d.customer.cityBrgy = (panel.querySelector("#c-city-brgy")?.value || "").trim();
      d.customer.address = [d.customer.street, d.customer.cityBrgy].filter(Boolean).join(", ");
    }
    if (!d.customer.name) { toast("Customer name is required.", "error"); return; }
    wizard.step = 2;
    render();
  }

  function showNewForm() {
    card.querySelector("#tab-new").className = "btn btn-primary";
    card.querySelector("#tab-search").className = "btn btn-secondary";
    panel.innerHTML = `
      <div class="form-group">
        <label>Full Name *</label>
        <input type="text" class="form-control" id="c-name" placeholder="e.g. Maria Santos" value="${escapeHtml(d.customer.name)}" autofocus>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Contact Phone (11 digits)</label>
          <input type="tel" class="form-control" id="c-contact" placeholder="09xxxxxxxxx" maxlength="11" value="${escapeHtml(d.customer.contact)}">
        </div>
        <div class="form-group">
          <label>Email Address</label>
          <input type="email" class="form-control" id="c-email" placeholder="name@email.com" value="${escapeHtml(d.customer.email)}">
        </div>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Barangay / City (Search)</label>
          <input type="text" class="form-control" id="c-city-brgy" placeholder="Search barangay or city…" value="${escapeHtml(d.customer.cityBrgy || "")}" autocomplete="off">
          <div id="address-results" style="margin-top:8px;"></div>
        </div>
        <div class="form-group">
          <label>Street / House / Bldg / Unit No.</label>
          <input type="text" class="form-control" id="c-street" placeholder="e.g. 123 Katipunan St., Unit 4B" value="${escapeHtml(d.customer.street || "")}">
        </div>
      </div>
    `;

    const nameInput = panel.querySelector("#c-name");
    const contactInput = panel.querySelector("#c-contact");
    const emailInput = panel.querySelector("#c-email");
    const cityBrgyInput = panel.querySelector("#c-city-brgy");
    const streetInput = panel.querySelector("#c-street");
    const addrResults = panel.querySelector("#address-results");

    // Auto-focus first name immediately
    requestAnimationFrame(() => {
      nameInput?.focus();
    });

    // Enter on Name -> focus Contact
    nameInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        contactInput?.focus();
      }
    });

    // Contact 11-digit or Enter -> focus Email
    contactInput?.addEventListener("input", () => {
      let val = contactInput.value.replace(/\D/g, "");
      if (val.length > 11) val = val.slice(0, 11);
      contactInput.value = val;
      if (val.length === 11) {
        emailInput?.focus();
      }
    });
    contactInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        emailInput?.focus();
      }
    });

    // Enter on Email -> focus City/Brgy
    emailInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        cityBrgyInput?.focus();
      }
    });

    // City/Brgy search and selection -> focus Street
    let addrTimer = null;
    cityBrgyInput?.addEventListener("input", () => {
      clearTimeout(addrTimer);
      const q = cityBrgyInput.value;
      addrTimer = setTimeout(async () => {
        if (q.trim().length < 2) { addrResults.innerHTML = ""; return; }
        const results = await api.searchAddress(q);
        addrResults.innerHTML = results.map(
          (r) => `<div class="btn btn-secondary btn-block" style="margin-bottom:6px; text-align:left; justify-content:flex-start; font-size:13px;" data-addr="${escapeHtml(r.display_text)}">${icon("search")} ${escapeHtml(r.display_text)}</div>`
        ).join("");
        addrResults.querySelectorAll("[data-addr]").forEach((el) => {
          el.addEventListener("click", () => {
            cityBrgyInput.value = el.dataset.addr;
            addrResults.innerHTML = "";
            streetInput?.focus();
          });
        });
      }, 250);
    });
    cityBrgyInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        streetInput?.focus();
      }
    });

    // Enter on Street -> Auto-next to Step 2 (Event & Package)
    streetInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        proceedToStep2();
      }
    });
  }

  function showSearchForm() {
    card.querySelector("#tab-new").className = "btn btn-secondary";
    card.querySelector("#tab-search").className = "btn btn-primary";
    panel.innerHTML = `
      <div class="form-group">
        <label>Search Existing Records</label>
        <input type="text" class="form-control" id="c-search" placeholder="Type customer name or contact number…" autofocus>
      </div>
      <div id="search-results"></div>
      ${d.customer.id ? `
        <div class="card card-elevated" style="margin-top:14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:12px; color:var(--success); font-weight:700;">${icon("checkCircle")} SELECTED CUSTOMER</div>
            <div style="font-size:16px; font-weight:700;">${escapeHtml(d.customer.name)}</div>
            <div style="font-size:13px; color:var(--text-muted);">${escapeHtml(d.customer.contact)} · ${escapeHtml(d.customer.address)}</div>
          </div>
          <button class="btn btn-ghost" id="clear-selected">${icon("close")} Change</button>
        </div>
      ` : ""}
    `;

    const searchInput = panel.querySelector("#c-search");
    const resultsEl = panel.querySelector("#search-results");

    requestAnimationFrame(() => {
      searchInput?.focus();
    });

    if (d.customer.id) {
      panel.querySelector("#clear-selected").addEventListener("click", () => {
        d.customer = { id: null, name: "", contact: "", email: "", address: "" };
        showSearchForm();
      });
    }

    let timer = null;
    searchInput?.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const results = await api.searchCustomers(searchInput.value);
        resultsEl.innerHTML = results.map((r) => `
          <div class="card card-elevated customer-search-item" style="margin-bottom:8px; cursor:pointer; transition:transform 0.2s;" data-id="${r.id}">
            <b style="color:var(--text);">${escapeHtml(r.name)}</b><br>
            <span style="color:var(--text-muted); font-size:13px;">${escapeHtml(r.contact)} · ${escapeHtml(r.address)}</span>
          </div>
        `).join("") || `<p style="color:var(--text-muted); padding:10px;">No matches found.</p>`;
        
        // Auto-next to Event & Package upon selecting existing customer record
        resultsEl.querySelectorAll(".customer-search-item").forEach((el) => {
          el.addEventListener("click", () => {
            const found = results.find((r) => String(r.id) === el.dataset.id);
            if (found) {
              d.customer = { id: found.id, name: found.name, contact: found.contact, email: found.email, address: found.address };
              toast(`Selected customer: ${found.name}`, "success");
              wizard.step = 2;
              render();
            }
          });
        });
      }, 250);
    });
  }

  card.querySelector("#tab-new").addEventListener("click", showNewForm);
  card.querySelector("#tab-search").addEventListener("click", showSearchForm);
  showNewForm();

  footer("Next Step", proceedToStep2, false);
}

// ── Step 2: Package & Event ──────────────────────────────────────────

async function renderStepPackage(card) {
  const d = wizard.draft;
  card.innerHTML = `<h2 style="margin:0 0 10px;">${icon("package")} Event &amp; Package</h2><p style="color:var(--text-muted);">Loading packages…</p>`;
  if (!packagesCache.length) packagesCache = await api.getPackages();

  // If a package was pre-selected from Quick Options, ensure its full data is synced
  if (d.package.id && packagesCache.length) {
    const pre = packagesCache.find((p) => Number(p.id) === Number(d.package.id));
    if (pre) {
      d.package.name = pre.name;
      d.package.pricePerPax = d.package.pricePerPax || pre.price_per_pax;
      d.package.minPax = pre.min_pax;
      d.package.description = pre.description;
      d.package.image = pre.image;
      if (!d.package.baseTotal) {
        d.package.baseTotal = (d.package.pricePerPax || pre.price_per_pax) * (d.event.pax || 60);
      }
    }
  }

  card.innerHTML = `
    <h2 style="margin:0 0 8px; display:flex; align-items:center; gap:10px;">
      ${icon("package")} Event Schedule &amp; Package
    </h2>
    <p style="color:var(--text-muted); margin:0 0 20px; font-size:14px;">
      Select event date, expected guest count, venue, and choose or customize your package pricing.
    </p>

    <div class="grid-2">
      <div class="form-group">
        <label>Event Date *</label>
        <input type="date" class="form-control" id="e-date" value="${d.event.date}">
      </div>
      <div class="form-group">
        <label>Event Time</label>
        <input type="time" class="form-control" id="e-time" value="${d.event.time}">
      </div>
    </div>
    <div class="grid-2">
      <div class="form-group">
        <label>Guest Count (Pax) *</label>
        <input type="number" class="form-control" id="e-pax" min="10" max="2000" value="${d.event.pax}">
      </div>
      <div class="form-group">
        <label>Occasion / Event Type *</label>
        <select class="form-control" id="e-occasion">
          <option value="">Select Event Occasion…</option>
          ${OCCASIONS.map((occ) => `<option value="${escapeHtml(occ)}" ${d.event.occasion === occ ? "selected" : ""}>${escapeHtml(occ)}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="grid-2">
      <div class="form-group">
        <label>Venue Barangay / City (Search) *</label>
        <input type="text" class="form-control" id="e-venue-city" placeholder="Search barangay or city…" value="${escapeHtml(d.event.venueCity || "")}" autocomplete="off">
        <div id="venue-results" style="margin-top:8px;"></div>
      </div>
      <div class="form-group">
        <label>Venue Street / Landmark / Floor / Bldg</label>
        <input type="text" class="form-control" id="e-venue-street" placeholder="e.g. Grand Ballroom, 4th Floor, Skyline Hotel" value="${escapeHtml(d.event.venueStreet || "")}">
      </div>
    </div>

    <h3 style="margin:24px 0 12px; font-size:16px;">Select a Buffet Package</h3>
    <div class="kiosk-grid" id="pkg-grid">
      ${packagesCache.map((p) => {
        const isSelected = Number(d.package.id) === Number(p.id);
        return `
        <div class="kiosk-food-card select-card ${isSelected ? "selected" : ""}" data-id="${p.id}">
          <div class="kiosk-card-img-wrap">
            ${p.image ? `<img src="${p.image}" alt="${escapeHtml(p.name)}" class="kiosk-card-img">` : `
              <div class="kiosk-card-placeholder">
                ${icon("package")}
                <span style="font-size:12px; font-weight:700; opacity:0.85;">Buffet Tier</span>
              </div>
            `}
            <div class="kiosk-card-badge">
              ${isSelected ? icon("checkCircle") : icon("plus")}
            </div>
          </div>
          <div class="kiosk-card-body">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
              <h4 class="kiosk-card-title">${escapeHtml(p.name)}</h4>
              <button type="button" class="btn btn-ghost btn-view-pkg-details" data-pkg-details="${p.id}" style="padding:4px 8px; font-size:11px; height:24px; border-radius:12px; white-space:nowrap;" title="View Package Details & Inclusions">
                ${icon("info")} Details
              </button>
            </div>
            <p class="kiosk-card-desc">${escapeHtml(p.description || "Standard buffet catering setup.")}</p>
            <div class="kiosk-card-footer">
              <span class="kiosk-price-tag">${peso(p.price_per_pax)}<span style="font-size:12px; font-weight:600; color:var(--text-muted); font-family:inherit;"> / pax</span></span>
              <span class="kiosk-status-pill">Min ${p.min_pax} pax</span>
            </div>
          </div>
        </div>
      `;
      }).join("")}
    </div>

    <div class="grid-2" style="margin-top:20px;">
      <div class="form-group">
        <label>Price Per Pax (₱)</label>
        <input type="number" class="form-control" id="e-price-per-pax" step="0.01" value="${d.package.pricePerPax || 0}">
      </div>
      <div class="form-group">
        <label>Package Base Total (₱) — Directly Editable</label>
        <input type="number" class="form-control" id="e-base-total" step="0.01" value="${d.package.baseTotal || 0}">
      </div>
    </div>
  `;

  const dateInput = card.querySelector("#e-date");
  const timeInput = card.querySelector("#e-time");
  const paxInput = card.querySelector("#e-pax");
  const occasionSelect = card.querySelector("#e-occasion");
  const venueCityInput = card.querySelector("#e-venue-city");
  const venueStreetInput = card.querySelector("#e-venue-street");
  const venueResults = card.querySelector("#venue-results");

  // Auto-focus date immediately when entering Step 2
  requestAnimationFrame(() => {
    dateInput?.focus();
  });

  // Date -> Time
  dateInput?.addEventListener("change", () => {
    if (dateInput.value) timeInput?.focus();
  });
  dateInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      timeInput?.focus();
    }
  });

  // Time -> Guest Count
  timeInput?.addEventListener("change", () => {
    if (timeInput.value) paxInput?.focus();
  });
  timeInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      paxInput?.focus();
    }
  });

  // Guest Count -> Occasion
  paxInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      occasionSelect?.focus();
    }
  });

  // Occasion -> Venue City
  occasionSelect?.addEventListener("change", () => {
    if (occasionSelect.value) venueCityInput?.focus();
  });

  // Venue City Search and Selection -> Venue Street
  let vTimer = null;
  venueCityInput?.addEventListener("input", () => {
    clearTimeout(vTimer);
    vTimer = setTimeout(async () => {
      const q = venueCityInput.value;
      if (q.trim().length < 2) { venueResults.innerHTML = ""; return; }
      const results = await api.searchAddress(q);
      venueResults.innerHTML = results.map(
        (r) => `<div class="btn btn-secondary btn-block" style="margin-bottom:6px; text-align:left; justify-content:flex-start; font-size:13px;" data-addr="${escapeHtml(r.display_text)}">${icon("search")} ${escapeHtml(r.display_text)}</div>`
      ).join("");
      venueResults.querySelectorAll("[data-addr]").forEach((el) => {
        el.addEventListener("click", () => {
          venueCityInput.value = el.dataset.addr;
          venueResults.innerHTML = "";
          venueStreetInput?.focus();
        });
      });
    }, 250);
  });
  venueCityInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      venueStreetInput?.focus();
    }
  });

  // Venue Street -> Scroll to Package selection
  venueStreetInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      card.querySelector("#pkg-grid")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });

  const priceInput = card.querySelector("#e-price-per-pax");
  const baseInput = card.querySelector("#e-base-total");
  let syncing = false;

  function syncFromPricePerPax() {
    if (syncing) return;
    syncing = true;
    const pax = Number(paxInput.value || 0);
    const price = Number(priceInput.value || 0);
    d.event.pax = pax;
    d.package.pricePerPax = price;
    baseInput.value = (price * pax).toFixed(2);
    d.package.baseTotal = Number(baseInput.value);
    syncing = false;
    renderCart();
  }

  function syncFromBaseTotal() {
    if (syncing) return;
    syncing = true;
    const pax = Number(paxInput.value || 0);
    const base = Number(baseInput.value || 0);
    d.event.pax = pax;
    d.package.baseTotal = base;
    if (pax > 0) {
      priceInput.value = (base / pax).toFixed(2);
      d.package.pricePerPax = Number(priceInput.value);
    }
    syncing = false;
    renderCart();
  }

  paxInput.addEventListener("input", syncFromPricePerPax);
  priceInput.addEventListener("input", syncFromPricePerPax);
  baseInput.addEventListener("input", syncFromBaseTotal);

  function selectPackage(pkg) {
    card.querySelectorAll(".select-card").forEach((c) => {
      c.classList.remove("selected");
      c.querySelector(".kiosk-card-badge").innerHTML = icon("plus");
    });
    const selectedCard = card.querySelector(`.select-card[data-id="${pkg.id}"]`);
    if (selectedCard) {
      selectedCard.classList.add("selected");
      selectedCard.querySelector(".kiosk-card-badge").innerHTML = icon("checkCircle");
    }

    d.package.id = pkg.id;
    d.package.name = pkg.name;
    d.package.pricePerPax = pkg.price_per_pax;
    d.package.minPax = pkg.min_pax;
    d.package.description = pkg.description;

    const currentPax = Number(paxInput.value || 0);
    if (currentPax < pkg.min_pax) {
      d.event.pax = pkg.min_pax;
      paxInput.value = pkg.min_pax;
    }
    priceInput.value = pkg.price_per_pax;
    syncFromPricePerPax();
  }

  card.querySelectorAll(".select-card").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.closest(".btn-view-pkg-details")) return;
      const pkg = packagesCache.find((p) => String(p.id) === el.dataset.id);
      selectPackage(pkg);
    });
  });

  card.querySelectorAll(".btn-view-pkg-details").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const pkg = packagesCache.find((p) => String(p.id) === btn.dataset.pkgDetails);
      if (pkg) openPackageDetailsModal(pkg, selectPackage);
    });
  });

  footer("Next Step", () => {
    d.event.date = card.querySelector("#e-date").value;
    d.event.time = card.querySelector("#e-time").value || "18:00";
    d.event.pax = Number(paxInput.value || 0);
    d.event.occasion = card.querySelector("#e-occasion").value;
    d.event.venueStreet = (venueStreetInput.value || "").trim();
    d.event.venueCity = (venueCityInput.value || "").trim();
    d.event.venue = [d.event.venueStreet, d.event.venueCity].filter(Boolean).join(", ");
    d.package.pricePerPax = Number(priceInput.value || 0);
    d.package.baseTotal = Number(baseInput.value || 0);

    if (!d.event.venue.trim()) { toast("Venue address is required.", "error"); return; }
    if (!d.package.id && !d.package.baseTotal) { toast("Please choose a package or set base total.", "error"); return; }
    if (!d.event.date) { toast("Event date is required.", "error"); return; }
    wizard.step = 3;
    render();
  });
}

// ── Step 3: Menu & Add-ons (Mix & Match) ─────────────────────────────

async function renderStepMenu(card) {
  const d = wizard.draft;
  card.innerHTML = `<h2 style="margin:0 0 10px;">${icon("utensils")} Menu Selection</h2><p style="color:var(--text-muted);">Loading menu items…</p>`;
  menuGroupedCache = await api.getMenuItemsGrouped();

  const selectedIds = new Set(d.menuSelections.map((m) => m.menu_item_id));
  const categories = Object.keys(menuGroupedCache);

  card.innerHTML = `
    <div class="kiosk-menu-sticky-header">
      <div class="kiosk-menu-header-row" style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:10px; flex-wrap:wrap;">
        <div class="kiosk-menu-header-info" style="flex:1; min-width:220px;">
          <h2 style="margin:0 0 4px; display:flex; align-items:center; gap:10px;">
            ${icon("utensils")} Mix &amp; Match Menu Dishes
          </h2>
          <p style="color:var(--text-muted); margin:0; font-size:13px;">
            Select the dishes for your catering buffet. Tap dish photo or card to add or remove.
          </p>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <button type="button" class="btn btn-primary" id="sticky-next-btn-top" style="padding:10px 20px; font-weight:800; display:inline-flex; align-items:center; gap:8px; box-shadow:0 4px 14px var(--accent-glow);">
            Next Step ${icon("arrowRight")}
          </button>
        </div>
      </div>

      <!-- Live Search Bar & Category Navigation -->
      <div style="display:flex; gap:10px; align-items:center; margin-bottom:12px; flex-wrap:wrap;">
        <div style="position:relative; flex:1; min-width:220px;">
          <input type="text" class="form-control" id="menu-dish-search" placeholder="Search dish name, ingredients or category…" style="padding-left:36px; padding-right:32px; height:40px; font-size:13.5px; border-radius:20px;">
          <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--text-muted); pointer-events:none;">${icon("search")}</span>
          <button type="button" id="menu-dish-search-clear" style="display:none; position:absolute; right:10px; top:50%; transform:translateY(-50%); background:transparent; border:none; color:var(--text-muted); cursor:pointer; font-size:14px; padding:2px 6px;">✕</button>
        </div>
        <div id="search-match-count" style="display:none; font-size:12.5px; color:var(--gold); font-weight:700;"></div>
      </div>

      <!-- Quick Category Filter Bar -->
      <div class="kiosk-cat-bar" id="kiosk-cat-bar">
        <button type="button" class="kiosk-cat-pill active" data-cat="all">
          All Dishes
          <span class="pill pill-partial" style="padding:2px 7px; font-size:11px;" id="all-selected-count">0</span>
        </button>
        ${categories.map((cat) => `
          <button type="button" class="kiosk-cat-pill" data-cat="${escapeHtml(cat)}">
            ${escapeHtml(cat)}
            <span class="pill pill-partial" style="padding:2px 7px; font-size:11px;" data-pill-count="${escapeHtml(cat)}">0</span>
          </button>
        `).join("")}
      </div>
    </div>

    <div id="menu-categories-container">
      ${Object.entries(menuGroupedCache).map(([cat, items]) => `
        <div class="kiosk-category-section" id="cat-sec-${escapeHtml(cat.replace(/[^a-zA-Z0-9]/g, "-"))}" data-category-name="${escapeHtml(cat.toLowerCase())}" style="margin-bottom:28px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1.5px solid var(--border); padding-bottom:8px;">
            <h4 style="margin:0; font-size:17px; font-weight:800; color:var(--text);">${escapeHtml(cat)}</h4>
            <span class="pill pill-partial" data-count-for="${escapeHtml(cat)}">0 Selected</span>
          </div>
          <div class="kiosk-grid">
            ${items.map((it) => {
              const isSel = selectedIds.has(it.menu_item_id);
              return `
                <div class="kiosk-food-card select-card ${isSel ? "selected" : ""}" data-item-id="${it.menu_item_id}" data-item-name="${escapeHtml((it.name || '').toLowerCase())}" data-item-desc="${escapeHtml((it.description || '').toLowerCase())}" data-item-cat="${escapeHtml(cat.toLowerCase())}">
                  <div class="kiosk-card-img-wrap">
                    ${it.image ? `<img src="${it.image}" alt="${escapeHtml(it.name)}" class="kiosk-card-img">` : `
                      <div class="kiosk-card-placeholder">
                        ${icon("utensils")}
                        <span style="font-size:11px; font-weight:700; opacity:0.85;">${escapeHtml(cat)}</span>
                      </div>
                    `}
                    <div class="kiosk-card-badge item-check-badge">
                      ${isSel ? icon("checkCircle") : icon("plus")}
                    </div>
                  </div>
                  <div class="kiosk-card-body">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                      <h4 class="kiosk-card-title">${escapeHtml(it.name)}</h4>
                      <button type="button" class="btn btn-ghost btn-view-dish-details" data-dish-details="${it.menu_item_id}" style="padding:3px 8px; font-size:11px; height:24px; border-radius:12px; white-space:nowrap; flex-shrink:0;" title="View Dish Details & Photo">
                        ${icon("info")} Details
                      </button>
                    </div>
                    <p class="kiosk-card-desc">${escapeHtml(it.description || "Freshly prepared catering specialty.")}</p>
                    <div class="kiosk-card-footer">
                      <span class="kiosk-price-tag">${it.price ? `+ ${peso(it.price)}` : `<span style="font-size:13px; color:var(--success); font-weight:700;">Included</span>`}</span>
                      <span class="kiosk-status-pill">${it.price ? "Add-on" : "Buffet Included"}</span>
                    </div>
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        </div>
      `).join("") || "<p style='color:var(--text-muted);'>No menu items available.</p>"}
    </div>
    <div id="menu-no-search-results" style="display:none; padding:48px 24px; text-align:center; color:var(--text-muted);">
      <div style="font-size:36px; margin-bottom:8px;">🔍</div>
      <h3 style="margin:0 0 6px; color:var(--text);">No dishes found</h3>
      <p style="margin:0 0 16px; font-size:13.5px;">Try searching for a different dish name or category.</p>
      <button type="button" class="btn btn-secondary" id="btn-clear-search-empty">Clear Search Filter</button>
    </div>
  `;

  // Search logic
  const searchInput = card.querySelector("#menu-dish-search");
  const clearBtn = card.querySelector("#menu-dish-search-clear");
  const matchCountEl = card.querySelector("#search-match-count");
  const noResultsEl = card.querySelector("#menu-no-search-results");
  const foodCards = card.querySelectorAll(".kiosk-food-card");
  const categorySections = card.querySelectorAll(".kiosk-category-section");

  const filterDishes = () => {
    const q = (searchInput?.value || "").toLowerCase().trim();
    if (clearBtn) clearBtn.style.display = q ? "block" : "none";

    let visibleCount = 0;
    categorySections.forEach((sec) => {
      let secHasVisible = false;
      const cardsInSec = sec.querySelectorAll(".kiosk-food-card");
      cardsInSec.forEach((c) => {
        const name = c.dataset.itemName || "";
        const desc = c.dataset.itemDesc || "";
        const cat = c.dataset.itemCat || "";
        const matches = !q || name.includes(q) || desc.includes(q) || cat.includes(q);
        c.style.display = matches ? "" : "none";
        if (matches) {
          secHasVisible = true;
          visibleCount++;
        }
      });
      sec.style.display = secHasVisible ? "" : "none";
    });

    if (q) {
      matchCountEl.style.display = "block";
      matchCountEl.textContent = `${visibleCount} dish${visibleCount === 1 ? "" : "es"} found`;
    } else {
      matchCountEl.style.display = "none";
    }

    if (noResultsEl) {
      noResultsEl.style.display = visibleCount === 0 ? "block" : "none";
    }
  };

  searchInput?.addEventListener("input", filterDishes);
  clearBtn?.addEventListener("click", () => {
    if (searchInput) {
      searchInput.value = "";
      filterDishes();
      searchInput.focus();
    }
  });
  card.querySelector("#btn-clear-search-empty")?.addEventListener("click", () => {
    if (searchInput) {
      searchInput.value = "";
      filterDishes();
    }
  });

  // Smooth scroll to category on pill click
  card.querySelectorAll(".kiosk-cat-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      card.querySelectorAll(".kiosk-cat-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      const cat = pill.dataset.cat;
      if (cat === "all") {
        if (searchInput) { searchInput.value = ""; filterDishes(); }
        card.querySelector("#menu-categories-container")?.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      const targetSec = card.querySelector(`#cat-sec-${cat.replace(/[^a-zA-Z0-9]/g, "-")}`);
      if (targetSec) {
        targetSec.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  function updateCounts() {
    const counts = {};
    for (const m of d.menuSelections) counts[m.category] = (counts[m.category] || 0) + 1;
    card.querySelectorAll("[data-count-for]").forEach((el) => {
      const cat = el.dataset.countFor;
      const cnt = counts[cat] || 0;
      el.textContent = `${cnt} Selected`;
      el.className = `pill ${cnt > 0 ? "pill-paid" : "pill-partial"}`;
    });
    card.querySelectorAll("[data-pill-count]").forEach((el) => {
      const cat = el.dataset.pillCount;
      const cnt = counts[cat] || 0;
      el.textContent = cnt;
      el.className = `pill ${cnt > 0 ? "pill-paid" : "pill-partial"}`;
    });
    const allPill = card.querySelector("#all-selected-count");
    if (allPill) {
      allPill.textContent = d.menuSelections.length;
      allPill.className = `pill ${d.menuSelections.length > 0 ? "pill-paid" : "pill-partial"}`;
    }
  }

  const goNextStep = () => { wizard.step = 4; render(); };
  const topNextBtn = card.querySelector("#sticky-next-btn-top");
  if (topNextBtn) topNextBtn.addEventListener("click", goNextStep);

  const allItems = Object.values(menuGroupedCache).flat();
  card.querySelectorAll(".select-card").forEach((el) => {
    const item = allItems.find((it) => String(it.menu_item_id) === el.dataset.itemId);
    el.addEventListener("click", () => {
      const idx = d.menuSelections.findIndex((m) => m.menu_item_id === item.menu_item_id);
      if (idx === -1) {
        d.menuSelections.push({ menu_item_id: item.menu_item_id, item_name: item.name, category: item.category, price: item.price, quantity: 1 });
        el.classList.add("selected");
        el.querySelector(".item-check-badge").innerHTML = icon("checkCircle");
      } else {
        d.menuSelections.splice(idx, 1);
        el.classList.remove("selected");
        el.querySelector(".item-check-badge").innerHTML = icon("plus");
      }
      updateCounts();
      renderCart();
    });
  });

  // Dish details viewer button
  card.querySelectorAll(".btn-view-dish-details").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const itemId = btn.dataset.dishDetails;
      const item = allItems.find((it) => String(it.menu_item_id) === String(itemId));
      if (!item) return;
      const isSelected = d.menuSelections.some((m) => m.menu_item_id === item.menu_item_id);
      openDishDetailsModal(item, isSelected, () => {
        const idx = d.menuSelections.findIndex((m) => m.menu_item_id === item.menu_item_id);
        const cardEl = card.querySelector(`.select-card[data-item-id="${item.menu_item_id}"]`);
        if (idx === -1) {
          d.menuSelections.push({ menu_item_id: item.menu_item_id, item_name: item.name, category: item.category, price: item.price, quantity: 1 });
          if (cardEl) {
            cardEl.classList.add("selected");
            cardEl.querySelector(".item-check-badge").innerHTML = icon("checkCircle");
          }
        } else {
          d.menuSelections.splice(idx, 1);
          if (cardEl) {
            cardEl.classList.remove("selected");
            cardEl.querySelector(".item-check-badge").innerHTML = icon("plus");
          }
        }
        updateCounts();
        renderCart();
      });
    });
  });
  updateCounts();

  footer(`Next Step: Event Add-ons (${d.menuSelections.length} Chosen)`, () => { wizard.step = 4; render(); });
}

// ── Step 4: Add-ons & Extras (Upsell) ────────────────────────────────

function renderStepAddons(card) {
  const d = wizard.draft;
  card.innerHTML = `
    <h2 style="margin:0 0 8px; display:flex; align-items:center; gap:10px;">
      ${icon("plus")} Add-ons &amp; Extras
    </h2>
    <p style="color:var(--text-muted); margin:0 0 20px; font-size:14px;">
      Add popular equipment, lechon platters, beverage stations, or custom discounts.
    </p>

    <h3 style="font-size:16px; margin:0 0 12px;">Popular Event Add-ons</h3>
    <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:24px;">
      ${UPSELLS.map((u, i) => `
        <div class="card card-elevated" style="display:flex; justify-content:space-between; align-items:center; padding:16px 20px;">
          <div>
            <div style="font-weight:700; font-size:15px; color:var(--text);">${escapeHtml(u.name)}</div>
            <div style="font-weight:700; color:var(--gold); font-size:14px;">${peso(u.price)}</div>
          </div>
          <button class="btn btn-secondary" data-upsell="${i}" style="padding:8px 16px;">
            ${icon("plus")} Add
          </button>
        </div>
      `).join("")}
    </div>

    <h3 style="font-size:16px; margin:0 0 12px;">Custom Charge or Discount</h3>
    <div class="grid-2">
      <div class="form-group">
        <label>Description</label>
        <input type="text" class="form-control" id="charge-desc" placeholder="e.g. Delivery fee or VIP Discount">
      </div>
      <div class="form-group">
        <label>Amount (Negative for Discount)</label>
        <input type="number" class="form-control" id="charge-amount" step="0.01" placeholder="₱ 0.00">
      </div>
    </div>
    <button class="btn btn-secondary" id="add-charge">
      ${icon("plus")} Add Custom Charge / Discount
    </button>

    <h3 style="font-size:16px; margin:24px 0 12px;">Applied Extras &amp; Charges</h3>
    <div id="charge-list"></div>
  `;

  function renderChargeList() {
    const list = card.querySelector("#charge-list");
    list.innerHTML = d.additionalCharges.map((c, i) => `
      <div class="card card-elevated" style="display:flex; justify-content:space-between; align-items:center; padding:12px 18px; margin-bottom:8px;">
        <span style="font-weight:600;">${escapeHtml(c.description)}</span>
        <div style="display:flex; align-items:center; gap:12px;">
          <span style="font-weight:700; color:var(--gold);">${peso(c.amount)}</span>
          <button class="icon-btn icon-btn-danger" data-remove="${i}" style="width:32px; height:32px;">${icon("trash")}</button>
        </div>
      </div>
    `).join("") || `<p style="color:var(--text-muted); padding:10px;">No additional charges applied.</p>`;
    
    list.querySelectorAll("[data-remove]").forEach((el) => {
      el.addEventListener("click", () => {
        d.additionalCharges.splice(Number(el.dataset.remove), 1);
        renderChargeList();
        renderCart();
      });
    });
  }
  renderChargeList();

  card.querySelectorAll("[data-upsell]").forEach((el) => {
    el.addEventListener("click", () => {
      const u = UPSELLS[Number(el.dataset.upsell)];
      d.additionalCharges.push({ description: u.name, amount: u.price });
      toast(`Added ${u.name}`, "success");
      renderChargeList();
      renderCart();
    });
  });

  card.querySelector("#add-charge").addEventListener("click", () => {
    const desc = card.querySelector("#charge-desc").value.trim();
    const amount = Number(card.querySelector("#charge-amount").value || 0);
    if (!desc) { toast("Enter a charge description.", "error"); return; }
    d.additionalCharges.push({ description: desc, amount });
    card.querySelector("#charge-desc").value = "";
    card.querySelector("#charge-amount").value = "";
    renderChargeList();
    renderCart();
  });

  footer("Next Step", () => { wizard.step = 5; render(); });
}

// ── Step 5: Billing & Payment ─────────────────────────────────────────

function renderStepBilling(card) {
  const d = wizard.draft;
  const total = grandTotal(d);
  card.innerHTML = `
    <h2 style="margin:0 0 8px; display:flex; align-items:center; gap:10px;">
      ${icon("fileText")} Billing &amp; Payment
    </h2>
    <p style="color:var(--text-muted); margin:0 0 20px; font-size:14px;">
      Set initial downpayment amount, choose the payment method, and write special notes.
    </p>

    <div class="card card-elevated" style="margin-bottom:20px; padding:20px;">
      <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:6px;">
        <span style="color:var(--text-muted);">Package Base Total</span>
        <span style="font-weight:700;">${peso(d.package.baseTotal)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:10px;">
        <span style="color:var(--text-muted);">Add-ons / Adjustments</span>
        <span style="font-weight:700; color:var(--gold);">${peso(chargesTotal(d))}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:18px; border-top:1.5px solid var(--border); padding-top:10px;">
        <span style="font-weight:700;">Total Amount</span>
        <span style="font-family:'Outfit',sans-serif; font-weight:800; color:var(--gold); font-size:24px;">${peso(total)}</span>
      </div>
    </div>

    <div style="display:flex; gap:10px; margin-bottom:14px;">
      <button class="btn btn-secondary" id="dp-50" style="flex:1;">50% Downpayment</button>
      <button class="btn btn-secondary" id="dp-full" style="flex:1;">100% Fully Paid</button>
    </div>
    
    <div class="form-group">
      <label>Down Payment Amount (₱)</label>
      <input type="number" class="form-control" id="dp-amount" step="0.01" value="${d.downPayment}">
    </div>
    <div class="form-group">
      <label>Payment Method</label>
      <select class="form-control" id="pay-method">
        ${["Cash", "GCash", "Maya", "Bank Transfer", "Check", "Other"].map((m) => `<option value="${m}" ${d.paymentMethod === m ? "selected" : ""}>${m}</option>`).join("")}
      </select>
    </div>
    <div class="form-group">
      <label>Special Instructions / Event Notes</label>
      <textarea class="form-control" id="notes" rows="3" placeholder="Theme, setup instructions, dietary restrictions…">${escapeHtml(d.notes)}</textarea>
    </div>
  `;

  const dpInput = card.querySelector("#dp-amount");
  dpInput.addEventListener("input", () => {
    d.downPayment = Number(dpInput.value || 0);
    renderCart();
  });
  card.querySelector("#dp-50").addEventListener("click", () => { 
    dpInput.value = (total * 0.5).toFixed(2); 
    d.downPayment = Number(dpInput.value);
    renderCart();
  });
  card.querySelector("#dp-full").addEventListener("click", () => { 
    dpInput.value = total.toFixed(2); 
    d.downPayment = Number(dpInput.value);
    renderCart();
  });

  footer("Review Order", () => {
    const dp = Number(dpInput.value || 0);
    if (dp > total) { toast("Down payment cannot exceed total.", "error"); return; }
    d.downPayment = dp;
    d.paymentMethod = card.querySelector("#pay-method").value;
    d.notes = card.querySelector("#notes").value;
    wizard.step = 6;
    render();
  });
}

// ── Step 6: Preview & Confirm ─────────────────────────────────────────

function renderStepPreview(card) {
  const d = wizard.draft;
  const total = grandTotal(d);
  const balance = Math.max(0, total - (d.downPayment || 0));
  card.innerHTML = `
    <h2 style="margin:0 0 8px; display:flex; align-items:center; gap:10px;">
      ${icon("checkCircle")} Final Order Confirmation
    </h2>
    <p style="color:var(--text-muted); margin:0 0 20px; font-size:14px;">
      Please review all order details before confirming the booking.
    </p>

    <div class="grid-2" style="margin-bottom:20px;">
      <div class="card card-elevated" style="padding:16px;">
        <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Customer</div>
        <div style="font-size:16px; font-weight:700; color:var(--text); margin-top:4px;">${escapeHtml(d.customer.name)}</div>
        <div style="font-size:13px; color:var(--text-muted);">${escapeHtml(d.customer.contact || "—")}</div>
      </div>
      <div class="card card-elevated" style="padding:16px;">
        <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Event Schedule</div>
        <div style="font-size:16px; font-weight:700; color:var(--text); margin-top:4px;">${escapeHtml(d.event.date)} at ${escapeHtml(d.event.time)}</div>
        <div style="font-size:13px; color:var(--gold); font-weight:700;">${d.event.pax} Guests · ${escapeHtml(d.event.venue)}</div>
      </div>
    </div>

    <div class="card card-elevated" style="padding:18px; margin-bottom:20px;">
      <div style="font-size:14px; font-weight:700; margin-bottom:6px;">Package &amp; Menu Selections</div>
      <div style="color:var(--gold); font-weight:700; font-size:15px; margin-bottom:8px;">${escapeHtml(d.package.name)} (${peso(d.package.pricePerPax)} / pax)</div>
      <p style="color:var(--text-muted); font-size:13px; margin:0; line-height:1.6;">
        ${d.menuSelections.map((m) => escapeHtml(m.item_name)).join(", ") || "No specific dishes selected."}
      </p>
    </div>

    <div class="card" style="border:1.5px solid var(--accent); padding:20px; background:linear-gradient(135deg, rgba(225,29,72,0.1) 0%, var(--card) 100%);">
      <div style="display:flex; justify-content:space-between; font-size:15px; margin-bottom:6px;">
        <span>Grand Total</span>
        <span style="font-weight:700; color:var(--gold);">${peso(total)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:15px; margin-bottom:8px;">
        <span>Down Payment (${d.paymentMethod})</span>
        <span style="font-weight:700; color:var(--success);">${peso(d.downPayment)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:18px; border-top:1.5px solid var(--border); padding-top:10px;">
        <span style="font-weight:800;">Balance Due</span>
        <span style="font-family:'Outfit',sans-serif; font-size:22px; font-weight:800; color:var(--text);">${peso(balance)}</span>
      </div>
    </div>
  `;

  const wrap = document.createElement("div");
  wrap.style.cssText = "display:flex; justify-content:space-between; align-items:center; margin-top:28px; border-top:1.5px solid var(--border); padding-top:20px;";
  wrap.innerHTML = `
    <button class="btn btn-secondary" id="wiz-back">
      ${icon("arrowLeft")} Back
    </button>
    <button class="btn btn-primary btn-lg" id="confirm-order">
      ${icon("check")} Confirm &amp; Save Booking
    </button>
  `;
  card.appendChild(wrap);
  wrap.querySelector("#wiz-back").addEventListener("click", () => { wizard.step = 5; render(); });

  function openBookingConfirmationDrawer() {
    const confirmModalId = "booking-confirm-drawer";
    const grandTotal = d.package.baseTotal + d.additionalCharges.reduce((s, c) => s + Number(c.amount || 0), 0);
    const balanceDue = Math.max(0, grandTotal - Number(d.downPayment || 0));

    openModal({
      id: confirmModalId,
      title: `${icon("checkCircle")} Final Booking Confirmation`,
      bodyHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="text-align:center; padding:6px 0 2px;">
            <div style="width:54px; height:54px; border-radius:50%; background:rgba(225, 29, 72, 0.12); color:var(--accent); display:inline-flex; align-items:center; justify-content:center; margin-bottom:10px;">
              ${icon("calendar")}
            </div>
            <h3 style="margin:0 0 4px; font-size:19px;">Please Verify Your Event Details</h3>
            <p style="color:var(--text-muted); font-size:13px; margin:0;">Confirm that all client and event information is correct before placing.</p>
          </div>

          <div class="card card-elevated" style="padding:16px;">
            <div style="font-size:11.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:6px; letter-spacing:0.04em;">
              Client &amp; Event Schedule
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Customer</span>
              <span style="font-weight:700;">${escapeHtml(d.customer.name)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Phone Number</span>
              <span>${escapeHtml(d.customer.contact || "—")}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Event Date &amp; Time</span>
              <span style="font-weight:700;">${escapeHtml(d.event.date)} · ${escapeHtml(d.event.time || "18:00")}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:13px;">
              <span style="color:var(--text-muted);">Venue</span>
              <span style="text-align:right; max-width:60%; font-weight:600;">${escapeHtml(d.event.venue)}</span>
            </div>
          </div>

          <div class="card card-elevated" style="padding:16px;">
            <div style="font-size:11.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:6px; letter-spacing:0.04em;">
              Catering Package &amp; Payment Summary
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Package</span>
              <span style="font-weight:700;">${escapeHtml(d.package.name || "Custom Package")} (${d.event.pax} Pax)</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Selected Dishes</span>
              <span>${d.menuSelections.length} dishes chosen</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Grand Total</span>
              <span style="font-weight:800; font-size:16px; color:var(--gold);">${peso(grandTotal)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px;">
              <span style="color:var(--text-muted);">Down Payment</span>
              <span style="font-weight:700; color:var(--success);">${peso(d.downPayment)} (${escapeHtml(d.paymentMethod)})</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:13px;">
              <span style="color:var(--text-muted);">Remaining Balance</span>
              <span style="font-weight:700; color:${balanceDue > 0 ? "var(--danger)" : "var(--success)"};">${peso(balanceDue)}</span>
            </div>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary" data-close>${icon("arrowLeft")} Review &amp; Edit</button>
        <button class="btn btn-primary" id="btn-final-confirm-order">${icon("checkCircle")} Yes, Confirm Booking!</button>
      `,
    });

    const confirmModal = document.getElementById(confirmModalId);
    confirmModal.querySelector("#btn-final-confirm-order").addEventListener("click", async () => {
      const finalBtn = confirmModal.querySelector("#btn-final-confirm-order");
      finalBtn.disabled = true;
      finalBtn.innerHTML = `${icon("refresh")} Saving Booking…`;
      try {
        const terms = await api.terms();
        const payload = {
          customer_id: d.customer.id,
          customer_name: d.customer.name,
          contact: d.customer.contact,
          email: d.customer.email,
          address: d.customer.address,
          event_date: d.event.date,
          event_time: d.event.time,
          venue: d.event.venue,
          occasion: d.event.occasion,
          pax: d.event.pax,
          package_id: d.package.id,
          base_total: d.package.baseTotal,
          menu_selections: d.menuSelections,
          additional_charges: d.additionalCharges,
          down_payment: d.downPayment,
          payment_method: d.paymentMethod,
          notes: d.notes,
          terms_version: terms.version,
        };
        lastCreatedOrder = await api.placeOrder(payload);
        closeModal(confirmModalId);
        toast("Booking successfully created!", "success");
        renderReceipt(card);
      } catch (err) {
        toast("Failed to place order: " + err.message, "error");
        finalBtn.disabled = false;
        finalBtn.innerHTML = `${icon("checkCircle")} Yes, Confirm Booking!`;
      }
    });
  }

  wrap.querySelector("#confirm-order").addEventListener("click", openBookingConfirmationDrawer);
}

function renderReceipt(card) {
  const o = lastCreatedOrder;
  card.innerHTML = `
    <div style="text-align:center; padding:20px 0;">
      <div style="width:68px; height:68px; border-radius:50%; background:var(--success-bg); color:var(--success); display:inline-flex; align-items:center; justify-content:center; margin-bottom:16px; box-shadow:0 0 25px var(--success-glow);">
        ${icon("checkCircle")}
      </div>
      <h2 style="margin:0 0 8px; font-size:26px;">Thank You for Choosing Jayraldine's!</h2>
      <p style="color:var(--text-muted); font-size:14.5px; line-height:1.5; margin:0 0 24px; max-width:480px; margin-left:auto; margin-right:auto;">
        Your catering booking has been successfully placed. We are thrilled and honored to serve your special event!
      </p>
    </div>

    <div class="card card-elevated" style="padding:22px; margin-bottom:24px;">
      <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
        <span style="color:var(--text-muted);">Booking Reference</span>
        <span style="font-weight:800; font-size:18px; color:var(--gold);">${escapeHtml(o.booking_ref)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
        <span style="color:var(--text-muted);">Total Order Amount</span>
        <span style="font-weight:700;">${peso(o.total)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
        <span style="color:var(--text-muted);">Down Payment Received</span>
        <span style="font-weight:700; color:var(--success);">${peso(o.paid)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
        <span style="color:var(--text-muted);">Balance Due</span>
        <span style="font-weight:700;">${peso(o.balance)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; border-top:1.5px solid var(--border); padding-top:12px;">
        <span style="color:var(--text-muted);">Payment Status</span>
        <span>${statusPill(o.status)}</span>
      </div>
    </div>

    <div style="display:flex; gap:12px;">
      <button class="btn btn-secondary btn-block" id="print-receipt">
        ${icon("download")} Download PDF Receipt
      </button>
      <button class="btn btn-primary btn-block" id="done-btn">
        ${icon("home")} Return to Home
      </button>
    </div>
  `;
  const cart = document.getElementById("wizard-cart");
  if (cart) cart.innerHTML = "";

  card.querySelector("#print-receipt").addEventListener("click", () => {
    api.downloadReceipt(o.booking_id);
  });
  card.querySelector("#done-btn").addEventListener("click", () => {
    const doneBtn = card.querySelector("#done-btn");
    doneBtn.disabled = true;
    doneBtn.innerHTML = `${icon("refresh")} Returning…`;
    wizard.reset();
    window.dispatchEvent(new CustomEvent("kiosk:home", {
      detail: { transition: true, message: "Thank you for booking! Resetting kiosk for the next guest…" }
    }));
  });
}

function openPackageDetailsModal(p, selectCallback) {
  const modalId = "pkg-details-modal";
  openModal({
    id: modalId,
    title: `${icon("package")} ${escapeHtml(p.name)} Inclusions &amp; Details`,
    bodyHtml: `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="width:100%; height:190px; border-radius:var(--radius); overflow:hidden; background:var(--input-bg); border:1.5px solid var(--border); display:flex; align-items:center; justify-content:center;">
          ${p.image ? `<img src="${p.image}" alt="${escapeHtml(p.name)}" style="width:100%; height:100%; object-fit:cover;">` : `
            <div style="display:flex; flex-direction:column; align-items:center; gap:8px; color:var(--text-muted);">
              ${icon("package")}
              <span style="font-size:14px; font-weight:700;">${escapeHtml(p.name)}</span>
            </div>
          `}
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; background:var(--card-elevated); padding:14px 18px; border-radius:var(--radius); border:1.5px solid var(--border);">
          <div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Price Rate</div>
            <div style="font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; color:var(--gold);">${peso(p.price_per_pax)}<span style="font-size:13px; font-weight:600; color:var(--text-muted); font-family:inherit;"> / pax</span></div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Minimum Pax</div>
            <div style="font-size:17px; font-weight:800; color:var(--text);">${p.min_pax} Guests</div>
          </div>
        </div>

        <div>
          <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin:0 0 6px; letter-spacing:0.04em;">Package Summary</h4>
          <p style="font-size:13.5px; line-height:1.6; color:var(--text); margin:0; background:var(--input-bg); padding:12px 16px; border-radius:var(--radius-sm); border:1px solid var(--border);">
            ${escapeHtml(p.description || "Full-service buffet catering package with dining setup, quality food chafers, tableware and dedicated service staff.")}
          </p>
        </div>

        <div>
          <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin:0 0 8px; letter-spacing:0.04em;">Buffet Catering Inclusions</h4>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
            <div class="card" style="padding:10px 12px; font-size:12.5px; display:flex; align-items:center; gap:8px;">
              <span style="color:var(--success); font-weight:700;">${icon("check")}</span> Buffet Table &amp; Skirting
            </div>
            <div class="card" style="padding:10px 12px; font-size:12.5px; display:flex; align-items:center; gap:8px;">
              <span style="color:var(--success); font-weight:700;">${icon("check")}</span> Chafing Dishes &amp; Warmers
            </div>
            <div class="card" style="padding:10px 12px; font-size:12.5px; display:flex; align-items:center; gap:8px;">
              <span style="color:var(--success); font-weight:700;">${icon("check")}</span> Complete Dining Tableware
            </div>
            <div class="card" style="padding:10px 12px; font-size:12.5px; display:flex; align-items:center; gap:8px;">
              <span style="color:var(--success); font-weight:700;">${icon("check")}</span> Waiters &amp; Catering Staff
            </div>
            <div class="card" style="padding:10px 12px; font-size:12.5px; display:flex; align-items:center; gap:8px;">
              <span style="color:var(--success); font-weight:700;">${icon("check")}</span> Purified Drinking Water &amp; Ice
            </div>
            <div class="card" style="padding:10px 12px; font-size:12.5px; display:flex; align-items:center; gap:8px;">
              <span style="color:var(--success); font-weight:700;">${icon("check")}</span> Floral Table Centerpiece
            </div>
          </div>
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn btn-primary" id="modal-select-pkg">${icon("checkCircle")} Select This Package</button>
    `,
  });

  const modal = document.getElementById(modalId);
  modal.querySelector("#modal-select-pkg").addEventListener("click", () => {
    selectCallback(p);
    closeModal(modalId);
    toast(`Selected ${p.name}!`, "success");
  });
}

function openDishDetailsModal(it, isSelected, toggleCallback) {
  const modalId = "dish-details-modal";
  let currentlySelected = isSelected;

  openModal({
    id: modalId,
    title: `${icon("utensils")} ${escapeHtml(it.name)}`,
    bodyHtml: `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="width:100%; height:220px; border-radius:var(--radius); overflow:hidden; background:var(--input-bg); border:1.5px solid var(--border); display:flex; align-items:center; justify-content:center;">
          ${it.image ? `<img src="${it.image}" alt="${escapeHtml(it.name)}" style="width:100%; height:100%; object-fit:cover;">` : `
            <div style="display:flex; flex-direction:column; align-items:center; gap:8px; color:var(--text-muted);">
              ${icon("utensils")}
              <span style="font-size:14px; font-weight:700;">${escapeHtml(it.name)}</span>
            </div>
          `}
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; background:var(--card-elevated); padding:14px 18px; border-radius:var(--radius); border:1.5px solid var(--border);">
          <div>
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Category</div>
            <div style="font-size:18px; font-weight:800; color:var(--text);">${escapeHtml(it.category || "Main Entree")}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:0.04em;">Price Status</div>
            <div style="font-family:'Outfit',sans-serif; font-size:20px; font-weight:800; color:${it.price ? "var(--gold)" : "var(--success)"};">
              ${it.price ? `+ ${peso(it.price)}` : "Buffet Included"}
            </div>
          </div>
        </div>

        <div>
          <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin:0 0 6px; letter-spacing:0.04em;">Dish Description &amp; Preparation</h4>
          <p style="font-size:14px; line-height:1.6; color:var(--text); margin:0; background:var(--input-bg); padding:14px 16px; border-radius:var(--radius-sm); border:1px solid var(--border);">
            ${escapeHtml(it.description || "Prepared fresh with premium ingredients seasoned to culinary perfection by Jayraldine's kitchen team.")}
          </p>
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Close</button>
      <button class="btn ${currentlySelected ? "btn-danger" : "btn-primary"}" id="modal-dish-toggle-btn">
        ${currentlySelected ? `${icon("trash")} Remove Dish` : `${icon("plus")} Select This Dish`}
      </button>
    `,
  });

  const modal = document.getElementById(modalId);
  const toggleBtn = modal.querySelector("#modal-dish-toggle-btn");
  toggleBtn.addEventListener("click", () => {
    toggleCallback();
    currentlySelected = !currentlySelected;
    toggleBtn.className = `btn ${currentlySelected ? "btn-danger" : "btn-primary"}`;
    toggleBtn.innerHTML = currentlySelected ? `${icon("trash")} Remove Dish` : `${icon("plus")} Select This Dish`;
    toast(currentlySelected ? "Dish added to order!" : "Dish removed from order.", "info");
  });
}
