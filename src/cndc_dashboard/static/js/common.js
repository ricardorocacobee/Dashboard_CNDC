(function () {
  const PLOT_CONFIG = {
    responsive: true,
    displaylogo: false,
    scrollZoom: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };

  const COBEE_COLORS = {
    primary: "#0058A0",
    secondary: "#1098E8",
    accent: "#F28C28",
    dark: "#082840",
    lightBlue: "#2090D0",
    green: "#2E8B57",
    red: "#D64545",
    purple: "#7A5AA6",
    brown: "#8B6651",
    gray: "#606878",
    mutedGold: "#B39B35",
    pink: "#C95C9B",
    historicalYesterday: "#6B7280",
    historicalWeekAgo: "#B59A30",
  };

  const GENERATION_SERIES_STYLES = {
    PREV: { color: COBEE_COLORS.primary, width: 2.5, dash: "dash" },
    TOT: { color: COBEE_COLORS.accent, width: 4, dash: "solid" },
    TERMO: { color: COBEE_COLORS.green, width: 2.2, dash: "solid" },
    HIDRO: { color: COBEE_COLORS.secondary, width: 2.2, dash: "solid" },
    SOLAR: { color: COBEE_COLORS.purple, width: 2.2, dash: "solid" },
    EOL: { color: COBEE_COLORS.brown, width: 2.2, dash: "solid" },
    BAGAZO: { color: COBEE_COLORS.pink, width: 2.2, dash: "solid" },
    TOTAL_AYER: { color: COBEE_COLORS.historicalYesterday, width: 1.7, dash: "dash" },
    TOTAL_HACE_7_DIAS: { color: COBEE_COLORS.historicalWeekAgo, width: 1.7, dash: "dot" },
  };

  const DEMAND_SERIES_STYLES = {
    TOTAL_SIN: { color: COBEE_COLORS.primary, width: 4.5 },
    "SANTA CRUZ": { color: COBEE_COLORS.accent, width: 2 },
    "LA PAZ": { color: COBEE_COLORS.green, width: 2 },
    COCHABAMBA: { color: COBEE_COLORS.red, width: 2 },
    POTOSI: { color: COBEE_COLORS.purple, width: 2 },
    ORURO: { color: COBEE_COLORS.brown, width: 2 },
    TARIJA: { color: COBEE_COLORS.pink, width: 2 },
    CHUQUISACA: { color: COBEE_COLORS.gray, width: 2 },
    BENI: { color: COBEE_COLORS.mutedGold, width: 2 },
  };

  function generationStyle(serie) {
    const name = String(serie.nombre || "").trim();
    if (name === "Total Ayer") return GENERATION_SERIES_STYLES.TOTAL_AYER;
    if (name === "Total Hace 7 días") return GENERATION_SERIES_STYLES.TOTAL_HACE_7_DIAS;
    if (name === "Total") return GENERATION_SERIES_STYLES.TOT;
    return GENERATION_SERIES_STYLES[serie.codigo] || { color: COBEE_COLORS.dark, width: 2, dash: "solid" };
  }

  function demandStyle(serie) {
    return DEMAND_SERIES_STYLES[serie.codigo] || { color: COBEE_COLORS.dark, width: 2 };
  }

  function apiFetch(url, options = {}) {
    return fetch(url, options).then(async (response) => {
      if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
          const data = await response.json();
          if (data.detail) detail = data.detail;
        } catch {
          // Keep HTTP detail.
        }
        throw new Error(detail);
      }
      return response.json();
    });
  }

  function formatDate(value) {
    if (!value) return "--";
    const [year, month, day] = value.slice(0, 10).split("-");
    return `${day}/${month}/${year}`;
  }

  function formatDateTime(value) {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("es-BO", {
      timeZone: "America/La_Paz",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date).replace(",", "");
  }

  function sourceStatus(source) {
    return source === "CACHE_MEMORY" || source === "CACHE_DISK" ? "DATOS DE RESPALDO" : "ACTUALIZADO";
  }

  function updateMetadata(payload, fallbackDate) {
    const el = document.getElementById("technicalMetadata");
    if (!el) return;
    const operationDate = payload.fecha || fallbackDate || new Date().toISOString().slice(0, 10);
    const status = sourceStatus(payload.source);
    el.title = `Fuente técnica interna: ${payload.source || "API"}`;
    el.innerHTML = [
      `<span>FECHA DE OPERACIÓN: ${formatDate(operationDate)}</span>`,
      `<span>ESTADO: ${status}</span>`,
      `<span>ÚLTIMA ACTUALIZACIÓN: ${formatDateTime(payload.actualizado_en)}</span>`,
      "<span>FUENTE: CNDC</span>",
    ].join("");
  }

  let toastTimer = null;
  function showToast(text, type = "info", autoHide = true) {
    const el = document.getElementById("statusToast");
    if (!el) return;
    window.clearTimeout(toastTimer);
    el.textContent = text;
    el.className = `status-toast visible ${type === "error" ? "error" : ""}`.trim();
    if (autoHide) {
      toastTimer = window.setTimeout(() => {
        el.className = "status-toast";
      }, 2800);
    }
  }

  function setRefreshBusy(button, busy) {
    if (!button) return;
    button.disabled = busy;
    button.textContent = busy ? "Actualizando..." : "Actualizar ahora";
  }

  function hourlyTickValues(labels, stepHours = 2) {
    const step = Math.max(4, stepHours * 4);
    return labels.filter((_, index) => index % step === step - 1 || index === labels.length - 1);
  }

  function sparseTickValues(labels, targetCount = 12) {
    if (!labels.length) return [];
    const step = Math.max(1, Math.ceil(labels.length / targetCount));
    return labels.filter((_, index) => index % step === 0 || index === labels.length - 1);
  }

  function baseLayout(yTitle, labels, stepHours = 2) {
    return {
      autosize: true,
      margin: { l: 55, r: 18, t: 16, b: 68 },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      hovermode: "x unified",
      xaxis: {
        title: "",
        tickmode: "array",
        tickvals: hourlyTickValues(labels, stepHours),
        tickangle: 0,
        automargin: true,
        showgrid: true,
        gridcolor: "#eeeeee",
      },
      yaxis: {
        title: yTitle,
        automargin: true,
        showgrid: true,
        gridcolor: "#eeeeee",
      },
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: -0.13,
        yanchor: "top",
        font: { size: 10 },
      },
    };
  }

  function reactChart(chartElement, traces, layout) {
    return Plotly.react(chartElement, traces, layout, PLOT_CONFIG).then(() => {
      window.requestAnimationFrame(() => Plotly.Plots.resize(chartElement));
    });
  }

  function installResize(chartElement) {
    window.addEventListener("resize", () => {
      Plotly.Plots.resize(chartElement);
    });
  }

  window.CNDC = {
    PLOT_CONFIG,
    COBEE_COLORS,
    GENERATION_SERIES_STYLES,
    DEMAND_SERIES_STYLES,
    generationStyle,
    demandStyle,
    apiFetch,
    formatDate,
    formatDateTime,
    updateMetadata,
    showToast,
    setRefreshBusy,
    baseLayout,
    sparseTickValues,
    reactChart,
    installResize,
  };
})();
