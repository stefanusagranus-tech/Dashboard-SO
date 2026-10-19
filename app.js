/* =========================================================
   DASHBOARD SO C383 — APP LOGIC v7.0 (MASTERPIECE)
   Fitur: 100% Lengkap | Zero Duplication | Optimized Lazy-Load
   ========================================================= */

// =========================================================
// 1. KONFIGURASI & CONSTANTS
// =========================================================
const CONFIG = {
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev",
    STREAMLIT_URL: "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/",
    API_KEY: "so_c383_GOfNKuPRfhhdXnGTYGBYnr5zV5kzFRkz", // API Key Terbaru
    APP_VERSION: "1.0.0",
    TARGET_SO_PERSEN: 70,
};

const BOTS = {
    yui:    { emoji: "📦", name: "Yui",    role: "Data Entry",   endpoint: "/api/yui/chat" },
    hana:   { emoji: "🌸", name: "Hana",   role: "Master Shift", endpoint: "/api/hana/chat" },
    rei:    { emoji: "📊", name: "Rei",    role: "Analisis",     endpoint: "/api/rei/chat" },
    kurumi: { emoji: "🎀", name: "Kurumi", role: "Chief",        endpoint: "/api/kurumi/chat" },
};

const AUTH_KEYS = {
    TOKEN: "so_auth_token", USER: "so_auth_user", TEMP_TOKEN: "so_temp_token", USERNAME: "so_temp_username",
};

// =========================================================
// 2. STATE & CACHE GLOBAL (Mencegah API Numpuk)
// =========================================================
const AppCache = { user: null, rekap: null, shiftHariIni: null, personil: null };

let currentBot = "yui";
let chatHistories = {};
let pinInput = "";
let exitModalShown = false;
let idleTimer = null;
let clockInterval = null;
let dashboardRefreshInterval = null;
let autoThemeEnabled = true;
let updateInfo = null;
let toastTimer = null;

// State UI per halaman
let shiftPeriod = "hari_ini", masterShiftData = [], personilData = [];
let spdListData = [], spdPeriodCurrent = "bulan_ini", spdSortValue = "tanggal_desc";
let rakListData = [], rakFilterCurrent = "semua", rakSearchQuery = "";
let topData = [], topPeriodCurrent = "bulan_ini", topSortValue = "tanggal_desc", topTabCurrent = "rak", topSearchQuery = "", topSignCurrent = "minus", topSearchTimeout = null;
let rakDetailData = [], rakDetailCurrentRak = null, rakDetailFilter = "semua", rakDetailSearchQuery = "";
let statusPeriodCurrent = "bulan_ini", currentConfirmData = null;

let _personilCache = null, _personilCacheTime = 0;
window._pendingUploadSo = null;
window._pendingSpd = null;

const IDLE_TIMEOUT = 5 * 60 * 1000;

// =========================================================
// 3. AUTH & FETCH WRAPPER
// =========================================================
function getApiKey() { return CONFIG.API_KEY; }
function getToken() { return localStorage.getItem(AUTH_KEYS.TOKEN) || ""; }
function getUser() {
    if (AppCache.user) return AppCache.user;
    try { const raw = localStorage.getItem(AUTH_KEYS.USER); AppCache.user = raw ? JSON.parse(raw) : null; return AppCache.user; } catch (e) { return null; }
}
function setAuth(token, user) {
    if (token) localStorage.setItem(AUTH_KEYS.TOKEN, token);
    if (user) { localStorage.setItem(AUTH_KEYS.USER, JSON.stringify(user)); AppCache.user = user; }
    localStorage.setItem("so_login_timestamp", Date.now().toString());
}
function clearAuth() {
    Object.values(AUTH_KEYS).forEach(k => localStorage.removeItem(k));
    localStorage.removeItem("so_logged_in"); localStorage.removeItem("so_login_timestamp");
    AppCache.user = null;
}
function isLoggedIn() { return !!getToken() && !!getUser(); }

async function apiFetch(url, options = {}) {
    const headers = { "X-API-Key": getApiKey(), ...(options.headers || {}) };
    const _token = getToken();
    if (_token) headers["Authorization"] = `Bearer ${_token}`;
    
    let _resp;
    try { _resp = await fetch(url, { ...options, headers }); } 
    catch (_err) { throw new Error("Koneksi internet bermasalah"); }

    if (_resp.status === 401) {
        let _bodyText = await _resp.text();
        let _errMsg = "";
        try { _errMsg = JSON.parse(_bodyText).detail || JSON.parse(_bodyText).message || ""; } catch (e) {}
        if (!_errMsg.toLowerCase().includes("api key")) {
            clearAuth();
            showToastMini("⚠️ Session expired. Silakan login ulang.", "error");
            setTimeout(() => showScreen("loginScreen"), 800);
        }
        return new Response(_bodyText, { status: _resp.status, headers: _resp.headers });
    }
    return _resp;
}

// =========================================================
// 4. INIT & LIFECYCLE
// =========================================================
async function initApp() {
    await showSplashScreen();
    loadChatHistories();
    autoThemeEnabled = localStorage.getItem("so_auto_theme") !== "false";
    setTheme(localStorage.getItem("so_theme") || "halloween-dark");
    updateTimeTheme();
    updateApiKeyDisplay();

    bindLoginForm(); bindPinKeypad(); bindChatInput();
    setTimeout(() => checkForUpdate(false), 3000);

    if (isLoggedIn()) {
        resetIdleTimer();
        await loadDashboardWithLoading();
    } else {
        await hideSplashScreen();
        showScreen("loginScreen");
    }
    setInterval(updateTimeTheme, 60 * 1000);
}

function showSplashScreen() {
    return new Promise(resolve => {
        const splash = document.getElementById("splashScreen"), progressBar = document.getElementById("splashProgressBar");
        if (!splash) return resolve();
        splash.classList.add("active");
        let pct = 0;
        const interval = setInterval(() => {
            pct += 25; if (progressBar) progressBar.style.width = `${pct}%`;
            if (pct >= 100) { clearInterval(interval); setTimeout(resolve, 300); }
        }, 150);
    });
}
function hideSplashScreen() {
    return new Promise(resolve => {
        const splash = document.getElementById("splashScreen"); if (!splash) return resolve();
        splash.classList.add("fade-out"); setTimeout(() => { splash.remove(); resolve(); }, 400);
    });
}

// =========================================================
// 5. AUTH LOGIC
// =========================================================
function bindLoginForm() {
    const btnSubmit = document.getElementById("loginBtnSubmit"), inputUser = document.getElementById("loginUsername"), inputPass = document.getElementById("loginPassword");
    if (inputUser) inputUser.addEventListener("keydown", (e) => { if (e.key === "Enter") inputPass?.focus(); });
    if (inputPass) inputPass.addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
    if (btnSubmit) btnSubmit.addEventListener("click", doLogin);
}

async function doLogin() {
    const inputUser = document.getElementById("loginUsername"), inputPass = document.getElementById("loginPassword"), btnSubmit = document.getElementById("loginBtnSubmit"), errEl = document.getElementById("loginError");
    const _username = (inputUser?.value || "").trim().toUpperCase(), _password = (inputPass?.value || "").trim();

    if (errEl) errEl.textContent = "";
    if (!_username || !_password) { if (errEl) errEl.textContent = "❌ Username & password wajib diisi"; return; }
    if (btnSubmit) { btnSubmit.disabled = true; btnSubmit.innerHTML = '<span class="btn-spinner"></span> Memproses...'; }

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/auth/login`, {
            method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
            body: JSON.stringify({ username: _username, password: _password, device_info: "WebView" }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Login gagal");
        localStorage.setItem(AUTH_KEYS.TEMP_TOKEN, data.temp_token); localStorage.setItem(AUTH_KEYS.USERNAME, _username);
        pinInput = ""; updatePinDisplay();
        if (document.querySelector(".pin-hint")) document.querySelector(".pin-hint").textContent = `Login sebagai: ${_username}`;
        showLoginView(false); if (inputPass) inputPass.value = "";
    } catch (err) { if (errEl) errEl.textContent = `❌ ${err.message}`; } 
    finally { if (btnSubmit) { btnSubmit.disabled = false; btnSubmit.innerHTML = "🔓 MASUK"; } }
}

function showLoginView(showLogin) {
    document.getElementById("loginFormView")?.classList.toggle("hidden", !showLogin);
    document.getElementById("pinFormView")?.classList.toggle("hidden", showLogin);
}
function bindPinKeypad() {
    document.querySelectorAll(".pin-key").forEach(btn => {
        btn.addEventListener("click", () => {
            const num = btn.getAttribute("data-num"), action = btn.getAttribute("data-action");
            if (action === "back") pinInput = pinInput.slice(0, -1);
            else if (num && pinInput.length < 6) pinInput += num;
            updatePinDisplay();
            if (pinInput.length === 6) setTimeout(verifyPin, 200);
        });
    });
}
function updatePinDisplay() { document.querySelectorAll(".pin-dot").forEach((dot, idx) => dot.classList.toggle("filled", idx < pinInput.length)); }

async function verifyPin() {
    const _tempToken = localStorage.getItem(AUTH_KEYS.TEMP_TOKEN), pinError = document.getElementById("pinError");
    if (pinError) pinError.textContent = "";
    if (!_tempToken) { if (pinError) pinError.textContent = "❌ Session hilang, ulangi login"; return; }

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/auth/verify-pin`, {
            method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
            body: JSON.stringify({ temp_token: _tempToken, pin: pinInput }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "PIN salah");
        setAuth(data.token, data.user);
        localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN); localStorage.removeItem(AUTH_KEYS.USERNAME);
        pinInput = ""; updatePinDisplay(); resetIdleTimer();
        await loadDashboardWithLoading();
    } catch (err) {
        if (pinError) pinError.textContent = `❌ ${err.message}`;
        pinInput = ""; updatePinDisplay();
        if (navigator.vibrate) navigator.vibrate(200);
    }
}

