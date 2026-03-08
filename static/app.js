const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const leaveDelayMs = prefersReducedMotion ? 0 : 220;

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
    if (image.complete && image.naturalWidth > 0) {
      markReady();
      return;
    }

    image.addEventListener("load", markReady, { once: true });
    image.addEventListener("error", markReady, { once: true });
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
