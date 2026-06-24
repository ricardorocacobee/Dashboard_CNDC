(function () {
    "use strict";

    const CONFIG_URL = "/api/dashboard/config";
    const SESSION_INDEX_KEY = "cndcDashboardRotator.index";
    const SESSION_PAUSED_KEY = "cndcDashboardRotator.paused";

    const state = {
        pages: [],
        index: 0,
        paused: false,
        intervalMs: 40000,
        autoHideMs: 4000,
        loadTimeoutMs: 12000,
        rotationEnabled: true,
        showControls: true,
        rotationTimer: null,
        loadTimer: null,
        controlsTimer: null,
        navigationToken: 0,
        controlsHover: false,
        controlsFocus: false,
    };

    const elements = {};

    document.addEventListener("DOMContentLoaded", initializeRotator);

    function initializeRotator() {
        collectElements();
        bindControls();
        restoreSessionState();
        fetch(CONFIG_URL, { cache: "no-store" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Config HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(applyConfig)
            .catch((error) => {
                console.error("No fue posible cargar la configuracion del dashboard.", error);
                showWarning("No fue posible cargar la configuracion del dashboard.");
            });
    }

    function collectElements() {
        elements.frame = document.getElementById("dashboardFrame");
        elements.label = document.getElementById("screenLabel");
        elements.loading = document.getElementById("loadingStatus");
        elements.warning = document.getElementById("loadWarning");
        elements.controls = document.getElementById("rotatorControls");
        elements.previous = document.getElementById("previousScreen");
        elements.next = document.getElementById("nextScreen");
        elements.pause = document.getElementById("pauseRotation");
        elements.indicators = document.getElementById("pageIndicators");
    }

    function bindControls() {
        elements.previous.addEventListener("click", () => previousPage(true));
        elements.next.addEventListener("click", () => nextPage(true));
        elements.pause.addEventListener("click", togglePause);

        elements.controls.addEventListener("mouseenter", () => {
            state.controlsHover = true;
            revealControls();
        });
        elements.controls.addEventListener("mouseleave", () => {
            state.controlsHover = false;
            revealControls();
        });
        elements.controls.addEventListener("focusin", () => {
            state.controlsFocus = true;
            revealControls();
        });
        elements.controls.addEventListener("focusout", () => {
            state.controlsFocus = elements.controls.contains(document.activeElement);
            revealControls();
        });

        document.addEventListener("mousemove", revealControls);
        document.addEventListener("keydown", handleKeyboardNavigation);
    }

    function applyConfig(config) {
        state.pages = Array.isArray(config.pages) ? config.pages.slice() : [];
        state.rotationEnabled = config.enabled !== false;
        state.showControls = config.show_controls !== false;
        state.intervalMs = secondsToMilliseconds(config.interval_seconds, 40);
        state.autoHideMs = secondsToMilliseconds(config.auto_hide_controls_seconds, 4);
        state.loadTimeoutMs = secondsToMilliseconds(config.load_timeout_seconds, 12);

        document.body.classList.toggle("controls-disabled", !state.showControls);

        if (state.pages.length === 0) {
            showWarning("No existen pantallas habilitadas.");
            return;
        }

        state.index = normalizeIndex(state.index);
        buildIndicators();
        updatePauseButton();
        revealControls();
        navigateTo(state.index, false);
    }

    function secondsToMilliseconds(value, fallbackSeconds) {
        const parsed = Number(value);
        if (!Number.isFinite(parsed) || parsed <= 0) {
            return fallbackSeconds * 1000;
        }
        return parsed * 1000;
    }

    function buildIndicators() {
        elements.indicators.textContent = "";
        state.pages.forEach((page, pageIndex) => {
            const button = document.createElement("button");
            button.className = "indicator-button";
            button.type = "button";
            button.title = page.name;
            button.setAttribute("aria-label", `Mostrar ${page.name}`);
            button.addEventListener("click", () => navigateTo(pageIndex, true));
            elements.indicators.appendChild(button);
        });
    }

    function navigateTo(nextIndex, manual) {
        if (state.pages.length === 0) {
            return;
        }

        const page = state.pages[normalizeIndex(nextIndex)];
        state.index = normalizeIndex(nextIndex);
        saveSessionState();
        renderCurrentPage();
        startLoading();

        const token = state.navigationToken + 1;
        state.navigationToken = token;
        clearLoadTimer();

        elements.frame.onload = () => finishLoading(token);
        elements.frame.src = page.url;
        state.loadTimer = window.setTimeout(() => handleLoadTimeout(token, page), state.loadTimeoutMs);

        restartRotationTimer();
        if (manual) {
            revealControls();
        }
    }

    function renderCurrentPage() {
        const page = state.pages[state.index];
        elements.label.textContent = `${state.index + 1} / ${state.pages.length} - ${page.name}`;
        elements.warning.classList.remove("is-visible");
        elements.warning.textContent = "";

        Array.from(elements.indicators.children).forEach((button, indicatorIndex) => {
            const isCurrent = indicatorIndex === state.index;
            button.textContent = isCurrent ? "\u25cf" : "\u25cb";
            button.setAttribute("aria-current", isCurrent ? "page" : "false");
        });
    }

    function previousPage(manual) {
        navigateTo(state.index - 1, manual);
    }

    function nextPage(manual) {
        navigateTo(state.index + 1, manual);
    }

    function togglePause() {
        state.paused = !state.paused;
        saveSessionState();
        updatePauseButton();
        if (state.paused) {
            clearRotationTimer();
        } else {
            restartRotationTimer();
        }
        revealControls();
    }

    function updatePauseButton() {
        elements.pause.textContent = state.paused ? "\u25b6" : "\u275a\u275a";
        elements.pause.title = state.paused ? "Reanudar rotacion" : "Pausar rotacion";
        elements.pause.setAttribute(
            "aria-label",
            state.paused ? "Reanudar rotacion" : "Pausar rotacion",
        );
        elements.controls.classList.toggle("is-pinned", state.paused);
    }

    function restartRotationTimer() {
        clearRotationTimer();
        if (!state.rotationEnabled || state.paused || state.pages.length < 2) {
            return;
        }
        state.rotationTimer = window.setTimeout(() => nextPage(false), state.intervalMs);
    }

    function clearRotationTimer() {
        if (state.rotationTimer !== null) {
            window.clearTimeout(state.rotationTimer);
            state.rotationTimer = null;
        }
    }

    function startLoading() {
        elements.loading.classList.add("is-visible");
        elements.loading.textContent = "Cargando pantalla...";
        elements.warning.classList.remove("is-visible");
    }

    function finishLoading(token) {
        if (token !== state.navigationToken) {
            return;
        }
        clearLoadTimer();
        elements.loading.classList.remove("is-visible");
    }

    function handleLoadTimeout(token, page) {
        if (token !== state.navigationToken) {
            return;
        }
        clearLoadTimer();
        elements.loading.classList.remove("is-visible");
        showWarning("No fue posible cargar esta pantalla.");
        console.warn("Timeout al cargar pantalla del dashboard.", page);
        revealControls();
    }

    function clearLoadTimer() {
        if (state.loadTimer !== null) {
            window.clearTimeout(state.loadTimer);
            state.loadTimer = null;
        }
    }

    function showWarning(message) {
        elements.warning.textContent = message;
        elements.warning.classList.add("is-visible");
    }

    function revealControls() {
        if (!state.showControls) {
            return;
        }

        elements.controls.classList.remove("is-idle");
        if (state.controlsTimer !== null) {
            window.clearTimeout(state.controlsTimer);
            state.controlsTimer = null;
        }

        if (state.paused || state.controlsHover || state.controlsFocus) {
            return;
        }

        state.controlsTimer = window.setTimeout(() => {
            elements.controls.classList.add("is-idle");
            state.controlsTimer = null;
        }, state.autoHideMs);
    }

    function handleKeyboardNavigation(event) {
        if (isEditableTarget(event.target)) {
            return;
        }

        if (event.key === "ArrowLeft") {
            event.preventDefault();
            previousPage(true);
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            nextPage(true);
        } else if (event.key === " ") {
            event.preventDefault();
            togglePause();
        }
    }

    function isEditableTarget(target) {
        if (!target || target === document.body) {
            return false;
        }
        const tagName = target.tagName ? target.tagName.toLowerCase() : "";
        return tagName === "input" || tagName === "textarea" || tagName === "select" || target.isContentEditable;
    }

    function normalizeIndex(index) {
        const pageCount = state.pages.length;
        return ((index % pageCount) + pageCount) % pageCount;
    }

    function restoreSessionState() {
        try {
            const storedIndex = Number(sessionStorage.getItem(SESSION_INDEX_KEY));
            if (Number.isInteger(storedIndex) && storedIndex >= 0) {
                state.index = storedIndex;
            }
            state.paused = sessionStorage.getItem(SESSION_PAUSED_KEY) === "true";
        } catch (error) {
            console.debug("sessionStorage no disponible para el rotador.", error);
        }
    }

    function saveSessionState() {
        try {
            sessionStorage.setItem(SESSION_INDEX_KEY, String(state.index));
            sessionStorage.setItem(SESSION_PAUSED_KEY, String(state.paused));
        } catch (error) {
            console.debug("sessionStorage no disponible para el rotador.", error);
        }
    }

    window.CNDCDashboardRotator = {
        state,
        restartRotationTimer,
        clearRotationTimer,
    };
})();