function logout() { document.getElementById("exitModal")?.classList.add("active"); exitModalShown = true; }
function closeExitModal() { document.getElementById("exitModal")?.classList.remove("active"); exitModalShown = false; pushBackGuard(); }
async function confirmLogout() {
    document.getElementById("exitModal")?.classList.remove("active");
    try { await fetch(`${CONFIG.BACKEND_URL}/api/auth/logout`, { method: "POST", headers: { "X-API-Key": getApiKey(), "Authorization": `Bearer ${getToken()}` }}); } catch (e) {}
    clearAuth(); if (idleTimer) clearTimeout(idleTimer);
    pinInput = ""; updatePinDisplay();
    if (clockInterval) clearInterval(clockInterval); stopDashboardAutoRefresh();
    showToastMini("👋 Logout berhasil!", "success");
    setTimeout(() => { showLoginView(true); showScreen("loginScreen"); pushBackGuard(); }, 300);
}

// =========================================================
// 6. DASHBOARD LOADING & NAVIGATION
// =========================================================
async function loadDashboardWithLoading() {
    const overlay = document.getElementById("dataLoadingOverlay"), statusEl = document.getElementById("dataLoadingStatus");
    if (!overlay) { showScreen("homeScreen"); startLiveClock(); loadHomeDataLazy(); startDashboardAutoRefresh(); await hideSplashScreen(); return; }

    hideSplashScreen(); await new Promise(r => setTimeout(r, 400));
    overlay.classList.add("active"); resetLoadingSteps();

    try {
        await updateLoadingStep("config", "running", "Mengecek konfigurasi...");
        await new Promise(r => setTimeout(r, 300));
        await updateLoadingStep("config", "success", "Konfigurasi OK");

        await updateLoadingStep("dashboard", "running", "Memuat dashboard...");
        await loadHomeDataLazy();
        await updateLoadingStep("dashboard", "success", "Dashboard siap");

        await updateLoadingStep("shift", "running", "Memuat jadwal shift...");
        await new Promise(r => setTimeout(r, 400));
        await updateLoadingStep("shift", "success", "Jadwal siap");

        if (statusEl) statusEl.textContent = "Siap! 🚀";
        await new Promise(r => setTimeout(r, 500));
        overlay.classList.add("fade-out"); await new Promise(r => setTimeout(r, 400)); overlay.classList.remove("active", "fade-out");
        showScreen("homeScreen"); startLiveClock(); startDashboardAutoRefresh();
    } catch (e) {
        if (statusEl) statusEl.textContent = "Error, lanjut...";
        await new Promise(r => setTimeout(r, 1000)); overlay.classList.remove("active");
        showScreen("homeScreen"); startLiveClock(); startDashboardAutoRefresh();
    }
}
function resetLoadingSteps() { document.querySelectorAll(".data-loading-step").forEach(step => { step.classList.remove("running", "success", "error"); const icon = step.querySelector(".step-icon"); if (icon) icon.textContent = "⏳"; }); }
async function updateLoadingStep(stepId, status, msg) {
    const step = document.querySelector(`.data-loading-step[data-step="${stepId}"]`); if (!step) return;
    step.classList.remove("running", "success", "error"); step.classList.add(status);
    const icon = step.querySelector(".step-icon"), text = step.querySelector(".step-text");
    if (icon) icon.textContent = status === "running" ? "⏳" : status === "success" ? "✅" : "❌";
    if (text && msg) text.textContent = msg;
}

function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    document.getElementById(screenId)?.classList.add("active");
    const bottomNav = document.getElementById("bottomNav");
    if (bottomNav) {
        bottomNav.style.display = (screenId === "loginScreen") ? "none" : "flex";
        document.querySelectorAll(".nav-item").forEach(item => { item.classList.remove("active"); item.style.color = "#a39e93"; });
        let activeId = "";
        if (screenId === "homeScreen") activeId = "navHome";
        else if (screenId === "chatScreen") activeId = "navChat";
        else if (screenId === "masterShiftScreen") activeId = "navShift";
        else if (["settingsScreen", "userManagementScreen", "profileScreen"].includes(screenId)) activeId = "navSettings";
        if (activeId) { const el = document.getElementById(activeId); if (el) { el.classList.add("active"); el.style.color = "#ff7b00"; } }
    }
}

function goToHomeScreen() { closeSidebar(); showScreen("homeScreen"); startLiveClock(); loadHomeDataLazy(); startDashboardAutoRefresh(); }
function goToChatScreen() { stopDashboardAutoRefresh(); showScreen("chatScreen"); if (!currentBot || !BOTS[currentBot]) currentBot = "yui"; switchBot(currentBot); }
async function goToSettingsScreen() { closeSidebar(); await refreshUserData(); updateSettingsUserInfo(); updateAvatarUI(); showScreen("settingsScreen"); }
function goToMasterShiftScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("masterShiftScreen"); loadShiftDataLazy(); }
function goToRakListScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("rakListScreen"); loadRakList(); }
function goToSpdListScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("spdListScreen"); loadSpdList(); }
function goToTopMinusScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("topMinusScreen"); loadTopMinus(); }
function goToStatusScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("statusScreen"); loadStatusAnalysis(); }
function goToStreamlitScreen() { closeSidebar(); showScreen("streamlitScreen"); }

// =========================================================
// 7. AUTO REFRESH & LAZY LOAD (HOME)
// =========================================================
function startDashboardAutoRefresh() {
    stopDashboardAutoRefresh();
    dashboardRefreshInterval = setInterval(() => {
        if (document.querySelector(".screen.active")?.id === "homeScreen") loadMiniDashboard();
    }, 5 * 60 * 1000);
}
function stopDashboardAutoRefresh() {
    if (dashboardRefreshInterval) { clearInterval(dashboardRefreshInterval); dashboardRefreshInterval = null; }
}

function loadHomeDataLazy() {
    if (!AppCache.user) loadUserDataIfNeeded();
    if (!AppCache.rekap) loadMiniDashboard();
    // Jadwal ditarik pas geser carousel aja (ada di event listener)
}

async function loadUserDataIfNeeded() {
    const _user = getUser();
    if (AppCache.user && _user && _user.avatar_url) { updateAvatarUI(_user); return; }
    await refreshUserData();
}

async function refreshUserData() {
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/me`, { method: "GET" });
        if (resp.ok) { const data = await resp.json(); if (data.success && data.user) { setAuth(getToken(), data.user); updateAvatarUI(data.user); } }
    } catch (e) { console.warn("Gagal refresh user", e); }
}

function updateAvatarUI(user) {
    const _user = user || getUser(); if (!_user) return;
    const inisial = (_user.nama_lengkap || _user.username || "?").substring(0, 2).toUpperCase();
    const homeAvatar = document.getElementById("homeAvatarPreview"), setAvatar = document.getElementById("settingsAvatar");
    [homeAvatar, setAvatar].forEach(el => {
        if (!el) return;
        if (_user.avatar_url) { el.style.backgroundImage = `url('${_user.avatar_url}')`; el.style.backgroundColor = "transparent"; el.textContent = ""; } 
        else { el.style.backgroundImage = "none"; el.textContent = inisial; }
    });
    const _menuAdmin = document.getElementById("menuKelolaUser");
    if (_menuAdmin) _menuAdmin.style.display = (_user.role === "admin") ? "flex" : "none";
}

async function loadMiniDashboard() {
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/rekap`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) });
        const data = await resp.json(); AppCache.rekap = data.data || data;
        const _d = AppCache.rekap;
        const totalRak = _d.total_rak || 0, totalNominal = _d.total_nominal || 0, salesPeriode = _d.sales_periode || 0;
        const totalRakMaster = 145, persenSo = (totalRak / totalRakMaster) * 100;
        const statusPersen = salesPeriode > 0 ? (Math.abs(totalNominal) / salesPeriode) * 100 : 0;
        let statusKey = "aman", statusEmoji = "✅", statusText = "AMAN", statusColor = "hijau";
        if (statusPersen > 0.15) { statusKey = "bahaya"; statusEmoji = "🚨"; statusText = "BAHAYA"; statusColor = "merah"; }
        else if (statusPersen >= 0.13) { statusKey = "waspada"; statusEmoji = "⚠️"; statusText = "WASPADA"; statusColor = "kuning"; }
        
        if (document.getElementById("statRak")) document.getElementById("statRak").textContent = `${totalRak}/${totalRakMaster}`;
        if (document.getElementById("statSpd")) document.getElementById("statSpd").textContent = formatRupiahRingkas(salesPeriode);
        if (document.getElementById("statNominal")) document.getElementById("statNominal").textContent = formatRupiahRingkas(totalNominal);
        if (document.getElementById("statusIcon")) document.getElementById("statusIcon").textContent = statusEmoji;
        if (document.getElementById("statusValue")) document.getElementById("statusValue").textContent = `${statusText} (${statusColor})`;
        if (document.getElementById("statusPercent")) document.getElementById("statusPercent").textContent = `${statusPersen.toFixed(2)}%`;
        
        const statusBar = document.getElementById("statusBar");
        if (statusBar) { statusBar.classList.remove("status-aman", "status-waspada", "status-bahaya"); statusBar.classList.add(`status-${statusKey}`); }
        if (document.getElementById("progressFill")) document.getElementById("progressFill").style.width = `${Math.min(persenSo, 100)}%`;
        if (document.getElementById("progressLabel")) document.getElementById("progressLabel").textContent = `Progress SO: ${persenSo.toFixed(1)}% dari target ${CONFIG.TARGET_SO_PERSEN}%`;

        const runningParts = [`📦 Total Rak: <b>${totalRak}/${totalRakMaster}</b>`, `💰 SPD: <b>${formatRupiahRingkas(salesPeriode)}</b>`, `📉 Nominal Adjust: <b>${formatRupiahRingkas(totalNominal)}</b>`, `📊 Status: <b>${statusEmoji} ${statusText}</b> (${statusPersen.toFixed(2)}%)`];
        startRunningText(runningParts.join("  •  ") + "  •  ");
    } catch (err) {
        if (document.getElementById("statRak")) document.getElementById("statRak").textContent = "—";
        if (document.getElementById("progressLabel")) document.getElementById("progressLabel").textContent = "Gagal load data";
        if (document.getElementById("statusValue")) document.getElementById("statusValue").textContent = "Gagal load";
        if (document.getElementById("statusPercent")) document.getElementById("statusPercent").textContent = "—%";
    }
}

