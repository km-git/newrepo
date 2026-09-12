async function loadDashboard() {
  const res = await fetch('/api/dashboard');
  const data = await res.json();
  document.getElementById('tenant-count').textContent = data.tenant_count ?? 0;
  document.getElementById('oauth-count').textContent = data.oauth_grant_count ?? 0;
  document.getElementById('tool-count').textContent = data.inventory?.tool_count ?? 0;
  renderOAuth(data.oauth_grants || []);
}

function renderOAuth(grants) {
  const tbody = document.querySelector('#oauth-table tbody');
  tbody.innerHTML = '';
  grants.forEach(g => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${g.app_name || ''}</td><td>${g.publisher || ''}</td><td>${g.scopes || ''}</td><td>${g.risk_level || ''}</td>`;
    tbody.appendChild(tr);
  });
}

async function runScan(tenant) {
  const out = document.getElementById('report-output');
  out.textContent = `Running ${tenant} scan...`;
  const res = await fetch(`/api/scan/${tenant}`, { method: 'POST' });
  const data = await res.json();
  const reportRes = await fetch(`/api/report/${tenant}`);
  const report = await reportRes.json();
  out.textContent = report.markdown || JSON.stringify(data, null, 2);
  renderOAuth(data.oauth_grants || []);
  loadDashboard();
}

loadDashboard();
