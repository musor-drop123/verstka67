// Раньше здесь была автоматическая проверка /profile и показ панели при любой
// активной сессии — это было ошибкой: наличие валидного access_token у ОБЫЧНОГО
// ученика тоже даёт 200 от /profile, и админ-панель показывалась не проверяя
// права. Теперь показываем панель только после успешного /login/admin или
// /signup/admin — единственных мест, где право admin реально проверяется бэком.

document.getElementById("showSignupLink").addEventListener("click", (e) => {
  e.preventDefault();
  document.getElementById("loginBlock").classList.add("hidden");
  document.getElementById("signupBlock").classList.remove("hidden");
});
document.getElementById("showLoginLink").addEventListener("click", (e) => {
  e.preventDefault();
  document.getElementById("signupBlock").classList.add("hidden");
  document.getElementById("loginBlock").classList.remove("hidden");
});

document.getElementById("loginBtn").addEventListener("click", async () => {
  const surname = document.getElementById("loginSurname").value.trim();
  const name = document.getElementById("loginName").value.trim();
  const password = document.getElementById("loginPassword").value;
  const admin_code = document.getElementById("loginAdminCode").value.trim();
  const errorEl = document.getElementById("loginError");
  errorEl.textContent = "";

  if (!surname || !name || !password || !admin_code) {
    errorEl.textContent = "Заполните все поля, включая код доступа.";
    return;
  }

  try {
    const res = await apiPost("/login/admin", { name, surname, password, admin_code });
    if (res.status === 403) {
      errorEl.textContent = "Неверный код доступа администратора.";
      return;
    }
    if (res.redirected && res.url.includes("/signup")) {
      errorEl.textContent = "Неверное имя пользователя или пароль.";
      return;
    }
    // Если пользователь с таким именем не найден, бэк падает в 500
    // (обращение к полю "password" у None), а не отдаёт понятную ошибку.
    if (res.status >= 500) {
      errorEl.textContent = "Неверное имя пользователя или пароль.";
      return;
    }
    if (!res.ok && res.status !== 307 && res.status !== 200) {
      errorEl.textContent = "Ошибка входа.";
      return;
    }
    showAdminPanel();
  } catch {
    errorEl.textContent = "Не удалось связаться с сервером.";
  }
});

document.getElementById("signupBtn").addEventListener("click", async () => {
  const name = document.getElementById("suName").value.trim();
  const surname = document.getElementById("suSurname").value.trim();
  const password = document.getElementById("suPassword").value;
  const admin_code = document.getElementById("suAdminCode").value.trim();
  const errorEl = document.getElementById("signupError");
  errorEl.textContent = "";

  try {
    const res = await apiPost("/signup/admin", { name, surname, password, admin_code });
    if (res.status === 401) {
      errorEl.textContent = "Неверный код доступа администратора.";
      return;
    }
    if (!res.ok) {
      errorEl.textContent = "Не удалось зарегистрироваться.";
      return;
    }
    showAdminPanel();
  } catch {
    errorEl.textContent = "Не удалось связаться с сервером.";
  }
});

function showAdminPanel() {
  document.getElementById("authSection").classList.add("hidden");
  document.getElementById("adminPanel").classList.remove("hidden");
  document.getElementById("logoutLink").classList.remove("hidden");
}

document.getElementById("logoutLink").addEventListener("click", (e) => {
  e.preventDefault();
  logout();
});

// ---------- Живой предпросмотр HTML условия ----------
document.getElementById("taskText").addEventListener("input", (e) => {
  const preview = document.getElementById("taskPreview");
  preview.innerHTML = e.target.value || "<em style='color:var(--text-dim)'>Пусто</em>";
});

// ---------- Добавление задания ----------
document.getElementById("submitTaskBtn").addEventListener("click", async () => {
  const name = document.getElementById("taskName").value.trim();
  const number = document.getElementById("taskNumber").value.trim();
  const diff = document.getElementById("taskDiff").value;
  const text = document.getElementById("taskText").value;
  const answer = document.getElementById("taskAnswer").value.trim();
  const description = document.getElementById("taskDescription").value.trim();
  const msgEl = document.getElementById("taskFormMsg");
  msgEl.textContent = "";
  msgEl.style.color = "var(--red)";

  if (!name || !number || !text || !answer) {
    msgEl.textContent = "Заполните название, номер, условие и ответ.";
    return;
  }
  const numInt = parseInt(number, 10);
  if (isNaN(numInt) || numInt < 1 || numInt > 27) {
    msgEl.textContent = "Номер задания должен быть от 1 до 27.";
    return;
  }

  try {
    const res = await apiPost("/admin/add_task", { name, number, diff, text, answer, description });
    if (res.status === 401 || res.status === 403) {
      msgEl.textContent = "Недостаточно прав. Войдите как преподаватель.";
      return;
    }
    if (!res.ok) {
      msgEl.textContent = "Ошибка при сохранении задания на сервере.";
      return;
    }
    msgEl.style.color = "var(--green)";
    msgEl.textContent = "Задание добавлено ✓";
    document.getElementById("taskName").value = "";
    document.getElementById("taskNumber").value = "";
    document.getElementById("taskText").value = "";
    document.getElementById("taskAnswer").value = "";
    document.getElementById("taskDescription").value = "";
    document.getElementById("taskPreview").innerHTML = "<em style='color:var(--text-dim)'>Начните вводить условие</em>";
  } catch {
    msgEl.textContent = "Не удалось связаться с сервером.";
  }
});

// ---------- Просмотр случайного задания по номеру ----------
document.getElementById("peekBtn").addEventListener("click", async () => {
  const number = document.getElementById("peekNumber").value.trim();
  const resultEl = document.getElementById("peekResult");
  resultEl.innerHTML = "";
  if (!number) return;

  try {
    const res = await apiGet(`/tasks?number=${encodeURIComponent(number)}`);
    if (!res.ok) {
      resultEl.innerHTML = `<span style="color:var(--red)">Заданий с номером ${escapeHtml(number)} не найдено.</span>`;
      return;
    }
    const task = await res.json();
    resultEl.innerHTML = `
      <div class="card" style="background:var(--bg-panel-2);">
        <strong>${escapeHtml(task.name || "")}</strong>
        <span class="badge">№${escapeHtml(String(task.number))} · ${escapeHtml(task.diff || "")}</span>
        <div class="task-statement" style="margin-top:12px;">${task.text || ""}</div>
        <div class="hint">Ответ: ${escapeHtml(String(task.answer))}</div>
      </div>
    `;
  } catch {
    resultEl.innerHTML = `<span style="color:var(--red)">Ошибка сети.</span>`;
  }
});