async function loadHomeSchedule() {
    const container = document.getElementById("homeScheduleList"); if (!container) return;
    if (AppCache.shiftHariIni) { renderHomeSchedule(AppCache.shiftHariIni, container); return; }
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/shift-hari-ini`, { method: "GET" });
        const data = await resp.json(); AppCache.shiftHariIni = data; renderHomeSchedule(data, container);
    } catch (err) { container.innerHTML = `<p style="text-align:center; color:var(--danger);">Gagal load jadwal.</p>`; }
}

function renderHomeSchedule(data, container) {
    if (data.success && data.grouped) {
        let html = ""; const g = data.grouped;
        if (g.P7?.length) html += `<div style="margin-bottom:8px;"><b style="color:#06d6a0;">🟢 Pagi:</b> ${g.P7.join(", ")}</div>`;
        if (g.S15?.length) html += `<div style="margin-bottom:8px;"><b style="color:#feca57;">🟡 Siang:</b> ${g.S15.join(", ")}</div>`;
        if (g.M22?.length) html += `<div style="margin-bottom:8px;"><b style="color:#ee5253;">🔴 Malam:</b> ${g.M22.join(", ")}</div>`;
        if (g.O?.length) html += `<div style="margin-bottom:8px;"><b style="color:#a39e93;">⚪ Off:</b> ${g.O.join(", ")}</div>`;
        container.innerHTML = html || `<p style="text-align:center; color:var(--text-muted);">Tidak ada jadwal.</p>`;
    } else { container.innerHTML = `<p style="text-align:center; color:var(--text-muted);">Tidak ada jadwal.</p>`; }
}

// =========================================================
// 8. CAROUSEL (SINGLE EVENT LISTENER)
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
    const carousel = document.getElementById('homeCarousel');
    if (!carousel) return;
    let isScheduleLoaded = false;
    carousel.addEventListener('scroll', () => {
        const slideWidth = carousel.clientWidth + 16;
        const activeIndex = Math.round(carousel.scrollLeft / slideWidth);
        document.querySelectorAll('.carousel-dots .dot').forEach((dot, i) => dot.classList.toggle('active', i === activeIndex));
        if (activeIndex === 2 && !isScheduleLoaded) { isScheduleLoaded = true; loadHomeSchedule(); }
    });
});

function goToSlide(index) {
    const container = document.getElementById("homeCarousel"); if (!container) return;
    container.scrollTo({ left: index * (container.clientWidth + 16), behavior: "smooth" });
}

// =========================================================
// 9. DATA FETCHING LAINNYA (SHIFT, RAK, SPD, TOP, STATUS)
// =========================================================
async function loadShiftDataLazy() {
    if (!AppCache.personil) {
        try {
            const pResp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil`, { method: "GET" });
            const pData = await pResp.json(); AppCache.personil = pData.data || []; personilData = AppCache.personil;
            const filterSelect = document.getElementById("personilFilter");
            if (filterSelect) { filterSelect.innerHTML = '<option value="">👥 Semua Personil</option>'; personilData.forEach(p => filterSelect.innerHTML += `<option value="${p.nama}">👤 ${p.nama}</option>`); }
        } catch (e) {}
    } else { personilData = AppCache.personil; }
    loadMasterShift();
}

// =========================================================
// 10. HELPER FORMAT
// =========================================================
function formatRupiahRingkas(nominal) { const abs = Math.abs(nominal); if (abs >= 1_000_000_000) return (nominal / 1_000_000_000).toFixed(2) + "M"; if (abs >= 1_000_000) return (nominal / 1_000_000).toFixed(1) + "jt"; if (abs >= 1_000) return (nominal / 1_000).toFixed(0) + "rb"; return nominal.toFixed(0); }
function formatRupiahFull(nominal) { if (nominal === 0) return "Rp 0"; return `${nominal < 0 ? "-" : ""}Rp ${Math.abs(nominal).toLocaleString("id-ID")}`; }
function startRunningText(text) { const container = document.getElementById("runningTextContainer"); if (!container) return; container.innerHTML = `<div class="running-icon">📢</div><div class="running-viewport"><div class="running-track"><span class="running-inner">${text}</span><span class="running-inner">${text}</span></div></div>`; }
function showToastMini(message, type = "success") { document.querySelector(".toast-mini")?.remove(); const toast = document.createElement("div"); toast.className = `toast-mini ${type}`; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.classList.add("show"), 100); setTimeout(() => { toast.classList.remove("show"); setTimeout(() => toast.remove(), 400); }, 3000); }
function formatTime(timestamp) { if (!timestamp) return ""; const d = new Date(timestamp); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; }
function getSessionDate() { const d = new Date(); return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`; }
function formatMessage(text) { if (!text) return ""; let html = escapeHtml(text); html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>"); html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.25);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>'); html = html.replace(/^[\-\*]\s+(.+)$/gm, "• $1"); html = html.replace(/^(\d+)\.\s+(.+)$/gm, "$1. $2"); return html; }
function cleanHtmlEntities(str) { if (!str) return ""; return str.replace(/&#39;/g, "'").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&nbsp;/g, " ").replace(/&#x27;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">"); }
function escapeHtml(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }
function getWelcomeText(botId) { const welcomes = { yui: "Aku bisa:\n• Rekap SO\n• Input SO via chat / upload Excel\n• Input SPD\n• Top item", hana: "Aku bisa:\n• Cek jadwal shift\n• Update shift\n• Saran pengganti\n• Cek konflik", rei: "Aku bisa:\n• Analisis trend SO\n• LPJ & laporan\n• Prediksi\n• Insight", kurumi: "Aku bisa:\n• Rangkum laporan\n• Kirim report\n• Chat general\n• Koordinasi" }; return welcomes[botId] || ""; }

// =========================================================
// 11. THEME & SIDEBAR
// =========================================================
function toggleTheme() { setTheme(document.documentElement.getAttribute("data-theme") === "halloween-dark" ? "halloween-light" : "halloween-dark"); }
function setTheme(theme) { document.documentElement.setAttribute("data-theme", theme); localStorage.setItem("so_theme", theme); document.querySelectorAll("#themeIcon, #themeIcon2, #sidebarThemeIcon").forEach(el => el.textContent = theme === "halloween-dark" ? "🌙" : "☀️"); }
function updateTimeTheme() { if (!autoThemeEnabled) return; const hour = new Date().getHours(); document.documentElement.setAttribute("data-time-theme", hour < 11 ? "pagi" : hour < 15 ? "siang" : hour < 18 ? "sore" : "malam"); }
function toggleSidebar() { document.getElementById("sidebar")?.classList.toggle("open"); document.getElementById("sidebarOverlay")?.classList.toggle("active"); }
function closeSidebar() { document.getElementById("sidebar")?.classList.remove("open"); document.getElementById("sidebarOverlay")?.classList.remove("active"); }
function updateApiKeyDisplay() { const el = document.getElementById("settingsApiKey"); if (!el) return; const key = getApiKey(); el.textContent = key.length > 14 ? key.substring(0, 10) + "..." + key.substring(key.length - 6) : "***"; }

// =========================================================
// 12. CHAT LOGIC (FULL)
// =========================================================
function loadChatHistories() { try { chatHistories = JSON.parse(localStorage.getItem("so_chat_histories")) || {}; } catch (e) { chatHistories = {}; } Object.keys(BOTS).forEach(botId => { if (!chatHistories[botId]) chatHistories[botId] = []; }); }
function saveChatHistories() { try { localStorage.setItem("so_chat_histories", JSON.stringify(chatHistories)); } catch (e) {} }
function switchBot(botId) {
    if (!BOTS[botId]) return; currentBot = botId;
    if (document.getElementById("chatBotEmoji")) document.getElementById("chatBotEmoji").textContent = BOTS[botId].emoji;
    if (document.getElementById("chatBotName")) document.getElementById("chatBotName").textContent = BOTS[botId].name;
    document.querySelectorAll(".bot-item").forEach(item => item.classList.toggle("active", item.getAttribute("data-bot") === botId));
    renderChatHistory(); closeSidebar();
}

function renderChatHistory() {
    const container = document.getElementById("chatMessages"); if (!container) return;
    let history = chatHistories[currentBot] || [];
    if (history.length === 0) { container.innerHTML = `<div class="chat-message-wrapper ai"><div class="chat-avatar">${BOTS[currentBot].emoji}</div><div class="bubble-content ai"><div class="bubble bubble-ai bubble-welcome">Halo Bos! 👋<br>Aku <b>${BOTS[currentBot].name}</b>.<br>${getWelcomeText(currentBot)}</div></div></div>`; return; }
    container.innerHTML = "";
    let lastDate = "";
    history.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        const msgDate = new Date(msg.timestamp || Date.now()).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
        if (msgDate !== lastDate) { container.innerHTML += `<div class="chat-date-divider"><span>${msgDate}</span></div>`; lastDate = msgDate; }
        const wrapper = document.createElement("div"); wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;
        const avatar = document.createElement("div"); avatar.className = isUser ? "chat-avatar avatar-user" : "chat-avatar"; avatar.textContent = isUser ? "👤" : BOTS[currentBot].emoji;
        const bubbleContent = document.createElement("div"); bubbleContent.className = `bubble-content ${isUser ? "user" : "ai"}`;
        if (msg.isConfirm && msg.confirmData) { bubbleContent.appendChild(renderConfirmBubble(msg, idx)); } 
        else {
            const bubble = document.createElement("div"); bubble.className = `bubble bubble-${isUser ? "user" : "ai"}`;
            if (msg.isSuccess) bubble.classList.add("bubble-success"); else if (msg.isError) bubble.classList.add("bubble-error");
            if (msg.isSuccess && msg.content.includes("🌸")) bubble.innerHTML = formatSuccessMessage(msg.content); else bubble.innerHTML = formatMessage(msg.content);
            bubbleContent.appendChild(bubble);
        }
        const time = document.createElement("div"); time.className = "bubble-time"; time.textContent = formatTime(msg.timestamp);
        bubbleContent.appendChild(time); wrapper.appendChild(avatar); wrapper.appendChild(bubbleContent); container.appendChild(wrapper);
    });
    setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
}

function formatSuccessMessage(text) {
    if (!text) return ""; const lines = text.split("\n"); let html = "", inSummary = false, summaryLines = [];
    lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith("✅")) html += `<div class="success-header">${escapeHtml(trimmed)}</div>`;
        else if (trimmed.startsWith("🌸")) { inSummary = true; summaryLines = []; } 
        else if (inSummary && trimmed) summaryLines.push(trimmed);
        else if (trimmed) html += `<div style="margin-top: 4px;">${escapeHtml(trimmed)}</div>`;
    });
    if (summaryLines.length > 0) { html += `<div class="shift-summary-chat">`; summaryLines.forEach(line => { html += `<div class="shift-summary-chat-line">${escapeHtml(line)}</div>`; }); html += `</div>`; }
    return html;
}

function renderConfirmBubble(msg, idx) {
    const bubble = document.createElement("div"); bubble.className = "bubble bubble-ai bubble-confirm"; if (msg.resolved) bubble.classList.add("resolved");
    const data = msg.confirmData, items = data.items || [];
    const itemsHtml = items.slice(0, 4).map(it => `<span class="confirm-chip">👤 ${it.nama} → ${it.shift_nama || it.kode_shift}</span>`).join("");
    const moreHtml = items.length > 4 ? `<span class="confirm-chip confirm-chip-more">+${items.length - 4}</span>` : "";
    let actionsHtml = !msg.resolved ? `<div class="confirm-actions"><button class="confirm-btn confirm-btn-cancel" onclick="handleConfirmCancel(${idx})">❌ Batal</button><button class="confirm-btn confirm-btn-save" onclick="handleConfirmSave(${idx})" id="confirmBtnSave_${idx}">✅ Simpan</button></div>` : "";
    let statusHtml = msg.resolved ? (msg.resolvedStatus === "saved" ? `<div class="confirm-status confirm-status-saved">✅ Tersimpan</div>` : `<div class="confirm-status confirm-status-cancelled">❌ Dibatalkan</div>`) : "";
    bubble.innerHTML = `<div class="confirm-header"><span class="confirm-title-icon">🌸</span><span class="confirm-title">KONFIRMASI UPDATE</span><span class="confirm-date">📅 ${formatTanggalShort(data.tanggal)}</span></div><div class="confirm-chips">${itemsHtml}${moreHtml}</div>${actionsHtml}${statusHtml}`;
    return bubble;
}

function bindChatInput() {
    const input = document.getElementById("chatInput"); if (!input) return;
    input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 100) + "px"; });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
}

// =========================================================
// 13. CHAT SEND & LOGIC HANDLERS
// =========================================================
async function sendMessage() {
    const input = document.getElementById("chatInput"), sendBtn = document.getElementById("chatSend"); if (!input || !sendBtn) return;
    const text = input.value.trim(); if (!text) return;
    input.value = ""; input.style.height = "auto"; sendBtn.disabled = true;
    const _msgLower = text.toLowerCase().trim();

    // Deteksi perintah khusus
    if (_msgLower === "konfirmasi baru" || _msgLower === "ya konfirmasi") {
        if (window._pendingUploadSo) {
            window._pendingUploadSo.force_new_pic = true;
            chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }, { role: "assistant", content: `✅ Oke, PIC baru dikonfirmasi. Ketik **"simpan so"**.`, timestamp: Date.now() });
            saveChatHistories(); renderChatHistory(); scrollToBottom(); sendBtn.disabled = false; return;
        }
    }
    if (window._pendingUploadSo && (_msgLower.startsWith("tanggal") || _msgLower.startsWith("pic ") || _msgLower.includes(" pic "))) {
        const _handled = await handleTanggalPicInput(text); if (_handled) { sendBtn.disabled = false; return; }
    }
    if (_msgLower === "simpan so" || _msgLower === "save so") { await confirmSaveSo(); sendBtn.disabled = false; return; }
    if (_msgLower === "simpan spd" || _msgLower === "save spd") { await confirmSaveSpd(); sendBtn.disabled = false; return; }
    if (_msgLower === "batal" || _msgLower === "cancel") {
        if (window._pendingUploadSo) { cancelUploadSo(); sendBtn.disabled = false; return; }
        if (window._pendingSpd) { window._pendingSpd = null; chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }, { role: "assistant", content: `Oke, SPD dibatalkan.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); sendBtn.disabled = false; return; }
    }
    const _isSpdInput = currentBot === "yui" && ((_msgLower.includes("spd") || _msgLower.includes("sales")) && (_msgLower.includes("input") || _msgLower.includes("catat") || _msgLower.includes("simpan") || _msgLower.includes("tambah") || /\d{3,}/.test(_msgLower.replace(/[.,]/g, ""))));
    if (_isSpdInput) { chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); await handleSpdChat(text); sendBtn.disabled = false; return; }

    // Chat Biasa
    chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); showLoadingBubble();
    try {
        const history = chatHistories[currentBot].slice(-7, -1).filter(m => !m.isConfirm).map(m => ({ role: m.role, content: m.content }));
        const response = await apiFetch(`${CONFIG.BACKEND_URL}${BOTS[currentBot].endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, session_id: `so_${currentBot}_${getSessionDate()}`, history }) });
        hideLoadingBubble(); if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.detail || `Error ${response.status}`); }
        const data = await response.json();
        if (data.needs_confirm && data.parsed && data.parsed.items) { chatHistories[currentBot].push({ role: "assistant", content: data.text || `Oke, catat shift.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); setTimeout(() => openConfirmShiftModal({ tanggal: data.parsed.tanggal, items: data.parsed.items }), 400); }
        else { chatHistories[currentBot].push({ role: "assistant", content: data.text || "(kosong)", timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); }
    } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Error: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); }
    sendBtn.disabled = false; input.focus();
}

