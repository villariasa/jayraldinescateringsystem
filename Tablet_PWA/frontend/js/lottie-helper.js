// lottie-helper.js — High-performance offline Lottie helper for Jayraldine's Catering Tablet Kiosk
// Handles caching, hover interactions, touch gestures, tap bursts, and auto-cleanup.

const animationDataCache = new Map();
const activeInstances = new WeakMap();

/**
 * Preloads or fetches animation JSON data from the offline animations folder.
 */
export async function getAnimationData(name) {
  if (animationDataCache.has(name)) {
    return animationDataCache.get(name);
  }

  const filename = name.endsWith(".json") ? name : `${name}.json`;
  const url = `/animations/${filename}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${url}`);
    const data = await res.json();
    animationDataCache.set(name, data);
    return data;
  } catch (err) {
    console.warn(`[Lottie] Failed to load animation: ${name}`, err);
    return null;
  }
}

/**
 * Mounts a Lottie animation into a container.
 * Destroys any existing Lottie instance on the same container to avoid memory leaks.
 */
export async function mountLottie(container, name, options = {}) {
  if (!container || !window.lottie) return null;

  // Clean up any existing instance on this element
  const prev = activeInstances.get(container);
  if (prev) {
    try { prev.destroy(); } catch (_) {}
  }

  const animData = await getAnimationData(name);
  if (!animData) return null;

  const anim = window.lottie.loadAnimation({
    container,
    renderer: options.renderer || "svg",
    loop: options.loop !== undefined ? options.loop : true,
    autoplay: options.autoplay !== undefined ? options.autoplay : true,
    animationData: animData,
    rendererSettings: {
      preserveAspectRatio: options.preserveAspectRatio || "xMidYMid meet",
      progressiveLoad: true,
      hideOnTransparent: true,
      ...options.rendererSettings
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
    renderer: "svg",
    loop: false,
    autoplay: true,
    animationData: animData
  });

  burstAnim.addEventListener("complete", () => {
    try { burstAnim.destroy(); } catch (_) {}
    burstWrap.remove();
  });
}
