(function () {
  const chart = document.getElementById("chart");
  const dateInput = document.getElementById("dateInput");
  const refreshButton = document.getElementById("refreshButton");
  let latestDate = null;
  let selectedDate = null;
  let controller = null;

  function traceFor(serie) {
    const style = CNDC.generationStyle(serie);
    const isHistoricalComparison = serie.nombre === "Total Ayer" || serie.nombre === "Total Hace 7 días";
    return {
      x: window.currentLabels,
      y: serie.valores,
      name: serie.nombre,
      uid: serie.codigo === "TOT" ? serie.nombre : serie.codigo,
      mode: "lines",
      type: "scatter",
      connectgaps: false,
      line: {
        color: style.color,
        width: style.width,
        dash: style.dash,
      },
      visible: isHistoricalComparison ? "legendonly" : true,
    };
  }

  async function loadLatestDate() {
    const latest = await CNDC.apiFetch("/api/fechas/latest");
    latestDate = latest.fecha;
    selectedDate = selectedDate || latest.fecha;
    dateInput.value = selectedDate;
  }

  async function loadChart(forceRefresh = false) {
    if (controller) controller.abort();
    controller = new AbortController();
    CNDC.showToast("Actualizando", "info", false);
    if (forceRefresh) await fetch("/api/refresh", { method: "POST" });
    const payload = await CNDC.apiFetch(`/api/generacion?fecha=${selectedDate}`, { signal: controller.signal });
    window.currentLabels = payload.labels;
    const traces = payload.series.map(traceFor);
    const layout = CNDC.baseLayout("MW", payload.labels, 2);
    layout.uirevision = `generacion-${selectedDate}`;
    await CNDC.reactChart(chart, traces, layout);
    CNDC.updateMetadata(payload, selectedDate);
    CNDC.showToast(payload.source === "API" ? "Actualizado" : "Datos de respaldo");
  }

  async function refresh() {
    CNDC.setRefreshBusy(refreshButton, true);
    try {
      await loadLatestDate();
      await loadChart(true);
    } catch (error) {
      if (error.name !== "AbortError") CNDC.showToast(`Error: ${error.message}`, "error", false);
    } finally {
      CNDC.setRefreshBusy(refreshButton, false);
    }
  }

  dateInput.addEventListener("change", async () => {
    selectedDate = dateInput.value;
    try {
      await loadChart(false);
    } catch (error) {
      if (error.name !== "AbortError") CNDC.showToast(`Error: ${error.message}`, "error", false);
    }
  });

  refreshButton.addEventListener("click", refresh);
  CNDC.installResize(chart);

  (async function init() {
    try {
      await loadLatestDate();
      await loadChart(false);
      window.setInterval(loadLatestDate, 300000);
      window.setInterval(() => {
        if (selectedDate === latestDate) loadChart(false);
      }, 900000);
    } catch (error) {
      CNDC.showToast(`Error: ${error.message}`, "error", false);
    }
  })();
})();
