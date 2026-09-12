/**
 * keyboard-scroll.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Automatically scrolls focused inputs/textareas/selects into view whenever
 * the software keyboard opens on tablet or mobile. Works for both:
 *   • Text inputs (keyboard pushes view up, input hidden underneath)
 *   • Dropdowns / <select> (focus fires before the picker sheet appears)
 *
 * Strategy:
 *   1. On any `focusin` on an input/textarea/select, record the target element.
 *   2. Listen to visualViewport `resize` (fires when keyboard opens/closes).
 *      The viewport height shrinks by exactly the keyboard height.
 *   3. Compute how much of the focused element is below the visible viewport
 *      and scroll the page by that delta + a comfortable padding gap.
 *   4. Also run once on `focusin` (with a short delay) for fast keyboards
 *      that resize before the event fires.
 *
 * Fallback: browsers without `window.visualViewport` use `scrollIntoView`.
 * ─────────────────────────────────────────────────────────────────────────────
 */

const SCROLL_PADDING = 24;   // px gap to keep above keyboard
const FOCUS_DELAY_MS = 120;  // ms to wait after focusin before measuring

let focusedEl = null;
let scrollTimer = null;

/**
 * Scroll the page so that `el` is fully visible above the software keyboard.
 * Uses visualViewport for precise keyboard height; falls back to scrollIntoView.
 */
function ensureVisible(el) {
  if (!el) return;

  // ── Modern path: visualViewport ──────────────────────────────────────────
  if (window.visualViewport) {
    const vv = window.visualViewport;
    const rect = el.getBoundingClientRect();

    // Bottom of the focused element in viewport-relative coordinates
    const elBottom = rect.bottom;

    // The visible area bottom edge (keyboard cuts into this)
    const visibleBottom = vv.height;

    // How many px is the element hidden below the keyboard?
    const overflow = elBottom + SCROLL_PADDING - visibleBottom;

    if (overflow > 0) {
      // Shift the scroll position down by the overflow amount.
      window.scrollBy({
        top: overflow,
        behavior: "smooth",
      });
    }
    return;
  }

  // ── Fallback: scrollIntoView ─────────────────────────────────────────────
  el.scrollIntoView({ behavior: "smooth", block: "center" });
}

/**
 * Debounced scroll trigger — clears any pending timer and schedules a fresh one.
 */
function scheduleScroll(el, delay) {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(function() { ensureVisible(el); }, delay || 0);
}

// ── Event: focusin ───────────────────────────────────────────────────────────
document.addEventListener(
  "focusin",
  function(e) {
    var el = e.target;
    if (
      el.tagName === "INPUT" ||
      el.tagName === "TEXTAREA" ||
      el.tagName === "SELECT"
    ) {
      focusedEl = el;
      scheduleScroll(el, FOCUS_DELAY_MS);
    }
  },
  { passive: true }
);

// ── Event: focusout ──────────────────────────────────────────────────────────
document.addEventListener(
  "focusout",
  function() {
    setTimeout(function() {
      var active = document.activeElement;
      if (!active || (
        active.tagName !== "INPUT" &&
        active.tagName !== "TEXTAREA" &&
        active.tagName !== "SELECT"
      )) {
        focusedEl = null;
      }
    }, 200);
  },
  { passive: true }
);

// ── visualViewport resize ────────────────────────────────────────────────────
if (window.visualViewport) {
  window.visualViewport.addEventListener(
    "resize",
    function() {
      if (focusedEl) {
        scheduleScroll(focusedEl, 0);
      }
    },
    { passive: true }
  );

  window.visualViewport.addEventListener(
    "scroll",
    function() {
      if (focusedEl) {
        scheduleScroll(focusedEl, 0);
      }
    },
    { passive: true }
  );
}
