// Hero carousel: hand-rolled rotation (not Flowbite's Carousel class) so the
// auto-advance interval is a single, precise constant instead of fighting
// Flowbite's default 3000ms timer. Markup/classes still follow Flowbite's
// carousel conventions for visual consistency.
const HERO_INTERVAL_MS = 6000;

function initHeroCarousel() {
    const root = document.querySelector("[data-hero-carousel]");
    if (!root) return;

    const slides = Array.from(root.querySelectorAll("[data-hero-slide]"));
    const indicators = Array.from(root.querySelectorAll("[data-hero-indicator]"));
    if (slides.length <= 1) return;

    let current = 0;
    let timer = null;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function show(index) {
        current = (index + slides.length) % slides.length;
        slides.forEach((slide, i) => slide.classList.toggle("hidden", i !== current));
        indicators.forEach((dot, i) => {
            dot.setAttribute("aria-current", i === current ? "true" : "false");
            dot.classList.toggle("bg-white", i === current);
            dot.classList.toggle("bg-white/50", i !== current);
        });
    }

    function restart() {
        if (timer) window.clearInterval(timer);
        if (!prefersReducedMotion) {
            timer = window.setInterval(() => show(current + 1), HERO_INTERVAL_MS);
        }
    }

    root.querySelector("[data-hero-prev]")?.addEventListener("click", () => {
        show(current - 1);
        restart();
    });
    root.querySelector("[data-hero-next]")?.addEventListener("click", () => {
        show(current + 1);
        restart();
    });
    indicators.forEach((dot, i) => {
        dot.addEventListener("click", () => {
            show(i);
            restart();
        });
    });
    root.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            show(current - 1);
            restart();
        } else if (event.key === "ArrowRight") {
            show(current + 1);
            restart();
        }
    });

    show(0);
    restart();
}

// Shared handler for the two anonymous JSON endpoints (assistant ask, contact
// form) driven via htmx: both return JSON, not an HTML fragment, so htmx's
// default swap is skipped (hx-swap="none") and this listener renders the
// parsed response into the target itself.
function initAssistantWidget() {
    const toggle = document.getElementById("assistant-toggle");
    const panel = document.getElementById("assistant-panel");
    const log = document.getElementById("assistant-log");
    const form = document.getElementById("assistant-form");
    if (!toggle || !panel || !form) return;

    toggle.addEventListener("click", () => {
        const isOpen = !panel.classList.contains("hidden");
        panel.classList.toggle("hidden", isOpen);
        toggle.setAttribute("aria-expanded", String(!isOpen));
    });

    function appendMessage(role, text) {
        const bubble = document.createElement("p");
        bubble.className =
            role === "user"
                ? "ml-auto max-w-[85%] rounded-lg bg-brand-50 px-3 py-2 text-brand-700"
                : "mr-auto max-w-[85%] rounded-lg bg-gray-100 px-3 py-2 text-gray-800";
        bubble.textContent = text;
        log.appendChild(bubble);
        log.scrollTop = log.scrollHeight;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("assistant-question");
        const question = input.value.trim();
        if (!question) return;
        appendMessage("user", question);
        input.value = "";

        try {
            const response = await fetch("/api/v1/assistant/ask/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question }),
            });
            const data = await response.json();
            if (!response.ok) {
                appendMessage("assistant", data.detail || "Sorry, something went wrong. Please try again.");
                return;
            }
            appendMessage("assistant", data.text);
        } catch (error) {
            appendMessage("assistant", "Sorry, the assistant is unavailable right now.");
        }
    });
}

function initContactForm() {
    const form = document.getElementById("contact-form");
    const status = document.getElementById("contact-status");
    if (!form || !status) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        const payload = Object.fromEntries(formData.entries());

        try {
            const response = await fetch("/api/v1/content/contact/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) {
                status.textContent = "Please check the form and try again.";
                status.className = "mt-4 text-sm text-red-600";
                return;
            }
            status.textContent = "Message sent — we'll be in touch soon.";
            status.className = "mt-4 text-sm text-brand-600";
            form.reset();
        } catch (error) {
            status.textContent = "Sorry, something went wrong. Please try again.";
            status.className = "mt-4 text-sm text-red-600";
        }
    });
}

// Program list department filter: lightweight client-side show/hide, no
// page reload and no external library.
function initProgramFilter() {
    const chips = document.querySelectorAll("[data-filter-chip]");
    const items = document.querySelectorAll("[data-program-item]");
    if (!chips.length) return;

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            chips.forEach((c) => c.setAttribute("aria-pressed", "false"));
            chip.setAttribute("aria-pressed", "true");

            const department = chip.dataset.department;
            items.forEach((item) => {
                const matches = department === "all" || item.dataset.department === department;
                item.classList.toggle("hidden", !matches);
            });
        });
    });
}

// Show/hide toggle for password fields (currently just the student portal
// login). Swaps the input's type between "password" and "text", and swaps
// the eye / eye-slash icon and aria-label to match the resulting state.
function initPasswordToggles() {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        const input = document.getElementById(button.dataset.target);
        const showIcon = button.querySelector("[data-icon-show]");
        const hideIcon = button.querySelector("[data-icon-hide]");
        if (!input || !showIcon || !hideIcon) return;

        button.addEventListener("click", () => {
            const isCurrentlyHidden = input.type === "password";
            input.type = isCurrentlyHidden ? "text" : "password";
            showIcon.classList.toggle("hidden", isCurrentlyHidden);
            hideIcon.classList.toggle("hidden", !isCurrentlyHidden);
            button.setAttribute("aria-label", isCurrentlyHidden ? "Hide password" : "Show password");
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initHeroCarousel();
    initAssistantWidget();
    initContactForm();
    initProgramFilter();
    initPasswordToggles();
});
