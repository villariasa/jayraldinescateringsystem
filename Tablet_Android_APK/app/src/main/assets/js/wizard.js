import { api } from "./api.js";
import { wizard, chargesTotal, grandTotal, peso } from "./state.js";
import { toast, escapeHtml, statusPill, openModal, closeModal } from "./views.js";
import { icon } from "./icons.js";
import { getTheme, toggleTheme } from "./app.js";
import { mountLottie } from "./lottie-helper.js";
import { openLiveDbConfigModal } from "./settings.js";

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
let occasionsCache = [];
let lastCreatedOrder = null;
window.__clearWizardCaches = () => {
  packagesCache = [];
  menuGroupedCache = {};
  occasionsCache = [];
};

async function refreshVisiblePackageCards() {
  if (!root || wizard.step !== 2) return;
  const grid = root.querySelector("#pkg-grid");
  if (!grid) return;

  const pkgs = await api.getPackages();
  packagesCache = pkgs;

  for (const p of pkgs) {
    const card = grid.querySelector(`.select-card[data-id="${p.id}"]`);
    const wrap = card?.querySelector(".kiosk-card-img-wrap");
    if (!wrap) continue;

    const badge = wrap.querySelector(".kiosk-card-badge");
    const placeholder = wrap.querySelector(".kiosk-card-placeholder");
    let img = wrap.querySelector("img.kiosk-card-img");

    if (p.image) {
      if (!img) {
        img = document.createElement("img");
        img.className = "kiosk-card-img";
        wrap.insertBefore(img, badge || null);
      }
      img.src = p.image;
      img.alt = p.name || "Package";
      if (placeholder) placeholder.remove();
    } else if (img) {
      img.remove();
    }
  }
}

window.__onMasterDataUpdated = () => {
  refreshVisiblePackageCards().catch(() => {});
};

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
  document.body.classList.add("wizard-mode");
  wizard.reset();
  render();
}

function confirmCancelOrder() {
  openModal({
    id: "cancel-order-modal",
    title: `${icon("alertTriangle")} Discard Draft Order?`,
    bodyHtml: `
      <div style="text-align:center; padding:16px 8px 10px;">
        <div id="discard-lottie-icon" style="width:72px; height:72px; border-radius:50%; background:rgba(239,68,68,0.15); color:var(--danger); display:inline-flex; align-items:center; justify-content:center; margin-bottom:16px; overflow:hidden;">
          ${icon("trash")}
        </div>
        <div id="discard-lottie-msg" style="margin-bottom:6px;">
          <p style="font-size:16px; font-weight:700; color:var(--text); margin:0 0 8px;">Are you sure you want to discard this order?</p>
          <p style="font-size:13.5px; color:var(--text-muted); line-height:1.5; margin:0;">
            All current customer information, package choices, and custom menu dishes will be reset.
          </p>
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary" data-close>Keep Editing</button>
      <button class="btn btn-danger" id="modal-confirm-discard" style="position:relative; overflow:hidden;">
        <span id="discard-yes-icon-wrap" style="display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; vertical-align:middle; margin-right:4px; overflow:hidden;">${icon("trash")}</span>
        Yes, Discard Order
      </button>
    `,
  });

  const modal = document.getElementById("cancel-order-modal");

  // Lottie animation on the trash icon circle
  const discardIconEl = modal.querySelector("#discard-lottie-icon");
  if (discardIconEl) {
    mountLottie(discardIconEl, "toast-error", { loop: true, speed: 0.7 });
  }

  // Lottie animation on the "Yes" button icon
  const yesIconEl = modal.querySelector("#discard-yes-icon-wrap");
  if (yesIconEl) {
    mountLottie(yesIconEl, "toast-error", { loop: true, speed: 0.9 });
  }

  // Entrance animation on the message container
  const msgEl = modal.querySelector("#discard-lottie-msg");
  if (msgEl) {
    msgEl.style.animation = "slideUpFade 0.4s cubic-bezier(0.16,1,0.3,1) both";
  }

  modal.querySelector("#modal-confirm-discard").addEventListener("click", () => {
    closeModal("cancel-order-modal");
    document.body.classList.remove("wizard-mode");
    window.dispatchEvent(new CustomEvent("kiosk:home"));
  });
}