async function handleConfirmSave(idx) {
    const history = chatHistories[currentBot] || [], msg = history[idx]; if (!msg || !msg.confirmData) return;
    const btnSave = document.getElementById(`confirmBtnSave_${idx}`); if (btnSave) { btnSave.disabled = true; btnSave.innerHTML = '<span class="btn-spinner"></span> Menyimpan...'; }
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/save-batch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: msg.confirmData.tanggal, items: msg.confirmData.items.map(it => ({ nama: it.nama, kode_shift: it.kode_shift })) }) });
        const result = await resp.json(); if (!resp.ok || !result.success) throw new Error(result.detail || `HTTP ${resp.status}`);
        msg.resolved = true; msg.resolvedStatus = "saved"; history.push({ role: "assistant", content: `✅ ${result.saved || msg.confirmData.items.length} shift tersimpan!\n\n${getShiftSummaryText(msg.confirmData.items)}`, timestamp: Date.now(), isSuccess: true });
        saveChatHistories(); renderChatHistory(); if (document.getElementById("masterShiftScreen")?.classList.contains("active")) loadMasterShift(); showToastMini(`✅ Shift tersimpan`, "success");
    } catch (err) { msg.resolved = true; msg.resolvedStatus = "error"; history.push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); }
}
function handleConfirmCancel(idx) { const history = chatHistories[currentBot] || [], msg = history[idx]; if (!msg || !msg.confirmData) return; msg.resolved = true; msg.resolvedStatus = "cancelled"; history.push({ role: "assistant", content: `❌ Dibatalkan.`, timestamp: Date.now(), isCancel: true }); saveChatHistories(); renderChatHistory(); showToastMini("❌ Dibatalkan", "error"); }
function getShiftSummaryText(items) { const grouped = { P7: [], S15: [], M22: [], O: [], CUTI: [] }; items.forEach(it => { if (grouped[it.kode_shift]) grouped[it.kode_shift].push(it.nama); }); const lines = ["🌸 Shift terbaru:"]; if (grouped.P7.length) lines.push(`🟢 Pagi: ${grouped.P7.join(", ")}`); if (grouped.S15.length) lines.push(`🟡 Siang: ${grouped.S15.join(", ")}`); if (grouped.M22.length) lines.push(`🔴 Malam: ${grouped.M22.join(", ")}`); if (grouped.O.length) lines.push(`⚪ Off: ${grouped.O.join(", ")}`); if (grouped.CUTI.length) lines.push(`⚫ Cuti: ${grouped.CUTI.join(", ")}`); return lines.join("\n"); }

// =========================================================
// 14. LOADING BUBBLE & SCROLL
// =========================================================
function showLoadingBubble() { const container = document.getElementById("chatMessages"); if (!container) return; document.getElementById("loadingBubble")?.remove(); const el = document.createElement("div"); el.className = "bubble bubble-ai bubble-loading"; el.id = "loadingBubble"; el.innerHTML = "<span></span><span></span><span></span>"; container.appendChild(el); scrollToBottom(); }
function hideLoadingBubble() { document.getElementById("loadingBubble")?.remove(); }
function scrollToBottom(force = false) { const container = document.getElementById("chatMessages"); if (!container) return; if (force) { setTimeout(() => { container.scrollTop = container.scrollHeight; document.getElementById("scrollBottomBtn")?.classList.remove("show"); }, 50); return; } setTimeout(() => { const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100; const btn = document.getElementById("scrollBottomBtn"); if (btn) { if (isNearBottom) btn.classList.remove("show"); else btn.classList.add("show"); } }, 50); }

