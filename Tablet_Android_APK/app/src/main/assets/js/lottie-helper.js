// lottie-helper.js — High-performance offline Lottie helper for Jayraldine's Catering Tablet Kiosk
// Pre-bundled offline vector animations loaded dynamically on-demand to eliminate boot jank

const animationDataCache = new Map();
const activeInstances = new WeakMap();

let animationsModulePromise = null;
let loadedAnimations = null;

async function getBundledAnimations() {
  if (loadedAnimations) return loadedAnimations;
  if (!animationsModulePromise) {
    animationsModulePromise = import("./animations-data.js")
      .then((m) => {
        loadedAnimations = m.ANIMATIONS || {};
        return loadedAnimations;
      })
      .catch((err) => {
        console.warn("[Lottie] Failed to load animations bundle", err);
        loadedAnimations = {};
        return loadedAnimations;
      });
  }
  return animationsModulePromise;
}

/**
 * Preloads or fetches animation JSON data from the offline animations bundle.
 */
export async function getAnimationData(name) {
  if (!name) return null;
  const cleanName = String(name).replace(/\.json$/, "").trim();

  // 1. Instantaneous in-memory lookup from bundled offline animations (lazy loaded on first use)
  const bundled = await getBundledAnimations();
  if (bundled && bundled[cleanName]) {
    return bundled[cleanName];
  }

  if (animationDataCache.has(cleanName)) {
    return animationDataCache.get(cleanName);
  }

  const filename = `${cleanName}.json`;
  // 2. Relative URLs work in Android WebView assets, standalone PWAs, and file:///
  const candidateUrls = [
    `animations/${filename}`,
    `/animations/${filename}`,
    `assets/animations/${filename}`
  ];

  for (const url of candidateUrls) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        animationDataCache.set(cleanName, data);
        return data;
      }
    } catch (_) {}
  }

  console.warn(`[Lottie] Animation not found: ${name}`);
  return null;
}

/**
 * Mounts a Lottie animation into a container using GPU-composited Canvas rendering.
 * Destroys any existing Lottie instance on the same container to avoid memory leaks.
 */
export async function mountLottie(container, name, options = {}) {
  if (!container || !window.lottie) return null;

  const animData = await getAnimationData(name);
  if (!animData) {
    // If animation data could not be found, preserve any existing icon child
    return null;
  }

  // Destroy any existing Lottie instance on this element
  const prev = activeInstances.get(container);
  if (prev) {
    try { prev.destroy(); } catch (_) {}
  }

  // Clear existing content only once the animation data is verified ready
  container.innerHTML = "";

  const anim = window.lottie.loadAnimation({
    container,
    renderer: options.renderer || "canvas",
    loop: options.loop !== undefined ? options.loop : true,
    autoplay: options.autoplay !== undefined ? options.autoplay : true,
    animationData: animData,
    rendererSettings: {
      clearCanvas: true,
      preserveAspectRatio: options.preserveAspectRatio || "xMidYMid meet",
      progressiveLoad: true,
      hideOnTransparent: true,
      ...options.rendererSettings
    }
  });

  // Ensure rendered canvas or svg fills container according to CSS without hardcoded pixel attributes
  anim.addEventListener("DOMLoaded", () => {
    const el = container.querySelector("canvas") || container.querySelector("svg");
    if (el) {
      el.removeAttribute("width");
      el.removeAttribute("height");
      el.style.cssText = "width:100%;height:100%;display:block;";
    }
  });

  if (options.speed) {
    anim.setSpeed(options.speed);
  }

  if (options.onComplete) {
    anim.addEventListener("complete", options.onComplete);
  }

  activeInstances.set(container, anim);
  return anim;
}

/**
 * Mounts a micro-interaction Lottie animation that plays on hover or touch.
 * On mouseenter: plays forward.
 * On mouseleave: reverses or plays forward to end.
 */
export async function mountHoverLottie(container, name, options = {}) {
  if (!container || !window.lottie) return null;

  const anim = await mountLottie(container, name, {
    loop: false,
    autoplay: false,
    speed: options.speed || 1.2,
    ...options
  });

  if (!anim) return null;

  let isHovered = false;

  const onEnter = () => {
    isHovered = true;
    anim.setDirection(1);
    anim.play();
  };

  const onLeave = () => {
    isHovered = false;
    if (options.reverseOnLeave) {
      anim.setDirection(-1);
      anim.play();
    } else {
      // Return to frame 0 smoothly
      anim.goToAndStop(0, true);
    }
  };

  container.addEventListener("mouseenter", onEnter);
  container.addEventListener("mouseleave", onLeave);
  container.addEventListener("touchstart", onEnter, { passive: true });
  container.addEventListener("touchend", onLeave, { passive: true });

  return anim;
}

/**
 * Triggers a one-shot burst animation on top of a target element (e.g. START ORDER button tap).
 * Automatically cleans up its overlay after completion.
 */
export async function playTapBurst(targetEl, name = "cloche-tap-burst") {
  if (!targetEl || !window.lottie) return;

  const burstWrap = document.createElement("div");
  burstWrap.className = "lottie-burst-overlay";
  burstWrap.style.position = "absolute";
  burstWrap.style.top = "50%";
  burstWrap.style.left = "50%";
  burstWrap.style.transform = "translate(-50%, -50%)";
  burstWrap.style.width = "140px";
  burstWrap.style.height = "140px";
  burstWrap.style.pointerEvents = "none";
  burstWrap.style.zIndex = "10";

  targetEl.style.position = targetEl.style.position || "relative";
  targetEl.appendChild(burstWrap);

  const animData = await getAnimationData(name);
  if (!animData) {
    burstWrap.remove();
    return;
  }

  const burstAnim = window.lottie.loadAnimation({
    container: burstWrap,
    renderer: "canvas",
    loop: false,
    autoplay: true,
    animationData: animData,
    rendererSettings: {
      clearCanvas: true,
      preserveAspectRatio: "xMidYMid meet"
    }
  });

  burstAnim.addEventListener("complete", () => {
    try { burstAnim.destroy(); } catch (_) {}
    burstWrap.remove();
  });
}
