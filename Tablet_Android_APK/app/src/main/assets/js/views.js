// Modern interactive UI helpers (Modals, Toasts, Status Pills) with SVGs and animations.
import { icon } from "./icons.js";
import { mountLottie } from "./lottie-helper.js";

function getToastContainer() {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

export function toast(message, kind = "", duration = 0) {
  const container = getToastContainer();

  // If this is an error or danger toast, dismiss any in-flight info / connecting toasts
  if (kind === "danger" || kind === "error") {
    container.querySelectorAll(".toast:not(.danger):not(.error)").forEach((prior) => {
      prior.style.opacity = "0";
      prior.style.transform = "translateY(-8px)";
      setTimeout(() => prior.remove(), 180);
    });
  }

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
    <span class="toast-text" style="flex:1; word-break:break-word;">${escapeHtml(message)}</span>
    <button class="toast-close-btn" type="button" aria-label="Close" title="Dismiss">&times;</button>
  `;

  const closeBtn = el.querySelector(".toast-close-btn");
  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      el.style.opacity = "0";
      el.style.transform = "translateY(-8px)";
      el.style.transition = "all 0.2s ease-in";
      setTimeout(() => el.remove(), 200);
    });
  }

  container.appendChild(el);

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

  const timeoutMs = duration || ((kind === "danger" || kind === "error") ? 7500 : 3500);

  setTimeout(() => {
    if (el.parentNode) {
      el.style.opacity = "0";
      el.style.transform = "translateY(-8px)";
      el.style.transition = "all 0.25s ease-in";
      setTimeout(() => el.remove(), 250);
    }
  }, timeoutMs);
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
    const updateFsIcon = () => {
      if (!fsToggleBtn) return;
      const isFs = panel.classList.contains("drawer-fullscreen");
      fsToggleBtn.innerHTML = isFs ? icon("minimize") : icon("fullscreen");
      fsToggleBtn.title = isFs ? "Minimize Window (Unstretch)" : "Maximize Window (Stretch Fullscreen)";
    };

    if (fsToggleBtn) {
      fsToggleBtn.addEventListener("click", () => {
        panel.style.transition = ""; // Ensure CSS stretch/unstretch transition rules take effect
        panel.classList.toggle("drawer-fullscreen");
        updateFsIcon();
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

    // Reset inline transition so CSS stylesheet stretch animation executes cleanly
    panel.style.transition = "";

    if (deltaY < -35 && allowSwipeUpFullscreen) {
      // Swipe UP on tip: Expand to Fullscreen
      panel.classList.add("drawer-fullscreen");
      panel.style.transform = "";
      overlay.style.opacity = "1";
      const fsToggleBtn = overlay.querySelector(`#${id}-fullscreen-toggle`);
      if (fsToggleBtn) {
        fsToggleBtn.innerHTML = icon("minimize");
        fsToggleBtn.title = "Minimize Window (Unstretch)";
      }
    } else if (deltaY > 60 && panel.classList.contains("drawer-fullscreen")) {
      // Drag DOWN on tip from Fullscreen: Shrink to normal drawer
      panel.classList.remove("drawer-fullscreen");
      panel.style.transform = "";
      overlay.style.opacity = "1";
      const fsToggleBtn = overlay.querySelector(`#${id}-fullscreen-toggle`);
      if (fsToggleBtn) {
        fsToggleBtn.innerHTML = icon("fullscreen");
        fsToggleBtn.title = "Maximize Window (Stretch Fullscreen)";
      }
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

/**
 * Slide-to-confirm modal dialog replacing native browser confirm().
 * Resolves Promise<boolean> (true on confirmed slide, false on cancel/dismiss).
 */
export function confirmWithSlider({
  title = "Confirm Action",
  message = "Are you sure you want to proceed?",
  submessage = "",
  sliderLabel = "Slide to delete ➔",
}) {
  return new Promise((resolve) => {
    const modalId = "slide-confirm-modal-" + Math.floor(Math.random() * 1000000);
    let isResolved = false;

    const cleanupAndResolve = (result) => {
      if (isResolved) return;
      isResolved = true;
      closeModal(modalId);
      resolve(result);
    };

    const bodyHtml = `
      <div class="slide-confirm-box">
        <div style="display:flex; align-items:flex-start; gap:14px; margin-bottom:8px;">
          <div style="width:44px; height:44px; border-radius:12px; background:rgba(220, 38, 38, 0.12); color:#EF4444; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
            ${icon("alertTriangle")}
          </div>
          <div style="flex:1;">
            <div style="font-size:15px; font-weight:700; color:var(--text, #F8FAFC); line-height:1.4;">${escapeHtml(message)}</div>
            ${submessage ? `<div style="font-size:13px; color:var(--text-muted, #94A3B8); margin-top:6px; line-height:1.4;">${escapeHtml(submessage)}</div>` : ""}
          </div>
        </div>

        <div class="slide-confirm-track" id="${modalId}-track">
          <div class="slide-confirm-fill" id="${modalId}-fill"></div>
          <span class="slide-confirm-text" id="${modalId}-text">${escapeHtml(sliderLabel)}</span>
          <div class="slide-confirm-thumb" id="${modalId}-thumb">
            ${icon("arrowRight")}
          </div>
        </div>

        <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:4px;">
          <button type="button" class="btn btn-ghost" id="${modalId}-cancel-btn" style="padding:8px 16px;">Cancel</button>
        </div>
      </div>
    `;

    openModal({
      id: modalId,
      title: title,
      bodyHtml,
      large: false,
      onClose: () => cleanupAndResolve(false),
    });

    setTimeout(() => {
      const modalEl = document.getElementById(modalId);
      if (!modalEl) return;
      const cancelBtn = modalEl.querySelector(`#${modalId}-cancel-btn`);
      if (cancelBtn) {
        cancelBtn.addEventListener("click", () => cleanupAndResolve(false));
      }

      const track = modalEl.querySelector(`#${modalId}-track`);
      const fill = modalEl.querySelector(`#${modalId}-fill`);
      const thumb = modalEl.querySelector(`#${modalId}-thumb`);
      const text = modalEl.querySelector(`#${modalId}-text`);
      if (!track || !thumb) return;

      let isDragging = false;
      let startX = 0;
      let currentX = 0;

      const getMaxSlide = () => Math.max(10, track.clientWidth - thumb.clientWidth - 8);

      const setPos = (x, animate = false) => {
        const trans = animate ? "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)" : "none";
        thumb.style.transition = trans;
        thumb.style.transform = `translateX(${x}px)`;
        if (fill) {
          fill.style.transition = trans;
          fill.style.width = `${x + thumb.clientWidth / 2 + 4}px`;
        }
        if (text) {
          const max = getMaxSlide();
          const progress = max > 0 ? x / max : 0;
          text.style.opacity = String(Math.max(0, 1 - progress * 1.5));
        }
      };

      const onStart = (clientX) => {
        isDragging = true;
        startX = clientX;
        currentX = 0;
        setPos(0, false);
      };

      const onMove = (clientX) => {
        if (!isDragging) return;
        const max = getMaxSlide();
        const delta = Math.max(0, Math.min(max, clientX - startX));
        currentX = delta;
        setPos(delta, false);
      };

      const onEnd = () => {
        if (!isDragging) return;
        isDragging = false;
        const max = getMaxSlide();
        if (max > 0 && currentX >= max * 0.75) {
          setPos(max, true);
          if (thumb) thumb.innerHTML = icon("check");
          if (text) {
            text.textContent = "Confirmed!";
            text.style.opacity = "1";
          }
          setTimeout(() => cleanupAndResolve(true), 250);
        } else {
          setPos(0, true);
        }
      };

      thumb.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        e.stopPropagation();
        try { thumb.setPointerCapture?.(e.pointerId); } catch (_) {}
        onStart(e.clientX);
      });

      window.addEventListener("pointermove", (e) => {
        if (isDragging) onMove(e.clientX);
      });

      window.addEventListener("pointerup", (e) => {
        if (isDragging) {
          try { thumb.releasePointerCapture?.(e.pointerId); } catch (_) {}
          onEnd();
        }
      });

      window.addEventListener("pointercancel", () => {
        if (isDragging) onEnd();
      });
    }, 60);
  });
}