// =========================================================
// 15. UPLOAD SO, SPD & PARSER
// =========================================================
async function loadPersonilMaster() {
    if (_personilCache && (Date.now() - _personilCacheTime) < 5 * 60 * 1000) return _personilCache;
    try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil`, { method: "GET" }); const data = await resp.json(); _personilCache = (data.data || []).filter(p => p.aktif !== false).map(p => String(p.nama).trim().toUpperCase()); _personilCacheTime = Date.now(); return _personilCache; } catch (e) { return _personilCache || []; }
}
async function autoCorrectPic(userInput) {
    const _input = String(userInput).trim().toUpperCase(); if (!_input) return { status: "empty", pic: null, suggestions: [], original: _input };
    const _list = await loadPersonilMaster(); if (_list.length === 0) return { status: "exact", pic: _input, suggestions: [], original: _input };
    if (_list.includes(_input)) return { status: "exact", pic: _input, suggestions: [], original: _input };
    const _matches = _list.filter(p => p.startsWith(_input) || p.includes(_input) || _input.includes(p));
    if (_matches.length === 1) return { status: "corrected", pic: _matches[0], original: _input, suggestions: _matches };
    if (_matches.length > 1) return { status: "multiple", pic: null, original: _input, suggestions: _matches.slice(0, 5) };
    return { status: "not_found", pic: null, original: _input, suggestions: [] };
}
function groupItemsByRak(items) { const grouped = {}; (items || []).forEach(it => { const rak = (it.rak_id || "UNKNOWN").toUpperCase(); if (!grouped[rak]) grouped[rak] = []; grouped[rak].push(it); }); return grouped; }

async function parseTanggalPicInput(text) {
    const _lower = text.toLowerCase().trim(); const _result = { tanggal: null, pic_per_rak: null, pic_issues: [], is_new_pic: false };
    let _match = _lower.match(/tanggal\s+(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (_match) _result.tanggal = `${_match[1]}-${String(_match[2]).padStart(2,'0')}-${String(_match[3]).padStart(2,'0')}`;
    let _picRaw = {}; const _picMatch = text.match(/pic\s+(.+?)(?:\s+tanggal|$)/i);
    if (_picMatch) {
        let _picStr = _picMatch[1].trim(); const _picStrLower = _picStr.toLowerCase();
        if (_picStrLower.startsWith("semua ")) _picRaw["_ALL"] = _picStr.substring(6).trim();
        else if (_picStrLower.startsWith("baru ")) { _picRaw["_ALL"] = _picStr.substring(5).trim(); _result.is_new_pic = true; }
        else if (_picStr.includes(",")) _picStr.split(",").map(p => p.trim()).forEach(part => { const m = part.match(/^([A-Za-z0-9]+)\s*[:]?\s+(.+)$/); if (m) _picRaw[m[1].toUpperCase()] = m[2].trim(); });
        else { const _rakMatch = _picStr.match(/^([A-Za-z0-9]+)\s+(.+)$/); if (_rakMatch && /^[A-Z]{1,3}\d{1,4}$/i.test(_rakMatch[1])) _picRaw[_rakMatch[1].toUpperCase()] = _rakMatch[2].trim(); else _picRaw["_ALL"] = _picStr; }
    }
    if (Object.keys(_picRaw).length > 0) {
        _result.pic_per_rak = {};
        for (const [key, namaRaw] of Object.entries(_picRaw)) {
            const _corrected = await autoCorrectPic(namaRaw);
            if (_corrected.status === "exact") _result.pic_per_rak[key] = _corrected.pic;
            else if (_corrected.status === "corrected") { _result.pic_per_rak[key] = _corrected.pic; _result.pic_issues.push({ type: "corrected", key, original: namaRaw, corrected: _corrected.pic }); }
            else if (_corrected.status === "multiple") _result.pic_issues.push({ type: "multiple", key, original: namaRaw, suggestions: _corrected.suggestions });
            else if (_corrected.status === "not_found") _result.pic_issues.push({ type: "not_found", key, original: namaRaw, is_new: _result.is_new_pic });
        }
    }
    return _result;
}
async function handleTanggalPicInput(text) {
    const _pending = window._pendingUploadSo; if (!_pending) return false;
    const _lower = text.toLowerCase().trim(); if (!_lower.startsWith("tanggal") && !_lower.includes("pic ")) return false;
    const _parsed = await parseTanggalPicInput(text); chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }); if (_parsed.tanggal) _pending.tanggal = _parsed.tanggal;
    let _responseText = "";
    if (_parsed.pic_issues.some(i => i.type === "corrected")) { _responseText += `🔍 **Auto-correct PIC:**\n\n`; _parsed.pic_issues.filter(i => i.type === "corrected").forEach(i => { _responseText += `- "${i.original}" → **${i.corrected}** ✅\n`; }); _responseText += `\n`; }
    if (_parsed.pic_issues.some(i => i.type === "multiple")) { _responseText += `⚠️ **Nama ambigu, pilih:**\n\n`; _parsed.pic_issues.filter(i => i.type === "multiple").forEach(i => { i.suggestions.forEach(s => { _responseText += `   • \`pic ${i.key} ${s}\`\n`; }); }); chatHistories[currentBot].push({ role: "assistant", content: _responseText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return true; }
    if (_parsed.pic_issues.some(i => i.type === "not_found")) { const _notFound = _parsed.pic_issues.filter(i => i.type === "not_found"); _responseText += `⚠️ **Nama gak ada:**\n\n`; _notFound.forEach(i => { _responseText += `- "${i.original}" ❌\n`; }); _responseText += `\n**Ketik ulang:** \`pic ${_notFound[0].key} NAMA\``; chatHistories[currentBot].push({ role: "assistant", content: _responseText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return true; }
    if (_parsed.pic_per_rak && Object.keys(_parsed.pic_per_rak).length > 0) { if (_parsed.pic_per_rak["_ALL"]) { const _rakList = Object.keys(groupItemsByRak(_pending.items)); _pending.pic_per_rak = {}; _rakList.forEach(rak => { _pending.pic_per_rak[rak] = _parsed.pic_per_rak["_ALL"]; }); } else _pending.pic_per_rak = { ...(_pending.pic_per_rak || {}), ..._parsed.pic_per_rak }; }
    window._pendingUploadSo = _pending;
    const _rakList = Object.keys(groupItemsByRak(_pending.items)); const _picPerRak = _pending.pic_per_rak || {}; const _rakMissing = _rakList.filter(rak => !_picPerRak[rak]);
    _responseText += `📝 **Update konfirmasi:**\n\n`; if (_pending.tanggal) _responseText += `📅 Tanggal: ✅ **${_pending.tanggal}**\n\n`; else _responseText += `📅 Tanggal: ❌ Belum\n\n`;
    _responseText += `👤 **PIC per Rak:**\n`; _rakList.forEach(rak => { if (_picPerRak[rak]) _responseText += `   • ${rak} → **${_picPerRak[rak]}** ✅\n`; else _responseText += `   • ${rak} → ❌ belum\n`; }); _responseText += `\n`;
    if (_pending.tanggal && _rakMissing.length === 0) { _responseText += `🎉 **Lengkap!** Ketik **"simpan so"**.`; } else { _responseText += `⚠️ Masih ada yang kosong.`; }
    chatHistories[currentBot].push({ role: "assistant", content: _responseText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return true;
}

async function confirmSaveSo() {
    const _pending = window._pendingUploadSo; if (!_pending || !_pending.items) { showToastMini("❌ Gak ada data", "error"); return; }
    if (!_pending.tanggal) { showToastMini("❌ Tanggal belum!", "error"); return; }
    const _rakList = Object.keys(groupItemsByRak(_pending.items)); const _picPerRak = _pending.pic_per_rak || {}; const _rakMissing = _rakList.filter(rak => !_picPerRak[rak]);
    if (_rakMissing.length > 0) { showToastMini(`❌ PIC belum: ${_rakMissing.join(", ")}`, "error"); return; }
    const _listMaster = await loadPersonilMaster(); const _picNotInMaster = [];
    for (const rak of _rakList) { const _pic = _picPerRak[rak]; if (_pic && !_listMaster.includes(_pic) && !_picNotInMaster.includes(_pic)) _picNotInMaster.push(_pic); }
    if (_picNotInMaster.length > 0 && !_pending.force_new_pic) { let _warnText = `⚠️ **Konfirmasi PIC Baru:**\n\nNama ini gak ada di master:\n`; _picNotInMaster.forEach(p => { _warnText += `   • **${p}**\n`; }); _warnText += `\nKetik \`konfirmasi baru\` atau typo: \`pic ${_rakList[0]} NAMA_BENER\``; chatHistories[currentBot].push({ role: "assistant", content: _warnText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return; }
    chatHistories[currentBot].push({ role: "user", content: `💾 simpan so`, timestamp: Date.now() }, { role: "assistant", content: `⏳ Menyimpan...`, timestamp: Date.now(), isTemp: true }); saveChatHistories(); renderChatHistory();
    const _itemsWithPic = _pending.items.map(it => ({ ...it, pic: _picPerRak[(it.rak_id || "").toUpperCase()] || "" }));
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/save-so`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: _pending.tanggal, items: _itemsWithPic, keterangan: _pending.keterangan }) });
        const data = await resp.json(); chatHistories[currentBot] = chatHistories[currentBot].filter(m => !m.isTemp);
        if (!resp.ok || !data.success) throw new Error(data.detail || data.error || "Gagal simpan");
        const _saved = data.saved_count || 0; const _total = data.total_nominal || 0; let _picSummary = ""; Object.entries(_picPerRak).forEach(([rak, pic]) => { _picSummary += `   • **${rak}** → ${pic}\n`; });
        chatHistories[currentBot].push({ role: "assistant", content: `🎉 **Beres!**\n- 📅 Tanggal: **${_pending.tanggal}**\n- ✅ **${_saved} rak**\n- 💰 Total: **${formatRupiahFull(_total)}**\n\n**PIC:**\n${_picSummary}`, timestamp: Date.now(), isSuccess: true }); saveChatHistories(); renderChatHistory(); window._pendingUploadSo = null; if (document.getElementById("homeScreen")?.classList.contains("active")) loadMiniDashboard(); showToastMini(`✅ ${_saved} rak tersimpan`, "success");
    } catch (err) { chatHistories[currentBot] = chatHistories[currentBot].filter(m => !m.isTemp); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); }
}

async function handleChatFileUpload(file) {
    if (!file || currentBot !== "yui") return showToastMini("❌ Upload cuma di chat Yui", "error");
    chatHistories[currentBot].push({ role: "user", content: `📎 **Upload file:** ${file.name}`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showLoadingBubble();
    try {
        const formData = new FormData(); formData.append("file", file);
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/upload-so`, { method: "POST", body: formData });
        hideLoadingBubble(); if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || `HTTP ${resp.status}`);
        const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal parse");
        window._pendingUploadSo = { tanggal: data.tanggal, items: data.items, keterangan: `Upload ${file.name}`, filename: file.name };
        const _grouped = {}; (data.items || []).forEach(it => { const rak = (it.rak_id || "UNKNOWN").toUpperCase(); if (!_grouped[rak]) _grouped[rak] = []; _grouped[rak].push(it); });
        const _rakList = Object.keys(_grouped).sort(); let _previewText = ""; _rakList.forEach((rak, idx) => { _previewText += `**${idx + 1}. 🏪 ${rak}** (${_grouped[rak].length} item)\n`; });
        let _aiContent = `✅ File **${file.name}** dibaca!\n📅 Tanggal: **${data.tanggal || "❌ belum ada"}**\n🏪 Rak: **${_rakList.length}**\n📦 Item: **${data.total_items || 0}**\n\n`;
        if (!data.tanggal) _aiContent += `⚠️ **Isi tanggal:** \`tanggal 2026-10-14\`\n\n`;
        _aiContent += `⚠️ **Isi PIC:** \`pic ZAKI\` atau \`pic ${_rakList[0]} ZAKI\``;
        chatHistories[currentBot].push({ role: "assistant", content: _aiContent, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showToastMini(`✅ Item siap`, "success");
    } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); }
}
function cancelUploadSo() { window._pendingUploadSo = null; chatHistories[currentBot].push({ role: "user", content: `❌ batal`, timestamp: Date.now() }, { role: "assistant", content: `Oke, dibuang. 👍`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showToastMini("❌ Dibatalkan", "error"); }

async function handleSpdChat(text) {
    showLoadingBubble();
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/parse-spd`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
        const parse = await resp.json(); hideLoadingBubble();
        if (!parse.success || !parse.nominal) { chatHistories[currentBot].push({ role: "assistant", content: `Hmm, gak nemu nominal SPD.\nContoh: \`input spd 12.750.800\``, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return; }
        window._pendingSpd = { tanggal: parse.tanggal, nominal: parse.nominal };
        chatHistories[currentBot].push({ role: "assistant", content: `💰 **Konfirmasi Input SPD**\n📅 Tanggal: **${parse.tanggal}**\n💵 SPD: **${formatRupiahFull(parse.nominal)}**\n🎯 Budget SO (0,15%): **${formatRupiahFull(parse.nominal * 0.0015)}**\n\nKetik **"simpan spd"**.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory();
    } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Error: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); }
}
async function confirmSaveSpd() {
    const _pending = window._pendingSpd; if (!_pending) return showToastMini("❌ Gak ada SPD", "error");
    chatHistories[currentBot].push({ role: "user", content: `💾 simpan spd`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showLoadingBubble();
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/save-spd`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: _pending.tanggal, nominal: _pending.nominal, keterangan: "Input via APK" }) });
        const data = await resp.json(); hideLoadingBubble(); if (!resp.ok || !data.success) throw new Error(data.detail || data.message || "Gagal");
        chatHistories[currentBot].push({ role: "assistant", content: `✅ **SPD tersimpan!**\n📅 Tanggal: **${_pending.tanggal}**\n💰 SPD: **${formatRupiahFull(_pending.nominal)}**\n🎯 Budget SO: **${formatRupiahFull(data.budget_so)}**`, timestamp: Date.now(), isSuccess: true }); saveChatHistories(); renderChatHistory(); window._pendingSpd = null; showToastMini(`✅ SPD tersimpan`, "success");
    } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); }
}

