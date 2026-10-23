const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

let authHeader = "";
let currentUser = null;
const $ = (id) => document.getElementById(id);

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {"Content-Type":"application/json", ...(authHeader ? {"Authorization":authHeader} : {}), ...(options.headers || {})}
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Не удалось выполнить запрос");
  return data;
}
async function init() {
  if (tg?.initData) {
    authHeader = "tma " + tg.initData;
    currentUser = tg.initDataUnsafe?.user || null;
  } else {
    const config = await api("/api/config");
    if (!config.dev_mode) {
      document.querySelector(".app").innerHTML = `
        <div style="text-align:center;padding:70px 12px">
          <div style="font-size:56px">🐸</div><h1>LUDOMAN Case</h1>
          <p style="color:#9aab9b;line-height:1.6">Открой эту Mini App через Telegram, используя кнопку в боте. Для локального теста включи DEV_MODE=1 в .env.</p>
        </div>`;
      return;
    }
  }
  $("avatar").textContent = (currentUser?.first_name || "L").slice(0,1).toUpperCase();
  try {
    await loadMe();
    await loadCases();
    await loadInventory();
  } catch (e) { showToast(e.message); }
}
async function loadMe() {
  const data = await api("/api/me");
  $("balance").textContent = data.balance.toLocaleString("ru-RU");
  $("inventoryCount").textContent = data.inventory_count;
}
async function loadCases() {
  const data = await api("/api/cases");
  $("cases").innerHTML = data.cases.map(c => `
    <article class="case-card ${c.id === "daily" ? "daily" : ""}">
      <div class="case-art">${c.emoji}</div>
      <div class="case-info">
        <div class="case-title">${escapeHtml(c.name)}</div>
        <div class="case-desc">${escapeHtml(c.description)}</div>
        <div class="case-bottom">
          <div class="cost">${c.cost ? `${c.cost} 🪙` : "Бесплатно"}</div>
          <button class="primary open-btn" data-case="${c.id}">Открыть</button>
        </div>
      </div>
    </article>`).join("");
  document.querySelectorAll(".open-btn").forEach(btn => btn.addEventListener("click", () => openCase(btn.dataset.case, btn)));
}
async function openCase(caseId, button) {
  button.disabled = true;
  button.textContent = "Открываем…";
  try {
    const data = await api("/api/open", {method:"POST", body:JSON.stringify({case_id:caseId})});
    $("resultEmoji").textContent = data.reward.emoji;
    $("resultName").textContent = data.reward.name;
    $("resultRarity").textContent = data.reward.rarity;
    $("result").classList.remove("hidden");
    $("balance").textContent = data.balance.toLocaleString("ru-RU");
    await loadInventory();
    tg?.HapticFeedback?.notificationOccurred("success");
  } catch(e) {
    showToast(e.message);
    tg?.HapticFeedback?.notificationOccurred("error");
  } finally {
    button.disabled = false;
    button.textContent = "Открыть";
  }
}
async function loadInventory() {
  const data = await api("/api/inventory");
  $("inventoryCount").textContent = data.items.length;
  if (!data.items.length) {
    $("inventory").innerHTML = '<div class="empty">Пока пусто — пора открыть кейс!</div>';
    return;
  }
  $("inventory").innerHTML = data.items.map(item => `
    <div class="item">
      <div class="item-emoji">${item.emoji}</div>
      <div class="item-name">${escapeHtml(item.item_name)}</div>
      <div class="item-rarity">${escapeHtml(item.rarity)}</div>
    </div>`).join("");
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
$("resultClose").addEventListener("click", () => $("result").classList.add("hidden"));
document.querySelectorAll(".bottom-nav a").forEach(a => a.addEventListener("click", e => {
  e.preventDefault();
  document.querySelectorAll(".bottom-nav a").forEach(n => n.classList.remove("active"));
  a.classList.add("active");
  if (a.getAttribute("href") === "#inventory") $("inventory").scrollIntoView({behavior:"smooth", block:"start"});
  else if (a.getAttribute("href") === "#cases") $("cases").scrollIntoView({behavior:"smooth", block:"start"});
  else showToast("LUDOMAN Case — демо-проект");
}));
init();
