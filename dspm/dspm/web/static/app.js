const titles = {
  dashboard: "Dashboard",
  findings: "Findings",
  risks: "Risk Scores",
  exposures: "Exposure Scan",
  catalog: "Catalog & Lineage",
  governance: "Governance Policies",
  siem: "SIEM Events",
  warehouse: "SQL Warehouse",
  remediation: "Remediation Plan",
  sources: "Data Sources",
};

function tableFromRows(rows, columns) {
  if (!rows || !rows.length) return "<p class='muted'>No data</p>";
  const cols = columns || Object.keys(rows[0]);
  const head = cols.map((c) => `<th>${c}</th>`).join("");
  const body = rows
    .map((r) => `<tr>${cols.map((c) => `<td>${r[c] ?? ""}</td>`).join("")}</tr>`)
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const s = data.summary || {};
  document.getElementById("metrics-grid").innerHTML = `
    <div class="metric"><div class="label">Findings</div><div class="value">${s.findings_total ?? 0}</div></div>
    <div class="metric warn"><div class="label">PII/PHI/PCI</div><div class="value">${s.pii_findings ?? 0}</div></div>
    <div class="metric danger"><div class="label">Avg Risk</div><div class="value">${s.avg_risk_score ?? 0}</div></div>
    <div class="metric danger"><div class="label">Critical Exposure</div><div class="value">${s.critical_exposures ?? 0}</div></div>
    <div class="metric"><div class="label">Health</div><div class="value">${s.health ?? "—"}</div></div>
  `;
  document.getElementById("recent-findings").innerHTML = tableFromRows(
    (data.recent_findings || []).slice(0, 8),
    ["type", "location", "confidence", "verdict"]
  );
  const alerts = data.alerts || [];
  document.getElementById("active-alerts").innerHTML = alerts.length
    ? alerts.map((a) => `<div class="alert-item"><strong>${a.name}</strong>: ${a.condition} (${a.status})</div>`).join("")
    : "<p>No firing alerts</p>";
}

async function loadFindings() {
  const rows = await api("/api/findings?limit=100");
  document.getElementById("findings-table").innerHTML = tableFromRows(rows, [
    "id", "type", "location", "confidence", "verdict", "source",
  ]);
}

async function loadRisks() {
  const rows = await api("/api/risks?limit=100");
  document.getElementById("risks-table").innerHTML = tableFromRows(rows, [
    "id", "finding_id", "score", "vector", "suggested_action",
  ]);
}

async function loadExposures() {
  const rows = await api("/api/exposures?limit=100");
  document.getElementById("exposures-table").innerHTML = tableFromRows(rows, [
    "id", "resource", "exposure_type", "severity",
  ]);
}

async function loadCatalog() {
  const data = await api("/api/catalog");
  document.getElementById("catalog-assets").innerHTML = tableFromRows(
    data.assets || [],
    ["name", "asset_type", "owner", "urn"]
  );
  document.getElementById("lineage-json").textContent = JSON.stringify(data.lineage, null, 2);
}

async function loadGovernance() {
  const policies = await api("/api/governance");
  document.getElementById("gov-policies").innerHTML = policies
    .map((p) => `<div class="alert-item"><strong>${p.name}</strong> (${p.policy_type})<br><small>${JSON.stringify(p.definition)}</small></div>`)
    .join("");
}

async function loadSiem(q = "*") {
  const rows = await api(`/api/siem?q=${encodeURIComponent(q)}`);
  document.getElementById("siem-events").innerHTML = tableFromRows(rows, [
    "id", "event_type", "severity", "source", "message", "created_at",
  ]);
}

async function loadWarehouse() {
  const history = await api("/api/warehouse/history");
  document.getElementById("query-history").innerHTML = tableFromRows(history, [
    "id", "sql_text", "duration_ms", "row_count", "user_name",
  ]);
}

async function loadRemediation() {
  const plan = await api("/api/remediation");
  document.getElementById("remediation-plan").innerHTML = tableFromRows(plan, [
    "target", "action", "risk_level", "dry_run_safe",
  ]);
}

async function loadSources() {
  const objects = await api("/api/sources/objects?limit=50");
  document.getElementById("source-objects-table").innerHTML = tableFromRows(objects, [
    "provider", "name", "store_type", "source_uri", "path",
  ]);
}

const loaders = {
  dashboard: loadDashboard,
  findings: loadFindings,
  risks: loadRisks,
  exposures: loadExposures,
  catalog: loadCatalog,
  governance: loadGovernance,
  siem: () => loadSiem(document.getElementById("siem-query").value),
  warehouse: loadWarehouse,
  remediation: loadRemediation,
  sources: loadSources,
};

document.querySelectorAll(".nav").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const panel = btn.dataset.panel;
    document.getElementById(`panel-${panel}`).classList.add("active");
    document.getElementById("page-title").textContent = titles[panel] || panel;
    if (loaders[panel]) loaders[panel]();
  });
});

document.getElementById("btn-scan").addEventListener("click", async () => {
  document.getElementById("btn-scan").textContent = "Scanning…";
  await api("/api/scan", { method: "POST" });
  document.getElementById("btn-scan").textContent = "Run Full Scan";
  loadDashboard();
});

document.getElementById("btn-mask").addEventListener("click", async () => {
  const value = document.getElementById("mask-input").value;
  const data_type = document.getElementById("mask-type").value;
  const r = await api("/api/governance/mask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value, data_type, role: "DATA_USER" }),
  });
  document.getElementById("mask-result").textContent = JSON.stringify(r, null, 2);
});

document.getElementById("btn-siem-search").addEventListener("click", () => {
  loadSiem(document.getElementById("siem-query").value);
});

document.getElementById("btn-sql").addEventListener("click", async () => {
  const sql = document.getElementById("sql-input").value;
  const r = await api("/api/warehouse/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });
  document.getElementById("sql-result").innerHTML = tableFromRows(r.rows, r.columns);
  loadWarehouse();
});

document.getElementById("btn-source-scan").addEventListener("click", async () => {
  const scheme = document.getElementById("source-scheme").value;
  const path = document.getElementById("source-path").value;
  const uri = scheme + path;
  document.getElementById("btn-source-scan").textContent = "Scanning…";
  const r = await api("/api/sources/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uri, max_objects: 200 }),
  });
  document.getElementById("btn-source-scan").textContent = "Discover + Classify";
  document.getElementById("source-results").innerHTML = `
    <p><strong>${r.object_count}</strong> objects, <strong>${r.finding_count}</strong> findings from <code>${r.source_uri}</code></p>
    ${tableFromRows(r.findings || [], ["type", "location", "confidence", "verdict", "object_name"])}
  `;
  loadSources();
  loadDashboard();
});

document.getElementById("btn-source-discover").addEventListener("click", async () => {
  const scheme = document.getElementById("source-scheme").value;
  const path = document.getElementById("source-path").value;
  const uri = scheme + path;
  const r = await api("/api/sources/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uri, max_objects: 100 }),
  });
  document.getElementById("source-results").innerHTML = tableFromRows(
    r.objects || [],
    ["name", "provider", "store_type", "path", "size_bytes"]
  );
});

api("/api/health").then((h) => {
  document.getElementById("health-status").textContent = `● ${h.status} v${h.version}`;
});
loadDashboard();