// =========================================================
// 16. UTILITIES (THEME, CLOCK, MODAL, BACK BUTTON)
// =========================================================
function startLiveClock() { updateClock(); if (clockInterval) clearInterval(clockInterval); clockInterval = setInterval(updateClock, 1000); }
function updateClock() {
    const now = new Date(); const hh = String(now.getHours()).padStart(2, "0"); const mm = String(now.getMinutes()).padStart(2, "0");
    if (document.getElementById("clockTime")) document.getElementById("clockTime").textContent = `${hh}:${mm}`;
    const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]; const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    if (document.getElementById("clockDate")) document.getElementById("clockDate").textContent = `${hari[now.getDay()]}, ${now.getDate()} ${bulan[now.getMonth()]} ${now.getFullYear()}`;
    const hour = now.getHours(); let greeting = hour < 11 ? "Selamat Pagi 🌅" : hour < 15 ? "Selamat Siang ☀️" : hour < 18 ? "Selamat Sore 🌆" : "Selamat Malam 🌙";
    const _user = getUser(); if (document.getElementById("clockGreeting")) document.getElementById("clockGreeting").textContent = `${greeting}, ${_user?.nama_lengkap || "Bos"}!`;
}

function toggleTheme() { setTheme(document.documentElement.getAttribute("data-theme") === "halloween-dark" ? "halloween-light" : "halloween-dark"); }
function setTheme(theme) { document.documentElement.setAttribute("data-theme", theme); localStorage.setItem("so_theme", theme); document.querySelectorAll("#themeIcon, #themeIcon2, #sidebarThemeIcon").forEach(el => el.textContent = theme === "halloween-dark" ? "🌙" : "☀️"); }
function updateTimeTheme() { if (!autoThemeEnabled) return; const hour = new Date().getHours(); document.documentElement.setAttribute("data-time-theme", hour < 11 ? "pagi" : hour < 15 ? "siang" : hour < 18 ? "sore" : "malam"); }
function toggleSidebar() { document.getElementById("sidebar")?.classList.toggle("open"); document.getElementById("sidebarOverlay")?.classList.toggle("active"); }
function closeSidebar() { document.getElementById("sidebar")?.classList.remove("open"); document.getElementById("sidebarOverlay")?.classList.remove("active"); }

function formatTanggalLong(dateStr) { const d = new Date(dateStr); const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"], bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]; return `${d.getDate()} ${bulan[d.getMonth()]} ${d.getFullYear()} — ${hari[d.getDay()]}`; }
function formatTanggalShort(dateStr) { const d = new Date(dateStr), bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]; return `${d.getDate()} ${bulan[d.getMonth()]}`; }

window.addEventListener("popstate", (e) => {
    const activeScreen = document.querySelector(".screen.active"); if (!activeScreen) return;
    if (document.getElementById("sidebar")?.classList.contains("open")) { closeSidebar(); pushBackGuard(); return; }
    const modalOpen = document.querySelector(".modal-overlay.active:not(#exitModal)");
    if (modalOpen) { modalOpen.classList.remove("active"); pushBackGuard(); return; }
    if (activeScreen.id === "homeScreen" || activeScreen.id === "loginScreen") { e.preventDefault(); document.getElementById("exitModal")?.classList.add("active"); exitModalShown = true; pushBackGuard(); return; }
    e.preventDefault(); goToHomeScreen(); pushBackGuard();
});
function pushBackGuard() { try { history.pushState({ guard: true, ts: Date.now() }, "", ""); } catch (e) {} }
setTimeout(pushBackGuard, 800);

function resetIdleTimer() { if (idleTimer) clearTimeout(idleTimer); if (!isLoggedIn() || document.querySelector(".screen.active")?.id === "loginScreen") return; idleTimer = setTimeout(() => { autoLogout(); }, IDLE_TIMEOUT); }
function autoLogout() { clearAuth(); showToastMini("⏰ Idle 5 menit — auto logout", "error"); setTimeout(() => { showLoginView(true); showScreen("loginScreen"); pushBackGuard(); }, 300); }
["click", "touchstart", "keydown", "scroll"].forEach(evt => document.addEventListener(evt, resetIdleTimer, { passive: true }));

// =========================================================
// 17. KELOLA USER & MODAL (ADMIN)
// =========================================================
function openChatSelectionModal() { document.getElementById("chatModeModal").classList.add("active"); }
function closeChatModeModal() { document.getElementById("chatModeModal").classList.remove("active"); }
function selectChatMode(mode) { closeChatModeModal(); if (mode === 'bot') goToChatScreen(); else showToastMini("Fitur Room Chat segera hadir!", "error"); }

function goToProfileScreen() {
    const _user = getUser(); if (!_user) return;
    document.getElementById("editNamaLengkap").value = _user.nama_lengkap || "";
    const preview = document.getElementById("editAvatarPreview");
    if (preview) { if (_user.avatar_url) { preview.style.backgroundImage = `url(${_user.avatar_url})`; preview.textContent = ""; } else { preview.textContent = (_user.nama_lengkap || _user.username || "?").substring(0, 2).toUpperCase(); preview.style.backgroundImage = "none"; } }
    showScreen("profileScreen");
}
async function submitUpdateProfile() {
    const btn = document.getElementById("btnSaveProfile"), namaBaru = document.getElementById("editNamaLengkap").value.trim();
    if (!namaBaru) return showToastMini("❌ Nama nggak boleh kosong", "error");
    btn.disabled = true; btn.textContent = "Menyimpan...";
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/me/update`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nama_lengkap: namaBaru }) });
        const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal");
        await refreshUserData(); showToastMini("✅ Nama diupdate", "success"); goToSettingsScreen();
    } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } 
    finally { btn.disabled = false; btn.textContent = "Simpan Perubahan"; }
}
async function uploadAvatar(input) {
    const file = input.files[0]; if (!file) return;
    if (file.size > 2 * 1024 * 1024) { showToastMini("⚠️ Maksimal 2MB", "error"); input.value = ""; return; }
    if (!file.type.startsWith("image/")) { showToastMini("❌ Harus gambar", "error"); input.value = ""; return; }
    showToastMini("📸 Mengupload...", "success");
    try {
        const formData = new FormData(); formData.append("file", file);
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/me/upload-avatar`, { method: "POST", body: formData });
        const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal");
        await refreshUserData(); const _user = getUser(); const preview = document.getElementById("editAvatarPreview");
        if (preview) { preview.style.backgroundImage = `url('${_user.avatar_url}?t=${Date.now()}')`; preview.style.backgroundColor = "transparent"; preview.textContent = ""; }
        showToastMini("✅ Foto diupdate", "success");
    } catch (err) { showToastMini(`❌ ${err.message}`, "error"); }
}
function openImagePreview(url) { if (!url) return; const modal = document.getElementById("imagePreviewModal"), img = document.getElementById("imagePreviewImg"); if (modal && img) { img.src = url; modal.classList.add("active"); } }
function closeImagePreview() { document.getElementById("imagePreviewModal")?.classList.remove("active"); }

async function checkForUpdate(manual = false) {
    if (manual) showToastMini("🔍 Cek update...", "success");
    try { const resp = await fetch(`${CONFIG.BACKEND_URL}/api/config/`); const data = await resp.json(); if (data.app && isNewerVersion(data.app.latest_version, CONFIG.APP_VERSION)) { if (manual) showToastMini("✅ Update tersedia!", "success"); } } catch (e) {}
}
function isNewerVersion(latest, current) { const l = String(latest).split(".").map(Number), c = String(current).split(".").map(Number); for (let i = 0; i < 3; i++) { if ((l[i] || 0) > (c[i] || 0)) return true; if ((l[i] || 0) < (c[i] || 0)) return false; } return false; }