function render() {
  const currentStep = STEPS.find((s) => s.step === wizard.step) || STEPS[0];
  const currentTheme = getTheme();

  root.innerHTML = `
    <div class="wizard-shell">
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
          <div class="card wizard-step-card" id="wizard-step-card" style="animation: slideUpFade 0.3s cubic-bezier(0.16,1,0.3,1);">
            <div class="wizard-step-body" id="wizard-step-body"></div>
            <div class="wizard-step-footer" id="wizard-step-footer"></div>
          </div>
          <div class="card card-elevated" id="wizard-cart"></div>
        </div>
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
    if (window.ResizeObserver) {
      new ResizeObserver(updateHeaderH).observe(headerEl);
    }
  }

  renderStep();
  renderCart();

  const stepBodyEl = document.getElementById("wizard-step-body");
  if (stepBodyEl) {
    stepBodyEl.scrollTop = 0;
  }
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

function wireCartSwipeToRemove(cart) {
  const d = wizard.draft;

  const attachSwipeRow = (wrapper, onRemove) => {
    const content = wrapper.querySelector(".cart-dish-row-content");
    const removeBtn = wrapper.querySelector(".cart-dish-reveal-action");
    if (!content) return;

    const executeRemovalWithAnimation = () => {
      if (wrapper.classList.contains("is-removing")) return;
      wrapper.classList.add("is-removing");
      content.style.transform = "translateX(-100%)";
      setTimeout(() => {
        onRemove();
      }, 200);
    };

    if (removeBtn) {
      removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        executeRemovalWithAnimation();
      });
    }

    let startX = 0;
    let startY = 0;
    let currentX = 0;
    let isTracking = false;
    let isHorizontal = false;
    let isOpen = false;

    const snapTo = (x) => {
      content.style.transition = "transform 0.22s cubic-bezier(0.16, 1, 0.3, 1)";
      content.style.transform = `translateX(${x}px)`;
      isOpen = (x === -80);
    };

    content.addEventListener("click", (e) => {
      if (isOpen) {
        e.stopPropagation();
        snapTo(0);
      }
    });

    content.addEventListener("touchstart", (e) => {
      if (e.touches.length !== 1) return;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      currentX = startX;
      isTracking = true;
      isHorizontal = false;
      content.style.transition = "none";
    }, { passive: true });

    content.addEventListener("touchmove", (e) => {
      if (!isTracking || e.touches.length !== 1) return;
      currentX = e.touches[0].clientX;
      const currentY = e.touches[0].clientY;
      const dx = currentX - startX;
      const dy = currentY - startY;

      if (!isHorizontal) {
        if (Math.abs(dx) > 7 && Math.abs(dx) > Math.abs(dy)) {
          isHorizontal = true;
        } else if (Math.abs(dy) > 7) {
          isTracking = false;
          return;
        }
      }

      if (isHorizontal) {
        if (e.cancelable) e.preventDefault();
        const baseOffset = isOpen ? -80 : 0;
        let targetX = baseOffset + dx;
        if (targetX > 0) targetX = 0;
        if (targetX < -130) targetX = -130 - (targetX + 130) * 0.2;
        content.style.transform = `translateX(${targetX}px)`;
      }
    }, { passive: false });

    const handleTouchEnd = () => {
      if (!isTracking) return;
      isTracking = false;
      if (!isHorizontal) return;

      const dx = currentX - startX;
      const baseOffset = isOpen ? -80 : 0;
      const effectiveOffset = baseOffset + dx;

      if (effectiveOffset < -85) {
        executeRemovalWithAnimation();
      } else if (effectiveOffset < -35) {
        snapTo(-80);
      } else {
        snapTo(0);
      }
    };

    content.addEventListener("touchend", handleTouchEnd, { passive: true });
    content.addEventListener("touchcancel", handleTouchEnd, { passive: true });

    // Desktop mouse dragging support
    content.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      let mouseStartX = e.clientX;
      let mouseCurrentX = mouseStartX;
      let isDraggingMouse = true;
      content.style.transition = "none";

      const onMouseMove = (moveEvt) => {
        if (!isDraggingMouse) return;
        mouseCurrentX = moveEvt.clientX;
        const dx = mouseCurrentX - mouseStartX;
        const baseOffset = isOpen ? -80 : 0;
        let targetX = baseOffset + dx;
        if (targetX > 0) targetX = 0;
        if (targetX < -130) targetX = -130;
        content.style.transform = `translateX(${targetX}px)`;
      };

      const onMouseUp = () => {
        if (!isDraggingMouse) return;
        isDraggingMouse = false;
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);

        const dx = mouseCurrentX - mouseStartX;
        const baseOffset = isOpen ? -80 : 0;
        const effectiveOffset = baseOffset + dx;

        if (effectiveOffset < -85) {
          executeRemovalWithAnimation();
        } else if (effectiveOffset < -35) {
          snapTo(-80);
        } else {
          snapTo(0);
        }
      };

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    });
  };

  // Wire menu dish rows
  const dishesContainer = cart.querySelector("#cart-selected-dishes-list");
  if (dishesContainer) {
    dishesContainer.querySelectorAll(".cart-dish-row-wrapper:not(.cart-addon-row-wrapper)").forEach((wrapper) => {
      const itemId = wrapper.dataset.menuId;
      attachSwipeRow(wrapper, () => {
        const idx = d.menuSelections.findIndex((m) => String(m.menu_item_id) === String(itemId));
        if (idx !== -1) {
          d.menuSelections.splice(idx, 1);
        }
        const dishCard = document.querySelector(`.select-card[data-item-id="${itemId}"]`);
        if (dishCard) {
          dishCard.classList.remove("selected");
          const badge = dishCard.querySelector(".item-check-badge");
          if (badge) badge.innerHTML = icon("plus");
        }
        if (typeof window._updateStep3Counts === "function") {
          window._updateStep3Counts();
        }
        const wizNext = document.getElementById("wiz-next");
        if (wizNext && wizard.step === 3) {
          wizNext.textContent = window.innerWidth < 640
            ? `Next: Add-ons (${d.menuSelections.length})`
            : `Next Step: Event Add-ons (${d.menuSelections.length} Chosen)`;
        }
        renderCart();
      });
    });
  }

  // Wire add-on rows
  const addonsContainer = cart.querySelector("#cart-selected-addons-list");
  if (addonsContainer) {
    addonsContainer.querySelectorAll(".cart-addon-row-wrapper").forEach((wrapper) => {
      const addonIdx = Number(wrapper.dataset.addonIdx);
      attachSwipeRow(wrapper, () => {
        if (addonIdx >= 0 && addonIdx < d.additionalCharges.length) {
          d.additionalCharges.splice(addonIdx, 1);
        }
        if (typeof window._updateStep4Addons === "function") {
          window._updateStep4Addons();
        }
        renderCart();
      });
    });
  }
}

function renderCart() {
  const d = wizard.draft;
  const cart = document.getElementById("wizard-cart");
  if (!cart) return;

  const selectedCount = d.menuSelections.length;

  let selectedDishesHtml = "";
  if (selectedCount > 0) {
    selectedDishesHtml = `
      <div class="cart-section-header" style="display:flex; justify-content:space-between; align-items:center; margin:10px 0 8px;">
        <span class="cart-section-title" style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:0.6px; color:var(--text-muted);">Selected Menu</span>
        <span class="cart-section-badge">${selectedCount} SELECTED</span>
      </div>
      <div class="cart-selected-dishes-container" id="cart-selected-dishes-list">
        ${d.menuSelections.map((m, idx) => `
          <div class="cart-dish-row-wrapper" data-menu-id="${m.menu_item_id}" data-index="${idx}">
            <div class="cart-dish-reveal-action" data-remove-id="${m.menu_item_id}" role="button" aria-label="Remove ${escapeHtml(m.item_name)}">
              <span>REMOVE</span>
            </div>
            <div class="cart-dish-row-content">
              <div class="cart-dish-text-col">
                <div class="cart-dish-name">${escapeHtml(m.item_name)}</div>
                <div class="cart-dish-category">${escapeHtml(m.category || "Menu Item")}</div>
              </div>
              <div class="cart-dish-price-col">
                ${m.price ? `<span class="cart-dish-price">+ ${peso(m.price)}</span>` : `<span class="cart-dish-included">Included</span>`}
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } else {
    selectedDishesHtml = `
      <div class="cart-section-header" style="display:flex; justify-content:space-between; align-items:center; margin:10px 0 8px;">
        <span class="cart-section-title" style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:0.6px; color:var(--text-muted);">Selected Menu</span>
        <span class="cart-section-badge" style="background:var(--border) !important; color:var(--text-muted) !important;">0 SELECTED</span>
      </div>
      <div class="cart-empty-dishes">
        No dishes selected yet. Tap a dish to select. Swipe left to remove.
      </div>
    `;
  }

  let addonsHtml = "";
  if (d.additionalCharges && d.additionalCharges.length > 0) {
    addonsHtml = `
      <div class="cart-section-header" style="display:flex; justify-content:space-between; align-items:center; margin:14px 0 8px;">
        <span class="cart-section-title" style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:0.6px; color:var(--text-muted);">Add-ons &amp; Extras</span>
        <span class="cart-section-badge" style="font-size:11px !important; font-weight:800 !important; padding:2px 8px !important; border-radius:9999px !important; background:var(--gold) !important; color:#000 !important;">${d.additionalCharges.length} ADDED</span>
      </div>
      <div class="cart-selected-dishes-container" id="cart-selected-addons-list">
        ${d.additionalCharges.map((c, idx) => `
          <div class="cart-dish-row-wrapper cart-addon-row-wrapper" data-addon-idx="${idx}">
            <div class="cart-dish-reveal-action" data-remove-addon-idx="${idx}" role="button" aria-label="Remove ${escapeHtml(c.description)}">
              <span>REMOVE</span>
            </div>
            <div class="cart-dish-row-content">
              <div class="cart-dish-text-col">
                <div class="cart-dish-name">${escapeHtml(c.description)}</div>
                <div class="cart-dish-category">EVENT ADD-ON</div>
              </div>
              <div class="cart-dish-price-col">
                <span class="cart-dish-price" style="color:var(--gold); font-weight:700;">${peso(c.amount)}</span>
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  }

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
    
    <div style="border-bottom:1.5px solid var(--border); padding-bottom:10px; margin-bottom:10px;">
      ${selectedDishesHtml}
      ${addonsHtml}
    </div>

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

  wireCartSwipeToRemove(cart);

  cart.querySelector("#cart-quick-next")?.addEventListener("click", () => {
    // Forward to the current step's primary next button so all form inputs are properly harvested into state and validated!
    const stepNextBtn = document.getElementById("wiz-next") || document.getElementById("sticky-next-btn-top");
    if (stepNextBtn) {
      stepNextBtn.click();
      return;
    }
    if (wizard.step < 6) {
      wizard.step++;
      render();
    }
  });
  cart.querySelector("#cancel-order").addEventListener("click", confirmCancelOrder);
}

function stepCard() {
  return document.getElementById("wizard-step-card");
}

function stepBody() {
  return document.getElementById("wizard-step-body");
}

function stepFooter() {
  return document.getElementById("wizard-step-footer");
}

function footer(nextLabel, onNext, backEnabled = true) {
  const footerEl = stepFooter();
  if (footerEl) {
    footerEl.innerHTML = `
      <button class="btn btn-secondary" id="wiz-back" ${backEnabled ? "" : "disabled"}>
        ${icon("arrowLeft")} Back
      </button>
      <button class="btn btn-primary" id="wiz-next">
        ${nextLabel} ${icon("arrowRight")}
      </button>
    `;
    footerEl.querySelector("#wiz-back").addEventListener("click", () => {
      if (wizard.step > 1) { wizard.step--; render(); }
    });
    footerEl.querySelector("#wiz-next").addEventListener("click", onNext);
  } else {
    const card = stepCard();
    if (!card) return;
    const wrap = document.createElement("div");
    wrap.className = "wizard-step-footer";
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
}

async function renderStep() {
  const target = stepBody() || stepCard();
  switch (wizard.step) {
    case 1: return renderStepCustomer(target);
    case 2: return renderStepPackage(target);
    case 3: return renderStepMenu(target);
    case 4: return renderStepAddons(target);
    case 5: return renderStepBilling(target);
    case 6: return renderStepPreview(target);
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

    const renderSearchResults = async (query = "") => {
      const results = await api.searchCustomers(query);
      if (!results || results.length === 0) {
        resultsEl.innerHTML = `<p style="color:var(--text-muted); padding:10px;">No matching customers found.</p>`;
        return;
      }
      resultsEl.innerHTML = results.map((r) => `
        <div class="card card-elevated customer-search-item" style="margin-bottom:8px; cursor:pointer; transition:transform 0.2s; padding:12px 14px;" data-id="${r.id}">
          <b style="color:var(--text); font-size:15px;">${escapeHtml(r.name)}</b><br>
          <span style="color:var(--text-muted); font-size:13px;">${escapeHtml(r.contact || "No contact")} · ${escapeHtml(r.address || "Cebu")}</span>
        </div>
      `).join("");
      
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
    };

    // Populate existing customers immediately so list is visible right away!
    renderSearchResults("");

    let timer = null;
    searchInput?.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        renderSearchResults(searchInput.value);
      }, 200);
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
  card.innerHTML = `<h2 style="margin:0 0 10px;">${icon("package")} Event &amp; Package</h2><p style="color:var(--text-muted);">Fetching packages from Live Database…</p>`;
  try {
    const [pkgs, occs] = await Promise.all([
      api.getPackages(),
      api.getOccasions().catch(() => [])
    ]);
    packagesCache = pkgs;
    if (occs && occs.length > 0) {
      occasionsCache = occs.map((o) => (typeof o === "string" ? o : o.name));
    }
  } catch (err) {
    card.innerHTML = `
      <div style="padding:36px; text-align:center;">
        <div style="font-size:42px; margin-bottom:12px;">🔴</div>
        <h3 style="color:#EF4444; margin:0 0 8px;">Live Central Database Disconnected</h3>
        <p style="color:var(--text-muted); max-width:480px; margin:0 auto 20px; font-size:14px; line-height:1.5;">
          Tablet is configured to <b>strictly fetch data only from the Live Central Database</b>. Ensure your laptop is connected to Wi-Fi and the central server is running.
        </p>
        <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
          <button class="btn btn-outline" id="setup-live-packages" style="font-weight:700; border:1.5px solid var(--border); padding:10px 20px;">⚙️ Setup IP &amp; Credentials</button>
          <button class="btn btn-primary" id="retry-live-packages" style="font-weight:700; padding:10px 20px;">⚡ Retry Connection</button>
        </div>
      </div>
    `;
    card.querySelector("#setup-live-packages")?.addEventListener("click", () => openLiveDbConfigModal());
    card.querySelector("#retry-live-packages")?.addEventListener("click", () => renderStepPackage(card));
    return;
  }

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
      Fill in your event details and choose a buffet package below.
    </p>

    <div class="grid-2">
      <div class="form-group">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <label style="margin:0;">Event Date *</label>
          <button type="button" class="btn btn-ghost" id="btn-open-calendar" style="padding:2px 8px; font-size:12px; height:24px; color:var(--accent); font-weight:700;">
            📅 View Calendar
          </button>
        </div>
        <input type="date" class="form-control" id="e-date" value="${d.event.date}">
        <div id="date-conflict-warning" style="display:none; margin-top:6px; padding:6px 10px; border-radius:6px; font-size:12px; font-weight:600; background:rgba(245,158,11,0.15); color:#D97706; border:1px solid rgba(245,158,11,0.3);"></div>
      </div>
      <div class="form-group">
        <label>Event Start &amp; End Time (Optional)</label>
        <div style="display:flex; gap:8px; align-items:center;">
          <input type="time" class="form-control" id="e-time" value="${d.event.time || ''}" placeholder="Start Time" title="Event Start Time" style="flex:1;">
          <span style="color:var(--text-muted); font-size:12px; font-weight:700;">to</span>
          <input type="time" class="form-control" id="e-end-time" value="${d.event.endTime || ''}" placeholder="End Time (Optional)" title="Event End Time (Optional)" style="flex:1;">
        </div>
        <span style="font-size:11px; color:var(--text-muted); margin-top:3px; display:block;">Leave blank if To Be Followed (TBF).</span>
      </div>
    </div>
    <div class="grid-2">
      <div class="form-group">
        <label>Order Quantity / Sets (Min: 1 Set)</label>
        <input type="number" class="form-control" id="e-pax" min="1" max="2000" value="${d.event.pax || 1}">
        <span style="font-size:11px; color:var(--text-muted); margin-top:3px; display:block;">1 Set is good for 22 persons (4 dishes). Minimum order: 1 set.</span>
      </div>
      <div class="form-group">
        <label>Occasion / Event Type *</label>
        <select class="form-control" id="e-occasion">
          <option value="">Select Event Occasion…</option>
          ${((occasionsCache && occasionsCache.length > 0) ? occasionsCache : OCCASIONS).map((occ) => `<option value="${escapeHtml(occ)}" ${(d.event.occasion || '').toLowerCase() === occ.toLowerCase() ? "selected" : ""}>${escapeHtml(occ)}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="grid-2">
      <div class="form-group">
        <label>Venue Barangay / City (Search)</label>
        <input type="text" class="form-control" id="e-venue-city" placeholder="Search barangay or city (or leave blank if TBF)…" value="${escapeHtml(d.event.venueCity || "")}" autocomplete="off">
        <div id="venue-results" style="margin-top:8px;"></div>
      </div>
      <div class="form-group">
        <label>Venue Street / Landmark / Floor / Bldg</label>
        <input type="text" class="form-control" id="e-venue-street" placeholder="e.g. Grand Ballroom, 4th Floor, Skyline Hotel (or To be followed)" value="${escapeHtml(d.event.venueStreet || "")}">
      </div>
    </div>
    <div class="form-group">
      <label>🎨 Theme &amp; Motif</label>
      <input type="text" class="form-control" id="e-motif" placeholder="e.g. Rose Gold &amp; Ivory, Black &amp; White Elegance, Garden Green…" value="${escapeHtml(d.event.motif || "")}">
      <span style="font-size:11px; color:var(--text-muted); margin-top:3px; display:block;">Type the event's color theme or motif. This will appear on the official receipt.</span>
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
              <span class="kiosk-price-tag">${peso(p.price_per_pax)}<span style="font-size:12px; font-weight:600; color:var(--text-muted); font-family:inherit;"> / set</span></span>
              <span class="kiosk-status-pill">Min 1 Set (4 dishes good for 22 person)</span>
            </div>
          </div>
        </div>
      `;
      }).join("")}
    </div>

    <div class="grid-2" style="margin-top:20px;">
      <div class="form-group">
        <label>Price Per Set (₱)</label>
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
  const endTimeInput = card.querySelector("#e-end-time");
  const paxInput = card.querySelector("#e-pax");
  const occasionSelect = card.querySelector("#e-occasion");
  const venueCityInput = card.querySelector("#e-venue-city");
  const venueStreetInput = card.querySelector("#e-venue-street");
  const venueResults = card.querySelector("#venue-results");

  // Date conflict checker
  const dateWarning = card.querySelector("#date-conflict-warning");
  const checkDateConflict = async (dateVal) => {
    if (!dateVal || !dateWarning) return;
    try {
      const bks = await api.getBookingsByDate(dateVal);
      if (bks && bks.length > 0) {
        dateWarning.style.display = "block";
        dateWarning.innerHTML = `⚠️ <b>Notice:</b> ${bks.length} catering booking(s) already scheduled on this date. You may still proceed with reservation.`;
      } else {
        dateWarning.style.display = "none";
      }
    } catch (_) {
      dateWarning.style.display = "none";
    }
  };
  dateInput?.addEventListener("change", () => checkDateConflict(dateInput.value));
  if (dateInput?.value) checkDateConflict(dateInput.value);

  // Calendar button opens light calendar modal
  card.querySelector("#btn-open-calendar")?.addEventListener("click", () => {
    openLightCalendarModal((pickedDate) => {
      if (dateInput) {
        dateInput.value = pickedDate;
        d.event.date = pickedDate;
        checkDateConflict(pickedDate);
      }
    });
  });

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
    baseInput.value = (price * (pax || 1)).toFixed(2);
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

  async function selectPackage(pkg) {
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
    d.package.minPax = 1;
    d.package.description = pkg.description;

    // Pre-populate menu selections with default package items so Step 3 is auto-checked
    try {
      const items = await api.getPackageItems(pkg.id);
      if (items && items.length > 0) {
        d.menuSelections = items.map((it) => ({
          menu_item_id: it.item_id,
          item_name: it.item_name,
          category: it.category || "Main Course",
          price: 0,
          quantity: 1,
        }));
      }
    } catch (e) {
      console.warn("Could not load default package items:", e);
    }

    const currentPax = Number(paxInput.value || 0);
    if (currentPax < 1) {
      d.event.pax = 1;
      paxInput.value = 1;
    }
    priceInput.value = pkg.price_per_pax;
    syncFromPricePerPax();
  }

  card.querySelectorAll(".select-card").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.closest(".btn-view-pkg-details")) return;
      const pkg = packagesCache.find((p) => String(p.id) === el.dataset.id);
      if (pkg) selectPackage(pkg);
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
    d.event.time = card.querySelector("#e-time").value || "To be followed";
    d.event.endTime = card.querySelector("#e-end-time")?.value || "";
    d.event.pax = Number(paxInput.value || 1);
    d.event.occasion = card.querySelector("#e-occasion").value || "General Event";
    d.event.venueStreet = (venueStreetInput.value || "").trim();
    d.event.venueCity = (venueCityInput.value || "").trim();
    const venueCombined = [d.event.venueStreet, d.event.venueCity].filter(Boolean).join(", ");
    d.event.venue = venueCombined || "To be followed";
    d.event.motif = (card.querySelector("#e-motif")?.value || "").trim() || "Standard";
    d.package.pricePerPax = Number(priceInput.value || 0);
    d.package.baseTotal = Number(baseInput.value || 0);

    if (!d.package.id && !d.package.baseTotal) { toast("Please choose a package or set base total.", "error"); return; }
    if (!d.event.date) { toast("Event date is required.", "error"); return; }
    wizard.step = 3;
    render();
  });

  // Wire sticky top Next button to trigger the bottom #wiz-next (so all validation runs)
  const stickyPkgTopBtn = card.querySelector("#sticky-pkg-next-top");
  if (stickyPkgTopBtn) {
    stickyPkgTopBtn.addEventListener("click", () => {
      const wizNext = document.getElementById("wiz-next");
      if (wizNext) wizNext.click();
    });
  }
}

// ── Step 3: Menu & Add-ons (Mix & Match) ─────────────────────────────

async function renderStepMenu(card) {
  const d = wizard.draft;
  card.innerHTML = `<h2 style="margin:0 0 10px;">${icon("utensils")} Menu Selection</h2><p style="color:var(--text-muted);">Fetching dishes from Live Database…</p>`;
  try {
    menuGroupedCache = await api.getMenuItemsGrouped();
  } catch (err) {
    card.innerHTML = `
      <div style="padding:36px; text-align:center;">
        <div style="font-size:42px; margin-bottom:12px;">🔴</div>
        <h3 style="color:#EF4444; margin:0 0 8px;">Live Central Database Disconnected</h3>
        <p style="color:var(--text-muted); max-width:460px; margin:0 auto 20px; font-size:14px; line-height:1.5;">
          Tablet is configured to <b>strictly fetch data only from the Live Central Database</b>. Local offline dishes are disabled. Ensure Wi-Fi ARISE! is active and server is running at 192.168.1.10.
        </p>
        <button class="btn btn-primary" id="retry-live-menu">⚡ Retry Live Connection</button>
      </div>
    `;
    card.querySelector("#retry-live-menu")?.addEventListener("click", () => renderStepMenu(card));
    return;
  }

  const selectedIds = new Set(d.menuSelections.map((m) => m.menu_item_id));
  const categories = Object.keys(menuGroupedCache);
  const totalAll = Object.values(menuGroupedCache).reduce((sum, arr) => sum + (arr ? arr.length : 0), 0);

  card.innerHTML = `
    <div class="kiosk-menu-header-row" style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap;">
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

    <!-- Live Search Bar & Category Navigation (STICKY ON SCROLL) -->
    <div class="kiosk-menu-sticky-filter-bar" id="kiosk-menu-sticky-filter-bar">
      <div style="display:flex; gap:10px; align-items:center; margin-bottom:10px; flex-wrap:wrap;">
        <div style="position:relative; flex:1; min-width:220px;">
          <input type="text" class="form-control" id="menu-dish-search" placeholder="Search dish name, ingredients or category…" style="padding-left:36px; padding-right:32px; height:40px; font-size:13.5px; border-radius:20px;">
          <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--text-muted); pointer-events:none;">${icon("search")}</span>
          <button type="button" id="menu-dish-search-clear" style="display:none; position:absolute; right:10px; top:50%; transform:translateY(-50%); background:transparent; border:none; color:var(--text-muted); cursor:pointer; font-size:14px; padding:2px 6px;">✕</button>
        </div>
        <div id="search-match-count" style="display:none; font-size:12.5px; color:var(--gold); font-weight:700;"></div>
      </div>

      <!-- Quick Category Filter Bar with Dynamic Dish Counts -->
      <div class="kiosk-cat-bar" id="kiosk-cat-bar">
        <button type="button" class="kiosk-cat-pill active" data-cat="all">
          All Dishes (${totalAll})
          <span class="pill pill-partial" style="padding:2px 7px; font-size:11px;" id="all-selected-count">${totalAll}</span>
        </button>
        ${categories.map((cat) => {
          const catTotal = (menuGroupedCache[cat] || []).length;
          return `
            <button type="button" class="kiosk-cat-pill" data-cat="${escapeHtml(cat)}">
              ${escapeHtml(cat)} (${catTotal})
              <span class="pill pill-partial" style="padding:2px 7px; font-size:11px;" data-pill-count="${escapeHtml(cat)}" data-cat-total="${catTotal}">${catTotal}</span>
            </button>
          `;
        }).join("")}
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
      const catTotal = (menuGroupedCache[cat] || []).length;
      const cnt = counts[cat] || 0;
      el.textContent = cnt > 0 ? `${cnt} / ${catTotal} Selected` : `0 / ${catTotal} Selected`;
      el.className = `pill ${cnt > 0 ? "pill-paid" : "pill-partial"}`;
    });
    card.querySelectorAll("[data-pill-count]").forEach((el) => {
      const cat = el.dataset.pillCount;
      const catTotal = Number(el.dataset.catTotal) || (menuGroupedCache[cat] || []).length;
      const cnt = counts[cat] || 0;
      if (cnt > 0) {
        el.textContent = `${cnt} / ${catTotal}`;
        el.className = "pill pill-paid";
      } else {
        el.textContent = catTotal;
        el.className = "pill pill-partial";
      }
    });
    const allPill = card.querySelector("#all-selected-count");
    if (allPill) {
      const selTotal = d.menuSelections.length;
      if (selTotal > 0) {
        allPill.textContent = `${selTotal} / ${totalAll}`;
        allPill.className = "pill pill-paid";
      } else {
        allPill.textContent = totalAll;
        allPill.className = "pill pill-partial";
      }
    }
  }
  window._updateStep3Counts = updateCounts;

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

  footer(
    window.innerWidth < 640
      ? `Next: Add-ons (${d.menuSelections.length})`
      : `Next Step: Event Add-ons (${d.menuSelections.length} Chosen)`,
    () => { wizard.step = 4; render(); }
  );
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

  function updateUpsellButtons() {
    card.querySelectorAll("[data-upsell]").forEach((btn) => {
      const idx = Number(btn.dataset.upsell);
      const u = UPSELLS[idx];
      if (!u) return;
      const isSelected = d.additionalCharges.some((c) => c.description === u.name);
      if (isSelected) {
        btn.className = "btn btn-danger-outline";
        btn.style.padding = "8px 16px";
        btn.style.fontWeight = "700";
        btn.innerHTML = `${icon("trash")} Remove`;
      } else {
        btn.className = "btn btn-secondary";
        btn.style.padding = "8px 16px";
        btn.style.fontWeight = "";
        btn.innerHTML = `${icon("plus")} Add`;
      }
    });
  }

  function renderChargeList() {
    const list = card.querySelector("#charge-list");
    list.innerHTML = d.additionalCharges.map((c, i) => `
      <div class="card card-elevated" style="display:flex; justify-content:space-between; align-items:center; padding:12px 18px; margin-bottom:8px;">
        <div>
          <span style="font-weight:700; font-size:14px; color:var(--text);">${escapeHtml(c.description)}</span>
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; margin-top:2px;">Event Add-on / Charge</div>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          <span style="font-weight:800; color:var(--gold); font-size:14.5px;">${peso(c.amount)}</span>
          <button class="btn btn-ghost" data-remove="${i}" style="color:var(--danger); border-color:var(--danger); font-size:12px; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" title="Remove this add-on">
            ${icon("trash")} Remove
          </button>
        </div>
      </div>
    `).join("") || `<p style="color:var(--text-muted); padding:10px;">No additional charges applied. Tap "Add" above or enter a custom charge.</p>`;
    
    list.querySelectorAll("[data-remove]").forEach((el) => {
      el.addEventListener("click", () => {
        d.additionalCharges.splice(Number(el.dataset.remove), 1);
        renderChargeList();
        updateUpsellButtons();
        renderCart();
      });
    });
  }
  renderChargeList();
  updateUpsellButtons();

  window._updateStep4Addons = () => {
    renderChargeList();
    updateUpsellButtons();
  };

  card.querySelectorAll("[data-upsell]").forEach((el) => {
    el.addEventListener("click", () => {
      const u = UPSELLS[Number(el.dataset.upsell)];
      const existIdx = d.additionalCharges.findIndex((c) => c.description === u.name);
      if (existIdx !== -1) {
        d.additionalCharges.splice(existIdx, 1);
        toast(`Removed ${u.name}`, "info");
      } else {
        d.additionalCharges.push({ description: u.name, amount: u.price });
        toast(`Added ${u.name}`, "success");
      }
      renderChargeList();
      updateUpsellButtons();
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
    updateUpsellButtons();
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

  const footerEl = stepFooter();
  const wrap = footerEl || document.createElement("div");
  if (!footerEl) {
    wrap.style.cssText = "display:flex; justify-content:space-between; align-items:center; margin-top:28px; border-top:1.5px solid var(--border); padding-top:20px;";
    card.appendChild(wrap);
  }
  wrap.className = "wizard-step-footer";
  wrap.innerHTML = `
    <button class="btn btn-secondary" id="wiz-back">
      ${icon("arrowLeft")} Back
    </button>
    <button class="btn btn-primary btn-lg" id="confirm-order">
      ${icon("check")} Confirm &amp; Save Booking
    </button>
  `;
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
          event_end_time: d.event.endTime || null,
          venue: d.event.venue,
          occasion: d.event.occasion,
          pax: d.event.pax,
          motif: d.event.motif || "Standard",
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
        if (lastCreatedOrder && lastCreatedOrder._synced) {
          toast("Booking successfully created and synced to the central server!", "success");
        } else {
          toast("Booking saved on this tablet - will sync automatically once connected to the central server.", "warning");
        }
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
    <div style="text-align:center; padding:10px 0 20px;">
      <div id="receipt-success-lottie" style="width:130px; height:130px; margin:0 auto 12px; display:flex; align-items:center; justify-content:center;"></div>
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
  const footerEl = stepFooter();
  if (footerEl) footerEl.innerHTML = "";

  card.querySelector("#print-receipt").addEventListener("click", () => {
    api.downloadReceipt(o.booking_id);
  });
  card.querySelector("#done-btn").addEventListener("click", () => {
    const doneBtn = card.querySelector("#done-btn");
    doneBtn.disabled = true;
    doneBtn.innerHTML = `${icon("refresh")} Returning…`;
    wizard.reset();
    document.body.classList.remove("wizard-mode");
    window.dispatchEvent(new CustomEvent("kiosk:home", {
      detail: { transition: true, message: "Thank you for booking! Resetting kiosk for the next guest…" }
    }));
  });

  const successLottie = card.querySelector("#receipt-success-lottie");
  if (successLottie) {
    mountLottie(successLottie, "booking-success", { loop: false, autoplay: true });
  }
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

export function openLightCalendarModal(onSelectDate) {
  const modalId = "light-calendar-modal";
  const now = new Date();
  let viewYear = now.getFullYear();
  let viewMonth = now.getMonth(); // 0-indexed

  openModal({
    id: modalId,
    title: `📅 Event Scheduling Calendar`,
    bodyHtml: `<div id="calendar-modal-content"></div>`,
    footerHtml: `<button class="btn btn-secondary" data-close>Close</button>`,
  });

  const modal = document.getElementById(modalId);
  const container = modal.querySelector("#calendar-modal-content");

  async function renderMonth() {
    container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading schedule…</div>`;
    const bookings = await api.getMonthBookings(viewYear, viewMonth + 1).catch(() => []);
    const dateCounts = {};
    for (const b of (bookings || [])) {
      if (b.bk_event_date) {
        dateCounts[b.bk_event_date] = (dateCounts[b.bk_event_date] || 0) + 1;
      }
    }

    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    let daysHtml = "";
    for (let i = 0; i < firstDay; i++) {
      daysHtml += `<div style="padding:8px;"></div>`;
    }
    for (let day = 1; day <= daysInMonth; day++) {
      const pad = (n) => String(n).padStart(2, "0");
      const dStr = `${viewYear}-${pad(viewMonth + 1)}-${pad(day)}`;
      const cnt = dateCounts[dStr] || 0;
      daysHtml += `
        <div class="cal-day-cell" data-date="${dStr}" style="padding:8px 4px; border:1.5px solid ${cnt > 0 ? "rgba(245,158,11,0.5)" : "var(--border)"}; border-radius:8px; text-align:center; cursor:pointer; background:${cnt > 0 ? "rgba(245,158,11,0.1)" : "transparent"}; transition:all 0.15s; user-select:none;">
          <div style="font-weight:800; font-size:14px; color:${cnt > 0 ? "#D97706" : "var(--text)"};">${day}</div>
          ${cnt > 0 ? `<span style="font-size:9.5px; font-weight:800; padding:1px 4px; border-radius:8px; background:#D97706; color:#fff; display:inline-block; margin-top:2px;">${cnt} event${cnt > 1 ? "s" : ""}</span>` : `<span style="font-size:9.5px; color:var(--text-muted); opacity:0.6;">Available</span>`}
        </div>
      `;
    }

    container.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <button type="button" class="btn btn-ghost" id="cal-prev-month" style="font-size:14px; padding:6px 12px; font-weight:700;">◀ Prev</button>
        <h3 style="margin:0; font-size:16px; font-weight:800;">${monthNames[viewMonth]} ${viewYear}</h3>
        <button type="button" class="btn btn-ghost" id="cal-next-month" style="font-size:14px; padding:6px 12px; font-weight:700;">Next ▶</button>
      </div>
      <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px; font-weight:700; font-size:11px; text-align:center; color:var(--text-muted); margin-bottom:6px;">
        <div>Sun</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px;" id="cal-grid-days">
        ${daysHtml}
      </div>
      <p style="margin:12px 0 0; font-size:12px; color:var(--text-muted); text-align:center;">
        Tap any date to select it for your catering reservation.
      </p>
    `;

    container.querySelector("#cal-prev-month")?.addEventListener("click", () => {
      if (viewMonth === 0) { viewMonth = 11; viewYear--; } else { viewMonth--; }
      renderMonth();
    });
    container.querySelector("#cal-next-month")?.addEventListener("click", () => {
      if (viewMonth === 11) { viewMonth = 0; viewYear++; } else { viewMonth++; }
      renderMonth();
    });

    container.querySelectorAll(".cal-day-cell[data-date]").forEach((cell) => {
      cell.addEventListener("click", () => {
        const picked = cell.dataset.date;
        if (onSelectDate) onSelectDate(picked);
        closeModal(modalId);
        toast(`Selected date: ${picked}`, "success");
      });
      cell.addEventListener("mouseenter", () => { cell.style.borderColor = "var(--accent)"; });
      cell.addEventListener("mouseleave", () => {
        const dStr = cell.dataset.date;
        const cnt = dateCounts[dStr] || 0;
        cell.style.borderColor = cnt > 0 ? "rgba(245,158,11,0.5)" : "var(--border)";
      });
    });
  }

  renderMonth();
}
