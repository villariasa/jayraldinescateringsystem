// Modern interactive UI helpers (Modals, Toasts, Status Pills) with SVGs and animations.
import { icon } from "./icons.js";
import { mountLottie } from "./lottie-helper.js";

export function toast(message, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`.trim();
  
  let animName = "toast-info";
  let iconSvg = icon("info");
  if (kind === "success") {
    animName = "toast-success";
    iconSvg = icon("checkCircle");
  } else if (kind === "danger" || kind === "error") {
    animName = "toast-error";
    iconSvg = icon("alertTriangle");
  }

  el.innerHTML = `
    <span class="toast-icon">
      <span class="lottie-icon-container"></span>
      <span class="toast-fallback-icon" style="display:none;">${iconSvg}</span>
    </span>
    <span class="toast-text">${escapeHtml(message)}</span>
  `;
  document.body.appendChild(el);

  const lottieWrap = el.querySelector(".lottie-icon-container");
  if (lottieWrap) {
    mountLottie(lottieWrap, animName, { loop: false, autoplay: true }).then((a) => {
      if (!a) {
        const fb = el.querySelector(".toast-fallback-icon");
        if (fb) fb.style.display = "inline-flex";
      }
    }).catch(() => {
      const fb = el.querySelector(".toast-fallback-icon");
      if (fb) fb.style.display = "inline-flex";
    });
  }

  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(12px)";
    el.style.transition = "all 0.25s ease-in";
    setTimeout(() => el.remove(), 250);
  }, 3200);
}

export function statusPill(status) {
  const isPaid = status === "Paid";
  const isPartial = status === "Partial";
  const cls = isPaid ? "pill-paid" : isPartial ? "pill-partial" : "pill-unpaid";
  const iconSvg = isPaid ? icon("check") : isPartial ? icon("clock") : icon("alertTriangle");
  return `<span class="pill ${cls}">${iconSvg} ${escapeHtml(status)}</span>`;
}

const overlayRoot = () => document.getElementById("overlay-root");

/**
 * Renders a full Slide-Over Drawer panel with smooth spring slide-in and backdrop blur.
 */
export function openModal({ id, title, bodyHtml, footerHtml, large = false, allowSwipeUpFullscreen = (id === "owner-settings-modal"), onClose }) {
  // Remove any stale instance immediately
  const existing = document.getElementById(id);
  if (existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.className = "overlay drawer-overlay";
  overlay.id = id;
  overlay.innerHTML = `
    <div class="modal drawer-panel ${large ? "modal-lg drawer-lg" : ""}">
      <div class="drawer-grab-bar-wrap" id="${id}-grab-tip" title="Drag down on this tip to close">
        <div class="drawer-grab-bar"></div>
      </div>
      <div class="modal-header drawer-header">
        <h2>${title}</h2>
        <div style="display:flex; align-items:center; gap:8px;">
          ${allowSwipeUpFullscreen ? `<button class="icon-btn" id="${id}-fullscreen-toggle" title="Toggle Fullscreen">${icon("fullscreen")}</button>` : ""}
          <button class="icon-btn icon-btn-danger" data-close title="Close">${icon("close")}</button>
        </div>
      </div>
      <div class="modal-body drawer-body" id="${id}-body"></div>
      ${footerHtml ? `<div class="modal-footer drawer-footer">${footerHtml}</div>` : ""}
    </div>
  `;
  overlayRoot().appendChild(overlay);

  // Smoothly trigger scrolling up from below the screen (no abrupt pop)
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      overlay.classList.add("drawer-open");
    });
  });

  const handleClose = () => {
    closeModal(id);
    if (onClose) onClose();
  };

  overlay.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", handleClose);
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) handleClose();
  });

  const escHandler = (e) => {
    if (e.key === "Escape") {
      handleClose();
      window.removeEventListener("keydown", escHandler);
    }
  };
  window.addEventListener("keydown", escHandler);

  // ── Drag & Swipe STRICTLY on the Top Tip Handle Bar ──────────────────────
  const panel = overlay.querySelector(".modal, .drawer-panel");
  const grabTip = overlay.querySelector(".drawer-grab-bar-wrap");
  const bodyEl = overlay.querySelector(`#${id}-body`);

  if (allowSwipeUpFullscreen) {
    const fsToggleBtn = overlay.querySelector(`#${id}-fullscreen-toggle`);
    if (fsToggleBtn) {
      fsToggleBtn.addEventListener("click", () => {
        panel.classList.toggle("drawer-fullscreen");
      });
    }
  }

  let startY = 0;
  let currentY = 0;
  let isDraggingTip = false;

  const onTipTouchStart = (e) => {
    startY = e.touches[0].clientY;
    currentY = startY;
    isDraggingTip = true;
    panel.style.transition = "none";
  };

  const onTipTouchMove = (e) => {
    if (!isDraggingTip) return;
    currentY = e.touches[0].clientY;
    const deltaY = currentY - startY;

    if (deltaY > 0) {
      // Dragging downward on tip
      if (e.cancelable) e.preventDefault();
      if (!panel.classList.contains("drawer-fullscreen")) {
        panel.style.transform = `translateY(${deltaY}px)`;
        overlay.style.opacity = String(Math.max(0.25, 1 - deltaY / 380));
      }
    } else if (deltaY < 0 && allowSwipeUpFullscreen) {
      // Dragging upward on tip in settings
      if (e.cancelable) e.preventDefault();
    }
  };

  const onTipTouchEnd = () => {
    if (!isDraggingTip) return;
    isDraggingTip = false;
    const deltaY = currentY - startY;
    panel.style.transition = "transform 0.32s cubic-bezier(0.2, 0.9, 0.3, 1), opacity 0.32s ease";

    if (deltaY < -35 && allowSwipeUpFullscreen) {
      // Swipe UP on tip: Expand to Fullscreen
      panel.classList.add("drawer-fullscreen");
      panel.style.transform = "";
      overlay.style.opacity = "1";
    } else if (deltaY > 60 && panel.classList.contains("drawer-fullscreen")) {
      // Drag DOWN on tip from Fullscreen: Shrink to normal drawer
      panel.classList.remove("drawer-fullscreen");
      panel.style.transform = "";
      overlay.style.opacity = "1";
    } else if (deltaY > 75 && !panel.classList.contains("drawer-fullscreen")) {
      // Drag DOWN on tip: Close slider by scrolling down
      handleClose();
    } else {
      panel.style.transform = "";
      overlay.style.opacity = "1";
    }
  };

  if (grabTip) {
    grabTip.addEventListener("touchstart", onTipTouchStart, { passive: false });
    grabTip.addEventListener("touchmove", onTipTouchMove, { passive: false });
    grabTip.addEventListener("touchend", onTipTouchEnd);
  }

  if (typeof bodyHtml === "function") {
    bodyHtml(bodyEl);
  } else {
    bodyEl.innerHTML = bodyHtml;
  }
  return overlay;
}

export function closeModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.remove("drawer-open");
    el.style.pointerEvents = "none";
    el.style.opacity = "0";
    el.style.transition = "opacity 0.32s ease";
    const panel = el.querySelector(".modal, .drawer-panel");
    if (panel) {
      panel.style.transform = "translateY(100%)";
      panel.style.transition = "transform 0.34s cubic-bezier(0.32, 0, 0.67, 0)";
    }
    setTimeout(() => {
      if (el && el.parentNode) el.remove();
    }, 350);
  }
}

export function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}