// User Management (Admin)
function goToUserManagementScreen() { const _user = getUser(); if (!_user || _user.role !== "admin") { showToastMini("❌ Akses ditolak. Khusus Admin.", "error"); return; } showScreen("userManagementScreen"); loadUsers(); }
async function loadUsers() {
    const container = document.getElementById("userListContainer"); if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data user...</p></div>`;
    try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users`, { method: "GET" }); if (!resp.ok) throw new Error(`HTTP ${resp.status}`); const data = await resp.json(); if (!data.success) throw new Error(data.detail || "Gagal load user"); renderUserList(data.users); } 
    catch (err) { console.error("[UserMgmt] Error:", err); container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${err.message}</p></div>`; }
}
function renderUserList(users) {
    const container = document.getElementById("userListContainer"); if (!container) return;
    if (!users || users.length === 0) { container.innerHTML = `<p style="text-align:center; padding: 20px;">Belum ada user.</p>`; return; }
    const html = users.map(u => { const isMe = u.id === getUser().id, statusClass = u.aktif ? "shift-badge-p7" : "shift-badge-m22", statusText = u.aktif ? "Aktif" : "Nonaktif"; return `<div class="rak-card" style="margin-bottom: 10px;"><div class="rak-card-header"><span class="rak-card-id">${u.username}</span><span class="shift-badge ${statusClass}">${statusText}</span></div><div class="rak-card-body"><div class="rak-card-row"><span class="rak-card-label">Nama</span><span class="rak-card-value">${u.nama_lengkap}</span></div><div class="rak-card-row"><span class="rak-card-label">Role</span><span class="rak-card-value" style="text-transform: uppercase;">${u.role}</span></div><div class="rak-card-row"><span class="rak-card-label">Last Login</span><span class="rak-card-value">${u.last_login ? formatTanggalLong(u.last_login.split('T')[0]) : "-"}</span></div>${!isMe ? `<div style="display: flex; gap: 8px; margin-top: 12px;"><button class="settings-btn" style="padding: 8px; font-size: 12px;" onclick="resetUserPin(${u.id}, '${u.username}')">🔑 Reset PIN</button><button class="settings-btn" style="padding: 8px; font-size: 12px;" onclick="resetUserPassword(${u.id}, '${u.username}')">🔒 Reset Pass</button><button class="settings-btn settings-btn-danger" style="padding: 8px; font-size: 12px;" onclick="forceLogoutUser(${u.id}, '${u.username}')">🚪 Force Out</button></div>` : `<p style="font-size: 12px; color: var(--accent-orange); margin-top: 12px; text-align: center;">(Ini akun Anda)</p>`}</div></div>`; }).join("");
    container.innerHTML = html;
}
async function resetUserPin(userId, username) {
    const newPin = prompt(`Masukkan PIN baru untuk ${username} (6 digit):`);
    if (!newPin || newPin.length !== 6 || !/^\d+$/.test(newPin)) return showToastMini("❌ PIN harus 6 digit angka", "error");
    try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users/${userId}/reset-pin`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ new_pin: newPin }) }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); showToastMini(`✅ PIN ${username} direset`, "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); }
}
async function resetUserPassword(userId, username) {
    const newPass = prompt(`Masukkan Password baru untuk ${username} (min 6 char):`);
    if (!newPass || newPass.length < 6) return showToastMini("❌ Password minimal 6 karakter", "error");
    try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users/${userId}/reset-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ new_password: newPass }) }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); showToastMini(`✅ Password ${username} direset`, "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); }
}
async function forceLogoutUser(userId, username) {
    if (!confirm(`Tendang ${username} dari semua device?`)) return;
    try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users/${userId}/force-logout`, { method: "POST" }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); showToastMini(`✅ ${username} ditendang`, "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); }
}

function openAddUserModal() { document.getElementById("newUserUsername").value = ""; document.getElementById("newUserNama").value = ""; document.getElementById("newUserPassword").value = ""; document.getElementById("newUserPin").value = "123456"; document.getElementById("newUserRole").value = "operator"; document.getElementById("addUserError").textContent = ""; document.getElementById("addUserModal").classList.add("active"); }
function closeAddUserModal() { document.getElementById("addUserModal").classList.remove("active"); }
async function submitAddUser() {
    const btn = document.getElementById("btnSaveUser"), errEl = document.getElementById("addUserError"), username = document.getElementById("newUserUsername").value.trim().toUpperCase(), nama = document.getElementById("newUserNama").value.trim(), password = document.getElementById("newUserPassword").value, pin = document.getElementById("newUserPin").value, role = document.getElementById("newUserRole").value;
    if (!username || !nama || !password) { errEl.textContent = "❌ Semua field wajib diisi!"; return; }
    btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...'; errEl.textContent = "";
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password, nama_lengkap: nama, role, pin }) });
        const data = await resp.json(); if (!resp.ok || !data.success) throw new Error(data.detail || data.error || "Gagal menambah user");
        showToastMini(`✅ User ${username} berhasil dibuat`, "success"); closeAddUserModal(); loadUsers();
    } catch (err) { console.error("[AddUser] Error:", err); errEl.textContent = `❌ ${err.message}`; } 
    finally { btn.disabled = false; btn.innerHTML = '✅ Simpan'; }
}

// =========================================================
// TAMBALAN FUNGSI YANG HILANG (FIX CRASH)
// =========================================================

// 1. Fungsi Status Rak
async function loadRakList() {
    const container = document.getElementById("rakList");
    if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data rak...</p></div>`;
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/rak-status`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load data rak");
        
        rakListData = data.list_rak || [];
        if (document.getElementById("rakSummaryTotal")) document.getElementById("rakSummaryTotal").textContent = data.total_rak;
        if (document.getElementById("rakSummarySudah")) document.getElementById("rakSummarySudah").textContent = data.sudah_so;
        if (document.getElementById("rakSummaryBelum")) document.getElementById("rakSummaryBelum").textContent = data.belum_so;
        renderRakList();
    } catch (err) { 
        container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${escapeHtml(err.message)}</p></div>`; 
    }
}

// 2. Fungsi Render Status Rak
function renderRakList() {
    const container = document.getElementById("rakList");
    if (!container) return;
    let filtered = rakListData || [];
    if (rakFilterCurrent === "sudah") filtered = filtered.filter(r => r.status === "SUDAH");
    else if (rakFilterCurrent === "belum") filtered = filtered.filter(r => r.status === "BELUM");
    if (rakSearchQuery) filtered = filtered.filter(r => (r.rak_id || "").toLowerCase().includes(rakSearchQuery) || (r.pic || "").toLowerCase().includes(rakSearchQuery));

    if (filtered.length === 0) {
        container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">🔍</span><p>Tidak ada rak yang cocok</p></div>`;
        return;
    }
    container.innerHTML = filtered.map(rak => {
        if (rak.status === "SUDAH") {
            const nominalText = formatRupiahFull(rak.nominal);
            const nominalClass = rak.nominal < 0 ? "rak-nominal-minus" : "rak-nominal-plus";
            const tglShort = rak.tgl_so ? formatTanggalShort(rak.tgl_so) : "-";
            return `<div class="rak-card rak-card-sudah"><div class="rak-card-header"><span class="rak-card-badge rak-badge-sudah">✅</span><span class="rak-card-id">${escapeHtml(rak.rak_id)}</span><span class="rak-card-status">Sudah SO</span></div><div class="rak-card-body"><div class="rak-card-row"><span class="rak-card-label">📅 Tanggal</span><span class="rak-card-value">${tglShort}</span></div><div class="rak-card-row"><span class="rak-card-label">💰 Nominal</span><span class="rak-card-value ${nominalClass}">${nominalText}</span></div><div class="rak-card-row"><span class="rak-card-label">👤 PIC</span><span class="rak-card-value">${escapeHtml(rak.pic || "-")}</span></div></div></div>`;
        } else {
            return `<div class="rak-card rak-card-belum"><div class="rak-card-header"><span class="rak-card-badge rak-badge-belum">❌</span><span class="rak-card-id">${escapeHtml(rak.rak_id)}</span><span class="rak-card-status">Belum SO</span></div></div>`;
        }
    }).join("");
}

// 3. Fungsi SPD List
async function loadSpdList() {
    const container = document.getElementById("spdList"); if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data SPD...</p></div>`;
    try {
        const today = new Date();
        let start = spdPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1);
        let end = spdPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0);
        if (spdPeriodCurrent === "custom") {
            const s = document.getElementById("spdCustomStart"), e = document.getElementById("spdCustomEnd");
            if (s && s.value) start = new Date(s.value);
            if (e && e.value) end = new Date(e.value);
        }
        const body = { mode: spdPeriodCurrent };
        if (spdPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); }
        
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/spd-list`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load SPD");
        
        spdListData = data.list_spd || [];
        if (document.getElementById("spdSummaryTotal")) document.getElementById("spdSummaryTotal").textContent = formatRupiahFull(data.total_spd || 0);
        if (document.getElementById("spdSummaryMeta")) document.getElementById("spdSummaryMeta").textContent = `📅 ${data.periode || "—"}`;
        if (document.getElementById("spdSummaryHari")) document.getElementById("spdSummaryHari").textContent = data.total_hari || 0;
        if (document.getElementById("spdSummaryAvg")) document.getElementById("spdSummaryAvg").textContent = formatRupiahFull(data.avg_spd || 0);
        
        renderSpdList();
    } catch (err) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${escapeHtml(err.message)}</p></div>`; }
}

// 4. Fungsi Render SPD List
function renderSpdList() {
    const container = document.getElementById("spdList"); if (!container) return;
    if (!spdListData || spdListData.length === 0) {
        container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">💰</span><p>Belum ada data SPD di periode ini</p></div>`;
        return;
    }
    container.innerHTML = spdListData.map(item => {
        const spdText = formatRupiahFull(item.spd);
        const deltaNominal = item.delta_nominal || 0, deltaPersen = item.delta_persen || 0, trend = item.trend || "flat";
        let deltaHtml = trend === "flat" ? `<span class="spd-delta spd-delta-flat">— Flat</span>` : `<span class="spd-delta spd-delta-${trend}">${trend === "up" ? "↑" : "↓"} ${deltaNominal >= 0 ? "+" : ""}${formatRupiahFull(deltaNominal)} (${deltaNominal >= 0 ? "+" : ""}${deltaPersen.toFixed(2)}%)</span>`;
        return `<div class="spd-item"><div class="spd-item-header"><div class="spd-item-tgl">📅 ${formatTanggalLong(item.tanggal)}</div><div class="spd-item-spd">${spdText}</div></div><div class="spd-item-delta-row">${deltaHtml}</div></div>`;
    }).join("");
}

