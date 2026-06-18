(function () {
  const chart = document.getElementById("chart");
  const refreshButton = document.getElementById("refreshButton");

  function referenceTrace(labels, value, name, dash, color) {
    return {
      x: labels,
      y: labels.map(() => value),
      name,
      mode: "lines",
      type: "scatter",
      hoverinfo: "skip",
      line: { width: 1.3, dash, color },
    };
  }

  async function loadChart(forceRefresh = false) {
    CNDC.showToast("Actualizando", "info", false);
    if (forceRefresh) await fetch("/api/refresh", { method: "POST" });
    const payload = await CNDC.apiFetch("/api/frecuencia?registros=360");
    const traces = [
      {
        x: payload.labels,
        y: payload.valores,
        name: "Frecuencia",
        mode: "lines",
        type: "scatter",
        line: { width: 3, color: CNDC.COBEE_COLORS.primary },
      },
      referenceTrace(payload.labels, payload.limite_inferior, "49.75 Hz", "dash", CNDC.COBEE_COLORS.accent),
      referenceTrace(payload.labels, payload.nominal, "50.00 Hz", "dot", CNDC.COBEE_COLORS.green),
      referenceTrace(payload.labels, payload.limite_superior, "50.25 Hz", "dash", CNDC.COBEE_COLORS.red),
    ];
    const layout = CNDC.baseLayout("Hz", payload.labels, 1);
    layout.yaxis.range = [49.4, 50.6];
    layout.xaxis.tickmode = "array";
    layout.xaxis.tickvals = CNDC.sparseTickValues(payload.labels, 12);
    layout.margin = { l: 55, r: 18, t: 12, b: 62 };
    layout.uirevision = "frecuencia-sin";
    await CNDC.reactChart(chart, traces, layout);
    document.getElementById("lastFrequency").textContent = payload.ultimo_valor == null ? "--" : `${payload.ultimo_valor} Hz`;
    document.getElementById("lastFrequencyTime").textContent = payload.ultima_hora || "--";
    document.getElementById("frequencyState").textContent = (payload.estado || "--").toUpperCase();
    CNDC.updateMetadata(payload, new Date().toISOString().slice(0, 10));
    CNDC.showToast(payload.source === "API" ? "Actualizado" : "Datos de respaldo");
  }

  async function refresh() {
    CNDC.setRefreshBusy(refreshButton, true);
    try {
      await loadChart(true);
    } catch (error) {
      CNDC.showToast(`Error: ${error.message}`, "error", false);
    } finally {
      CNDC.setRefreshBusy(refreshButton, false);
    }
  }

  refreshButton.addEventListener("click", refresh);
  CNDC.installResize(chart);

  (async function init() {
    try {
      await loadChart(false);
      window.setInterval(loadChart, 60000);
    } catch (error) {
      CNDC.showToast(`Error: ${error.message}`, "error", false);
    }
  })();
})();
