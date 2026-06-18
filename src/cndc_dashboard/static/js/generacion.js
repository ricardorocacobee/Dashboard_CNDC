(function () {
  const chart = document.getElementById("chart");
  const dateInput = document.getElementById("dateInput");
  const refreshButton = document.getElementById("refreshButton");
  let latestDate = null;
  let selectedDate = null;
  let controller = null;

  function traceFor(serie) {
    return {
      x: window.currentLabels,
      y: serie.valores,
      name: serie.nombre,
      mode: "lines",
      type: "scatter",
      connectgaps: false,
      line: {
        width: serie.nombre === "Total" ? 3 : 2,
        dash: serie.nombre === "Previsto" ? "dash" : serie.nombre.includes("Ayer") || serie.nombre.includes("7") ? "dot" : "solid",
      },
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
    await CNDC.reactChart(chart, traces, CNDC.baseLayout("MW", payload.labels, 2));
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