// 5. Fungsi Top Minus
async function loadTopMinus() {
    const container = document.getElementById("topList"); if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data...</p></div>`;
    try {
        const today = new Date();
        let start = topPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1);
        let end = topPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0);
        const body = { mode: topPeriodCurrent };
        if (topPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); }
        
        let url = topTabCurrent === "rak" ? `${CONFIG.BACKEND_URL}/api/yui/top-rak` : `${CONFIG.BACKEND_URL}/api/yui/top-items-extended`;
        if (topTabCurrent === "rak") body.limit = 500; else { body.limit = null; body.search = topSearchQuery || ""; body.order_by = topSortValue; body.sign = topSignCurrent; }
        
        const resp = await apiFetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal");
        
        topData = topTabCurrent === "rak" ? (data.list_rak || []) : (data.items || []);
        if (document.getElementById("topSummaryTotal")) document.getElementById("topSummaryTotal").textContent = formatRupiahFull(data.total_nominal || 0);
        if (document.getElementById("topSummaryMeta")) document.getElementById("topSummaryMeta").textContent = `${topTabCurrent === "rak" ? data.total_rak : data.total_items} item • ${data.periode}`;
        
        if (topData.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">💰</span><p>Belum ada data.</p></div>`; return; }
        container.innerHTML = topData.map((item, idx) => `<div class="top-item-card"><div class="top-item-header"><span class="top-item-rank">#${idx + 1}</span><span class="top-item-title">${escapeHtml(item.rak_id || item.plu)}</span><span class="top-item-nominal ${item.nominal_adjust < 0 ? "top-nominal-minus" : "top-nominal-plus"}">${formatRupiahFull(item.nominal_adjust)}</span></div></div>`).join("");
    } catch (err) { container.innerHTML = `<p style="color:red;text-align:center;">Gagal: ${err.message}</p>`; }
}

// 6. Fungsi Status Analisis
async function loadStatusAnalysis() {
    try {
        const today = new Date();
        let start = statusPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1);
        let end = statusPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0);
        const body = { mode: statusPeriodCurrent };
        if (statusPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); }
        
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/status-analysis`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal");
        
        if (document.getElementById("statusBigEmoji")) document.getElementById("statusBigEmoji").textContent = data.status_emoji || "⏳";
        if (document.getElementById("statusBigLabel")) document.getElementById("statusBigLabel").textContent = data.status_label || "—";
        if (document.getElementById("statusBigPersen")) document.getElementById("statusBigPersen").textContent = `${(data.persen || 0).toFixed(3)}%`;
        if (document.getElementById("statusBigMeta")) document.getElementById("statusBigMeta").textContent = data.periode || "—";
        if (document.getElementById("metricNSB")) document.getElementById("metricNSB").textContent = formatRupiahFull(data.net_sales || 0);
        if (document.getElementById("metricAdjust")) document.getElementById("metricAdjust").textContent = formatRupiahFull(data.total_adjust || 0);
        if (document.getElementById("metricBTSB")) document.getElementById("metricBTSB").textContent = formatRupiahFull(data.btsb_rupiah || 0);
        if (document.getElementById("metricNSBPersonil")) document.getElementById("metricNSBPersonil").textContent = formatRupiahFull(data.nsb_personil || 0);
        if (document.getElementById("statusRekomendasi")) document.getElementById("statusRekomendasi").textContent = data.rekomendasi || "Tidak ada rekomendasi.";
    } catch (err) { console.error("Error Status:", err); }
}

// 7. Fungsi Master Shift
async function loadMasterShift() {
    const container = document.getElementById("shiftList"); if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat jadwal shift...</p></div>`;
    try {
        const today = new Date();
        let start = shiftPeriod === "hari_ini" ? today : new Date(today.getFullYear(), today.getMonth(), 1);
        let end = shiftPeriod === "hari_ini" ? today : new Date(today.getFullYear(), today.getMonth() + 1, 0);
        if (shiftPeriod === "minggu") { const day = today.getDay(); start = new Date(today); start.setDate(today.getDate() + (day === 0 ? -6 : 1 - day)); end = new Date(start); end.setDate(start.getDate() + 6); }
        
        const startStr = start.getFullYear() + "-" + String(start.getMonth() + 1).padStart(2, '0') + "-" + String(start.getDate()).padStart(2, '0');
        const endStr = end.getFullYear() + "-" + String(end.getMonth() + 1).padStart(2, '0') + "-" + String(end.getDate()).padStart(2, '0');
        const body = { tgl_start: startStr, tgl_end: endStr };
        
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/master-shift`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal");
        
        masterShiftData = data.data || [];
        if (masterShiftData.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><p>Belum ada data shift</p></div>`; return; }
        
        const grouped = {}; masterShiftData.forEach(r => { if (!grouped[r.tanggal]) grouped[r.tanggal] = []; grouped[r.tanggal].push(r); });
        container.innerHTML = Object.keys(grouped).sort().map(tgl => `<div class="date-group"><div class="date-group-header"><span class="date-group-date">📅 ${formatTanggalLong(tgl)}</span><span class="date-group-count">${grouped[tgl].length} orang</span></div>${grouped[tgl].map(r => `<div class="shift-row"><span class="shift-emoji">${r.shift_emoji || "❓"}</span><span class="shift-name">${r.nama}</span><span class="shift-badge ${getBadgeClass(r.kode_shift)}">${r.shift_nama || r.kode_shift}</span></div>`).join("")}</div>`).join("");
    } catch (err) { container.innerHTML = `<p style="color:red;text-align:center;">Gagal: ${err.message}</p>`; }
}

function getBadgeClass(kode) { return kode === "P7" ? "shift-badge-p7" : kode === "S15" ? "shift-badge-s15" : kode === "M22" ? "shift-badge-m22" : kode === "CUTI" ? "shift-badge-cuti" : "shift-badge-o"; }

// =========================================================
// TAMBALAN FUNGSI DARI HTML LAMA
// =========================================================

// 1. Fungsi Set Periode Shift (Biar tombol filter bisa diklik)
function setShiftPeriod(period) {
    shiftPeriod = period;
    document.querySelectorAll(".filter-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-period") === period);
    });
    const customRow = document.getElementById("customDateRow");
    if (customRow) {
        if (period === "custom") customRow.classList.remove("hidden");
        else customRow.classList.add("hidden");
    }
    loadMasterShift(); // Panggil ulang data shift
}

// 2. Fungsi Buka Streamlit di Browser
function openStreamlitInBrowser() {
    try {
        window.open(CONFIG.STREAMLIT_URL, "_blank");
    } catch (e) {
        window.location.href = CONFIG.STREAMLIT_URL;
    }
}

// 3. Fungsi Notifikasi (Placeholder sementara, biar gak error)
function goToNotificationsScreen() {
    showToastMini("🔔 Fitur Notifikasi segera hadir!", "success");
}

// 4. Tambahan buat jaga-jaga (Buka Modal Tema & Sistem)
function openThemeModal() {
    const isDark = document.documentElement.getAttribute("data-theme") === "halloween-dark";
    const pesan = isDark ? "Mode sekarang: DARK. Ganti ke LIGHT?" : "Mode sekarang: LIGHT. Ganti ke DARK?";
    if (confirm(pesan)) {
        toggleTheme();
        showToastMini("✅ Tema berhasil diubah", "success");
    }
}

function openSystemModal() {
    const aksi = prompt("Menu Sistem:\n1. Cek Update\n2. Ganti API Key\n3. Reset Semua Chat\n\nKetik angka (1/2/3):");
    if (aksi === "1") checkForUpdate(true);
    else if (aksi === "2") changeApiKey();
    else if (aksi === "3") resetAllChat();
}

function resetAllChat() {
    if (!confirm("Hapus SEMUA chat dengan 4 bot?")) return;
    Object.keys(BOTS).forEach(botId => { chatHistories[botId] = []; });
    saveChatHistories();
    showToastMini("✅ Semua chat dihapus", "success");
}

function changeApiKey() {
    const current = getApiKey();
    const newKey = prompt("Masukkan API Key baru:", current);
    if (!newKey || newKey.trim() === "") return;
    localStorage.setItem("so_api_key", newKey.trim());
    showToastMini("✅ API Key diupdate", "success");
}

// =========================================================
// TAMBALAN FUNGSI DARI HTML LAMA
// =========================================================

// 1. Fungsi Set Periode Shift (Biar tombol filter bisa diklik)
function setShiftPeriod(period) {
    shiftPeriod = period;
    document.querySelectorAll(".filter-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-period") === period);
    });
    const customRow = document.getElementById("customDateRow");
    if (customRow) {
        if (period === "custom") customRow.classList.remove("hidden");
        else customRow.classList.add("hidden");
    }
    loadMasterShift(); // Panggil ulang data shift
}

// 2. Fungsi Buka Streamlit di Browser
function openStreamlitInBrowser() {
    try {
        window.open(CONFIG.STREAMLIT_URL, "_blank");
    } catch (e) {
        window.location.href = CONFIG.STREAMLIT_URL;
    }
}

// 3. Fungsi Notifikasi (Placeholder sementara, biar gak error)
function goToNotificationsScreen() {
    showToastMini("🔔 Fitur Notifikasi segera hadir!", "success");
}

// 4. Tambahan buat jaga-jaga (Buka Modal Tema & Sistem)
function openThemeModal() {
    const isDark = document.documentElement.getAttribute("data-theme") === "halloween-dark";
    const pesan = isDark ? "Mode sekarang: DARK. Ganti ke LIGHT?" : "Mode sekarang: LIGHT. Ganti ke DARK?";
    if (confirm(pesan)) {
        toggleTheme();
        showToastMini("✅ Tema berhasil diubah", "success");
    }
}

function openSystemModal() {
    const aksi = prompt("Menu Sistem:\n1. Cek Update\n2. Ganti API Key\n3. Reset Semua Chat\n\nKetik angka (1/2/3):");
    if (aksi === "1") checkForUpdate(true);
    else if (aksi === "2") changeApiKey();
    else if (aksi === "3") resetAllChat();
}

function resetAllChat() {
    if (!confirm("Hapus SEMUA chat dengan 4 bot?")) return;
    Object.keys(BOTS).forEach(botId => { chatHistories[botId] = []; });
    saveChatHistories();
    showToastMini("✅ Semua chat dihapus", "success");
}

function changeApiKey() {
    const current = getApiKey();
    const newKey = prompt("Masukkan API Key baru:", current);
    if (!newKey || newKey.trim() === "") return;
    localStorage.setItem("so_api_key", newKey.trim());
    showToastMini("✅ API Key diupdate", "success");
}

// Boot
document.addEventListener("DOMContentLoaded", initApp);