import { icon } from "./icons.js";

export const DEFAULT_HERO_IMAGES = [
  "images/hero-buffet-1.jpg",
  "images/hero-buffet-2.jpg",
  "images/hero-buffet-3.jpg",
];

const STORAGE_KEY = "jc_landing_images";
const INTERVAL_KEY = "jc_slider_interval";
const DEFAULT_INTERVAL = 5000;

export function getLandingImages() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed.slice(0, 3);
      }
    }
  } catch (_) {}
  return [...DEFAULT_HERO_IMAGES];
}

export function saveLandingImages(images) {
  const sanitized = (images || []).filter(Boolean).slice(0, 3);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized.length ? sanitized : DEFAULT_HERO_IMAGES));
  window.dispatchEvent(new CustomEvent("kiosk:landing-images-changed"));
}

export function resetLandingImages() {
  localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new CustomEvent("kiosk:landing-images-changed"));
  return [...DEFAULT_HERO_IMAGES];
}

export function getSliderInterval() {
  const v = parseInt(localStorage.getItem(INTERVAL_KEY), 10);
  return (v && v >= 2000 && v <= 20000) ? v : DEFAULT_INTERVAL;
}

export function setSliderInterval(ms) {
  localStorage.setItem(INTERVAL_KEY, String(ms));
  window.dispatchEvent(new CustomEvent("kiosk:landing-images-changed"));
}

/**
 * Mounts the hero showcase or multi-image interactive auto-swipe slider into a target container.
 */
export function mountLandingSlider(container) {
  if (!container) return;

  const images = getLandingImages();
  const intervalMs = getSliderInterval();

  // If single image: clean hero display card
  if (images.length === 1) {
    container.innerHTML = `
      <div class="kiosk-hero-slider single-image">
        <div class="kiosk-slide-single">
          <img src="${images[0]}" alt="Jayraldine's Catering Feast" class="kiosk-slide-img" width="1080" height="724" decoding="async" loading="eager">
        </div>
      </div>
    `;
    return;
  }

  // Multiple images (2 or 3): Interactive carousel slider
  let currentIndex = 0;
  let timer = null;
  let isInteracting = false;

  container.innerHTML = `
    <div class="kiosk-hero-slider" id="kiosk-slider-root" tabindex="0" role="region" aria-label="Catering showcase gallery">
      <div class="kiosk-slider-track" id="kiosk-slider-track">
        ${images.map((src, i) => `
          <div class="kiosk-slide ${i === 0 ? "active" : ""}" data-index="${i}">
            <img src="${src}" alt="Catering Highlight ${i + 1}" class="kiosk-slide-img" width="1080" height="724" decoding="async" loading="${i === 0 ? "eager" : "lazy"}">
          </div>
        `).join("")}
      </div>

      <!-- Pagination Dots -->
      <div class="kiosk-slider-dots" id="slider-dots">
        ${images.map((_, i) => `
          <button class="kiosk-slider-dot ${i === 0 ? "active" : ""}" data-dot="${i}" aria-label="Go to slide ${i + 1}"></button>
        `).join("")}
      </div>
    </div>
  `;

  const track = container.querySelector("#kiosk-slider-track");
  const dots = container.querySelectorAll(".kiosk-slider-dot");
  const root = container.querySelector("#kiosk-slider-root");

  function updateSlide(newIndex, manual = false) {
    if (newIndex < 0) {
      currentIndex = images.length - 1;
    } else if (newIndex >= images.length) {
      currentIndex = 0;
    } else {
      currentIndex = newIndex;
    }

    if (track) {
      track.style.transform = `translateX(-${currentIndex * 100}%)`;
    }

    dots.forEach((dot, idx) => {
      dot.classList.toggle("active", idx === currentIndex);
    });

    if (manual) {
      restartTimer();
    }
  }

  function startTimer() {
    stopTimer();
    timer = setInterval(() => {
      if (!isInteracting) {
        updateSlide(currentIndex + 1);
      }
    }, intervalMs);
  }

  function stopTimer() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function restartTimer() {
    stopTimer();
    startTimer();
  }

  dots.forEach((dot) => {
    dot.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = parseInt(dot.dataset.dot, 10);
      updateSlide(idx, true);
    });
  });

  // Touch Swipe Gesture Support
  let startX = 0;
  let currentX = 0;
  let isSwiping = false;

  const onTouchStart = (e) => {
    isInteracting = true;
    isSwiping = true;
    startX = e.touches ? e.touches[0].clientX : e.clientX;
    currentX = startX;
    stopTimer();
  };

  const onTouchMove = (e) => {
    if (!isSwiping) return;
    currentX = e.touches ? e.touches[0].clientX : e.clientX;
  };

  const onTouchEnd = () => {
    if (!isSwiping) return;
    isSwiping = false;
    isInteracting = false;
    const diff = currentX - startX;
    if (diff > 45) {
      // Swiped right -> go prev
      updateSlide(currentIndex - 1, true);
    } else if (diff < -45) {
      // Swiped left -> go next
      updateSlide(currentIndex + 1, true);
    } else {
      restartTimer();
    }
  };

  if (root) {
    root.addEventListener("touchstart", onTouchStart, { passive: true });
    root.addEventListener("touchmove", onTouchMove, { passive: true });
    root.addEventListener("touchend", onTouchEnd);

    // Mouse drag support for desktop/tablet simulator
    root.addEventListener("mousedown", onTouchStart);
    root.addEventListener("mousemove", onTouchMove);
    root.addEventListener("mouseup", onTouchEnd);
    root.addEventListener("mouseleave", () => {
      if (isSwiping) onTouchEnd();
      isInteracting = false;
      startTimer();
    });

    root.addEventListener("mouseenter", () => {
      isInteracting = true;
    });
  }

  // Keyboard navigation
  root?.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") updateSlide(currentIndex - 1, true);
    if (e.key === "ArrowRight") updateSlide(currentIndex + 1, true);
  });

  startTimer();
}
