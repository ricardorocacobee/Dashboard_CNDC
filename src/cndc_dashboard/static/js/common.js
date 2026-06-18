(function () {
  const PLOT_CONFIG = {
    responsive: true,
    displaylogo: false,
    scrollZoom: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };

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
