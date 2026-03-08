const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const leaveDelayMs = prefersReducedMotion ? 0 : 220;
const INLINE_FALLBACK =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='800' viewBox='0 0 1200 800'>" +
      "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>" +
      "<stop offset='0%' stop-color='#0f172a'/>" +
      "<stop offset='55%' stop-color='#1d4ed8'/>" +
      "<stop offset='100%' stop-color='#0ea5a6'/>" +
      "</linearGradient></defs>" +
      "<rect width='1200' height='800' fill='url(#g)'/>" +
      "<rect x='80' y='580' width='1040' height='140' rx='20' fill='rgba(2,6,23,0.55)'/>" +
      "<text x='120' y='665' fill='#e2e8f0' font-family='Segoe UI, Arial, sans-serif' font-size='64' font-weight='700'>City Weather</text>" +
    "</svg>"
  );

function setupRevealObserver() {
  const revealNodes = document.querySelectorAll(".reveal");
  if (!revealNodes.length) {
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("show");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );

  revealNodes.forEach((node) => observer.observe(node));
}

function setupMediaShells() {
  document.querySelectorAll(".media-shell").forEach((shell) => {
    const image = shell.querySelector("img.lazy-image");
    if (!image) {
      shell.classList.add("ready");
      return;
    }

    const markReady = () => shell.classList.add("ready");
    const fallbackImage = image.dataset.fallback || "/city-image/City";

    const onError = () => {
      const src = image.getAttribute("src") || "";
      if (!image.dataset.fallbackTried) {
        image.dataset.fallbackTried = "1";
        image.src = src.includes("/city-image/") ? INLINE_FALLBACK : fallbackImage;
        return;
      }

      // Last-resort: hide the broken img icon and keep glass background visible.
      image.style.display = "none";
      markReady();
    };

    if (image.complete && image.naturalWidth > 0) {
      markReady();
      return;
    }

    image.addEventListener("load", markReady, { once: true });
    image.addEventListener("error", onError);
  });
}

function startLeaveTransition() {
  if (document.body.classList.contains("is-leaving")) {
    return;
  }
  document.body.classList.add("is-loading", "is-leaving");
}

function handleInternalLinkClicks() {
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (!link) {
      return;
    }
    if (
      link.dataset.noTransition === "true" ||
      link.target === "_blank" ||
      link.hasAttribute("download") ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }

    const href = link.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
      return;
    }

    const destination = new URL(link.href, window.location.href);
    if (destination.origin !== window.location.origin || destination.href === window.location.href) {
      return;
    }

    event.preventDefault();
    startLeaveTransition();
    window.setTimeout(() => {
      window.location.assign(destination.href);
    }, leaveDelayMs);
  });
}

function handleFormTransitions() {
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    if (form.dataset.noTransition === "true") {
      return;
    }
    startLeaveTransition();
  });
}

function clearLoadingState() {
  document.body.classList.remove("is-loading", "is-leaving");
}

window.addEventListener("pageshow", clearLoadingState);

setupRevealObserver();
setupMediaShells();
handleInternalLinkClicks();
handleFormTransitions();
