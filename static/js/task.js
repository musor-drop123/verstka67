// ---------- Состояние ----------
let currentTask = null;
let pyodide = null;
let ws = null;
let chatHistory = [];

const params = new URLSearchParams(window.location.search);
const taskId = params.get("id");

// ---------- Инициализация ----------
(async () => {
  await requireAuth();

  if (!taskId) {
    document.getElementById("taskTitle").textContent = "Задача не указана";
    return;
  }

  await loadTask();
  initPyodide();
  connectChatWs();

  document.getElementById("logoutLink").addEventListener("click", (e) => {
    e.preventDefault();
    logout();
  });
  document.getElementById("checkAnswerBtn").addEventListener("click", checkAnswer);
  document.getElementById("runBtn").addEventListener("click", runCode);
  document.getElementById("clearConsoleBtn").addEventListener("click", () => {
    setConsole("Вывод программы появится здесь.", false);
  });
  document.getElementById("chatSendBtn").addEventListener("click", sendChatMessage);
  document.getElementById("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });
  document.getElementById("codeEditor").addEventListener("keydown", (e) => {
    // Таб вставляет отступ вместо перехода фокуса — иначе писать код неудобно
    if (e.key === "Tab") {
      e.preventDefault();
      const el = e.target;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      el.value = el.value.slice(0, start) + "    " + el.value.slice(end);
      el.selectionStart = el.selectionEnd = start + 4;
    }
  });
})();

// ---------- Загрузка задачи ----------
async function loadTask() {
  try {
    const res = await apiGet(`/tasks/${encodeURIComponent(taskId)}`);
    if (res.status === 401) {
      window.location.href = "/static/login.html";
      return;
    }
    if (!res.ok) {
      document.getElementById("taskTitle").textContent = "Не удалось загрузить задачу";
      return;
    }
    currentTask = await res.json();
    renderTask(currentTask);
  } catch (err) {
    document.getElementById("taskTitle").textContent = "Ошибка сети";
  }
}

function renderTask(task) {
  document.getElementById("taskTitle").textContent = task.name || `Задача №${task.number}`;
  document.getElementById("taskBadge").textContent = `№${task.number} · сложность: ${task.diff || "?"}`;
  // Условие приходит как готовый HTML из БД (поле text) — так и задумано автором бэка.
  // ВНИМАНИЕ: это делает возможной XSS-инъекцию, если админка не фильтрует ввод при
  // создании задания. Рендерим как есть, т.к. источник — доверенные преподаватели,
  // но в проде стоит прогонять text через санитайзер (например DOMPurify) перед вставкой.
  document.getElementById("taskStatement").innerHTML = task.text || "<em>Условие отсутствует</em>";
}

// ---------- Проверка ответа ----------
function checkAnswer() {
  const input = document.getElementById("answerInput").value.trim();
  const resultEl = document.getElementById("answerResult");
  if (!currentTask) return;
  if (!input) {
    resultEl.style.color = "var(--red)";
    resultEl.textContent = "Введите ответ.";
    return;
  }
  // Сверяем на фронте, т.к. отдельного эндпоинта проверки ответа в бэке нет —
  // /tasks/{id} и так отдаёт поле answer целиком.
  if (input === String(currentTask.answer).trim()) {
    resultEl.style.color = "var(--green)";
    resultEl.textContent = "Верно! ✓";
  } else {
    resultEl.style.color = "var(--red)";
    resultEl.textContent = "Неверно, попробуй ещё раз.";
  }
}

// ---------- Песочница Python (Pyodide, в браузере, без ФС и терминала) ----------
async function initPyodide() {
  const statusEl = document.getElementById("pyodideStatus");
  try {
    pyodide = await loadPyodide();
    statusEl.textContent = "Python готов";
    setTimeout(() => (statusEl.textContent = ""), 2000);
  } catch (err) {
    statusEl.textContent = "Не удалось загрузить Python-песочницу";
  }
}

async function runCode() {
  const code = document.getElementById("codeEditor").value;
  const consoleEl = document.getElementById("consoleOutput");

  if (!pyodide) {
    setConsole("Песочница ещё не загружена, подождите...", true);
    return;
  }
  if (!code.trim()) {
    setConsole("Нечего запускать — код пуст.", true);
    return;
  }

  let output = "";
  // Перехватываем stdout/stderr в переменную вместо реальной консоли —
  // никакого доступа к файловой системе или терминалу хоста не даётся.
  pyodide.setStdout({ batched: (s) => (output += s + "\n") });
  pyodide.setStderr({ batched: (s) => (output += s + "\n") });

  try {
    await pyodide.runPythonAsync(code);
    setConsole(output || "(программа завершилась без вывода)", false);
  } catch (err) {
    setConsole(output + "\n" + String(err), true);
  }
}

function setConsole(text, isError) {
  const el = document.getElementById("consoleOutput");
  el.textContent = text;
  el.classList.toggle("has-error", !!isError);
}

// ---------- Чат с ИИ через WebSocket ----------
let aiStreamOpen = false;

function connectChatWs() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/explain/ai`);

  ws.addEventListener("open", () => {
    appendChat("system", "Соединение с ИИ установлено.");
  });

  ws.addEventListener("message", (event) => {
    // Бэк может прислать как обычный текст, так и JSON-событие от Replicate —
    // формат зависит от того, во что сериализуется объект event на сервере.
    let text = event.data;
    try {
      const parsed = JSON.parse(event.data);
      text = parsed.text || parsed.output || parsed.content || JSON.stringify(parsed);
    } catch {
      // не JSON — используем как есть
    }
    appendChat("ai", text, true);
  });

  ws.addEventListener("close", () => {
    appendChat("system", "Соединение с ИИ закрыто. Обновите страницу, чтобы продолжить чат.");
  });

  ws.addEventListener("error", () => {
    appendChat("system", "Ошибка соединения с ИИ.");
  });
}

function sendChatMessage() {
  const input = document.getElementById("chatInput");
  const comment = input.value.trim();
  if (!comment) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    appendChat("system", "Нет соединения с ИИ. Обновите страницу.");
    return;
  }

  const code = document.getElementById("codeEditor").value;
  const taskText = currentTask ? stripHtml(currentTask.text || "") : "";

  appendChat("user", comment);
  aiStreamOpen = false; // следующий ответ ИИ начнёт новый пузырь
  ws.send(JSON.stringify({ task: taskText, code, comment }));
  input.value = "";
}

function appendChat(role, text, isStreamChunk) {
  const log = document.getElementById("chatLog");

  // Стриминговые ответы ИИ могут приходить несколькими сообщениями подряд —
  // дописываем в последний AI-пузырь, пока он "открыт" для этого ответа.
  if (isStreamChunk && aiStreamOpen && log.lastElementChild) {
    log.lastElementChild.textContent += text;
    log.scrollTop = log.scrollHeight;
    return;
  }

  const div = document.createElement("div");
  div.className = `chat-msg ${role === "ai" ? "ai" : role === "user" ? "user" : "system"}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;

  if (isStreamChunk) aiStreamOpen = true;
}

function stripHtml(html) {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent || div.innerText || "";
}
