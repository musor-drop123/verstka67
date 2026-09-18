// Общие хелперы для всех страниц

async function apiGet(path) {
  const res = await fetch(path, { credentials: "include" });
  return res;
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res;
}

// signup/login/admin — GET-запросы с данными в query string (см. текущую реализацию бэка)
function buildQuery(params) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => usp.set(k, v));
  return usp.toString();
}

async function requireAuth() {
  const res = await apiGet("/profile");
  if (res.status === 401 || res.status === 403) {
    window.location.href = "/static/login.html";
    return null;
  }
  if (!res.ok) return null;
  try {
    return await res.json();
  } catch {
    return {};
  }
}

function logout() {
  document.cookie = "access_token=; Max-Age=0; path=/";
  document.cookie = "refresh_token=; Max-Age=0; path=/";
  window.location.href = "/static/login.html";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
