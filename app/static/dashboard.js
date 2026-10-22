(function () {
  const snapshotUrl = "/dashboard/snapshot";
  const drawer = document.getElementById("log-drawer");
  const logTitle = document.getElementById("log-title");
  const logSubtitle = document.getElementById("log-subtitle");
  const logMetrics = document.getElementById("log-metrics");
  const logEvents = document.getElementById("log-events");
  const logClose = document.getElementById("log-close");
  let previous = {};

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pill(status) {
    return `<span class="pill pill-${String(status).toLowerCase()}">${escapeHtml(status)}</span>`;
  }

  function meter(value) {
    if (value === null || value === undefined) return `<div class="meter empty"><span></span></div>`;
    const cls = value >= 85 ? "bad" : value >= 70 ? "warn" : "";
    return `<div class="meter ${cls}"><span style="width:${Math.min(value, 100)}%"></span></div>`;
  }

  function ago(iso) {
    if (!iso) return "—";
    const delta = Date.now() - Date.parse(iso);
    if (Number.isNaN(delta)) return "—";
    const minutes = Math.max(0, Math.round(delta / 60000));
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.round(minutes / 60)}h ago`;
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function chips(host) {
    const items = [
      `<button type="button" class="chip ${host.exporter.toLowerCase()}" title="${escapeHtml(host.exporter_label)} ${escapeHtml(host.exporter)}" data-host="${escapeHtml(host.name)}" data-check="${escapeHtml(host.exporter_label)}">${escapeHtml(host.exporter_short)}</button>`,
    ].concat(
      (host.services || []).map(
        (service) =>
          `<button type="button" class="chip ${service.status.toLowerCase()}" title="${escapeHtml(service.name)} ${escapeHtml(service.status)}" data-host="${escapeHtml(host.name)}" data-check="${escapeHtml(service.name)}">${escapeHtml(service.short)}</button>`
      )
    );
    return items.join("");
  }

  function renderBars(id, hosts, key, labelKey) {
    const node = document.getElementById(id);
    if (!node) return;
    node.innerHTML = (hosts || [])
      .map((host) => `<div class="bar-row"><span>${escapeHtml(host.name)}</span>${meter(host[key])}<span>${escapeHtml(host[labelKey])}</span></div>`)
      .join("");
  }

  function render(data) {
    const kpis = data.kpis || {};
    const hosts = data.hosts || [];
    setText("kpi-servers", kpis.servers);
    setText("kpi-healthy", kpis.healthy);
    setText("kpi-degraded", kpis.degraded);
    setText("kpi-unreachable", kpis.unreachable);
    setText("kpi-alerts", kpis.firing_alerts);
    setText("kpi-down-services", kpis.down_services);
    setText("kpi-backend", data.prometheus_available ? "Online" : "Down");
    const live = document.getElementById("live-label");
    const dot = document.getElementById("live-dot");
    const hasIssue = !data.prometheus_available || kpis.down_services > 0 || kpis.degraded > 0 || kpis.unreachable > 0;
    if (dot) dot.classList.toggle("down", hasIssue);
    if (live) live.textContent = hasIssue ? "Issue" : "Monitoring Online";

    const total = kpis.servers || 1;
    const healthyDeg = (kpis.healthy / total) * 360;
    const degradedDeg = healthyDeg + (kpis.degraded / total) * 360;
    const donut = document.getElementById("status-donut");
    if (donut) {
      donut.style.background = `conic-gradient(#22c55e 0 ${healthyDeg}deg, #eab308 ${healthyDeg}deg ${degradedDeg}deg, #ef4444 ${degradedDeg}deg 360deg)`;
      donut.innerHTML = `<div class="donut-hole">${kpis.servers}</div>`;
    }
    setText("status-legend", `Healthy ${kpis.healthy} · Degraded ${kpis.degraded} · Unreachable ${kpis.unreachable}`);

    const hostBody = document.getElementById("host-rows");
    if (hostBody) {
      hostBody.innerHTML = hosts
        .map((host) => {
          const changed = previous[host.name] && previous[host.name] !== host.status;
          previous[host.name] = host.status;
          const rowClass = host.status === "Unreachable" ? "is-down" : host.status === "Degraded" ? "is-degraded" : "";
          return `<tr class="host-row ${rowClass}${changed ? " flash" : ""}" data-host="${escapeHtml(host.name)}">
            <td><a href="${escapeHtml(host.href)}">${escapeHtml(host.name)}</a><div class="text-secondary small">${escapeHtml(host.role)}</div></td>
            <td>${escapeHtml(host.ip)}</td>
            <td>${pill(host.status)}</td>
            <td>${escapeHtml(host.cpu)}${meter(host.cpu_value)}</td>
            <td>${escapeHtml(host.memory)}${meter(host.memory_value)}</td>
            <td>${escapeHtml(host.disk)}${meter(host.disk_value)}</td>
            <td>${escapeHtml(host.uptime)}</td>
            <td>${chips(host)}</td>
            <td class="small text-secondary">${ago(host.last_seen)}</td>
          </tr>`;
        })
        .join("");
    }

    const alertList = document.getElementById("alert-list");
    if (alertList) {
      const alerts = data.alerts || [];
      alertList.innerHTML = alerts.length
        ? alerts
            .map(
              (alert) =>
                `<div class="alert-item"><div><strong>${escapeHtml(alert.name)}</strong><div class="text-secondary small">${escapeHtml(alert.server || "unmapped")} · ${escapeHtml(alert.summary || "")}</div></div>${pill(alert.severity)}</div>`
            )
            .join("")
        : `<p class="text-secondary mb-0">No firing alerts on WEB01, APP01, WIN01, or MON01.</p>`;
    }

    const serviceList = document.getElementById("service-list");
    if (serviceList) {
      serviceList.innerHTML = (data.services || [])
        .map((service) => {
          const latency = service.latency_ms == null ? "—" : `${service.latency_ms} ms`;
          return `<button type="button" class="service-item ${service.status === "DOWN" ? "down" : ""}" data-host="${escapeHtml(service.host)}" data-check="${escapeHtml(service.name)}">
            <div><strong>${escapeHtml(service.host)} · ${escapeHtml(service.name)}</strong></div>
            <div class="text-end">${pill(service.status)}<div class="text-secondary small">${escapeHtml(latency)}</div></div>
          </button>`;
        })
        .join("");
    }

    renderBars("cpu-bars", hosts, "cpu_value", "cpu");
    renderBars("mem-bars", hosts, "memory_value", "memory");
    renderBars("disk-bars", hosts, "disk_value", "disk");
    setText("updated-at", "just now");
  }

  async function openLogs(hostName, checkName) {
    if (!drawer) return;
    drawer.hidden = false;
    logTitle.textContent = checkName || hostName;
    logSubtitle.textContent = "Loading event log…";
    logMetrics.innerHTML = "";
    logEvents.innerHTML = "<p class='text-secondary'>Loading…</p>";
    try {
      const response = await fetch(`/dashboard/events/${encodeURIComponent(hostName)}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("failed");
      const data = await response.json();
      const host = data.host || {};
      logTitle.textContent = `${host.name} · ${checkName || host.problem}`;
      logSubtitle.textContent = `${host.role} · ${host.ip} · metrics ${host.instance} · ${host.status}`;
      logMetrics.innerHTML = `
        <div><span>CPU</span><strong>${escapeHtml(host.cpu)}</strong></div>
        <div><span>RAM</span><strong>${escapeHtml(host.memory)}</strong></div>
        <div><span>Disk</span><strong>${escapeHtml(host.disk)}</strong></div>
        <div><span>Uptime</span><strong>${escapeHtml(host.uptime)}</strong></div>`;
      const events = data.events || [];
      logEvents.innerHTML = events.length
        ? events
            .map(
              (event) => `<article class="log-line ${escapeHtml(event.level)}">
                <div class="log-meta">${escapeHtml(event.source)} · ${escapeHtml(event.at || "now")}</div>
                <strong>${escapeHtml(event.title)}</strong>
                <pre>${escapeHtml(event.message)}</pre>
              </article>`
            )
            .join("")
        : "<p class='text-secondary'>No stored events yet. The down state is from the live probe.</p>";
    } catch (_error) {
      logEvents.innerHTML = "<p class='text-danger'>Could not load the event log.</p>";
    }
  }

  function closeLogs() {
    if (drawer) drawer.hidden = true;
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-host]");
    if (!target || event.target.closest("a")) return;
    event.preventDefault();
    openLogs(target.getAttribute("data-host"), target.getAttribute("data-check"));
  });
  if (logClose) logClose.addEventListener("click", closeLogs);
  if (drawer) drawer.addEventListener("click", (event) => {
    if (event.target === drawer) closeLogs();
  });

  async function refresh() {
    if (document.hidden) return;
    try {
      const response = await fetch(snapshotUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) return;
      render(await response.json());
    } catch (_error) {
      const dot = document.getElementById("live-dot");
      if (dot) dot.classList.add("down");
    }
  }

  refresh();
  setInterval(refresh, 5000);
})();
