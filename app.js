/* =========================================================
   DASHBOARD SO C383 — APP LOGIC v11.0 (PROXY EDITION)
   Semua request lewat /api/proxy, API Key 100% aman di backend
   ========================================================= */

const CONFIG = {
    // URL Berubah jadi PROXY
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev/api/proxy",
    STREAMLIT_URL: "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/",
    APP_VERSION: "1.0.0",
    TARGET_SO_PERSEN: 70,
    // API_KEY SUDAH DIHAPUS DARI SINI
};

const DEFAULT_BOTS = {
    yui:    { emoji: "📦", name: "Yui",    role: "Data Entry",   endpoint: "/yui/chat", persona: "Kamu adalah Yui, asisten data entry yang ceria dan teliti.", foto: "https://api.dicebear.com/7.x/bottts/svg?seed=Yui" },
    hana:   { emoji: "🌸", name: "Hana",   role: "Master Shift", endpoint: "/hana/chat", persona: "Kamu adalah Hana, asisten master shift yang ramah dan penuh perhatian.", foto: "https://api.dicebear.com/7.x/bottts/svg?seed=Hana" },
    rei:    { emoji: "📊", name: "Rei",    role: "Analisis",     endpoint: "/rei/chat", persona: "Kamu adalah Rei, asisten analisis data yang tajam dan berwibawa.", foto: "https://api.dicebear.com/7.x/bottts/svg?seed=Rei" },
    kurumi: { emoji: "🎀", name: "Kurumi", role: "Chief",        endpoint: "/kurumi/chat", persona: "Kamu adalah Kurumi, Chief of Staff yang profesional dan tegas.", foto: "https://api.dicebear.com/7.x/bottts/svg?seed=Kurumi" },
};

let BOTS = JSON.parse(localStorage.getItem("so_bots_custom")) || JSON.parse(JSON.stringify(DEFAULT_BOTS));

const AUTH_KEYS = { TOKEN: "so_auth_token", USER: "so_auth_user", TEMP_TOKEN: "so_temp_token", USERNAME: "so_temp_username" };
const AppCache = { user: null, rekap: null, shiftHariIni: null, personil: null };

let currentBot = "yui", chatHistories = {}, pinInput = "", exitModalShown = false, idleTimer = null, clockInterval = null, dashboardRefreshInterval = null, autoThemeEnabled = true, updateInfo = null, toastTimer = null;
let shiftPeriod = "hari_ini", masterShiftData = [], personilData = [];
let spdListData = [], spdPeriodCurrent = "bulan_ini", spdSortValue = "tanggal_desc";
let rakListData = [], rakFilterCurrent = "semua", rakSearchQuery = "";
let topData = [], topPeriodCurrent = "bulan_ini", topSortValue = "tanggal_desc", topTabCurrent = "rak", topSearchQuery = "", topSignCurrent = "minus", topSearchTimeout = null;
let rakDetailData = [], rakDetailCurrentRak = null, rakDetailFilter = "semua", rakDetailSearchQuery = "";
let statusPeriodCurrent = "bulan_ini", currentConfirmData = null;
let _personilCache = null, _personilCacheTime = 0;
window._pendingUploadSo = null; window._pendingSpd = null;
const IDLE_TIMEOUT = 5 * 60 * 1000;
let mentionActive = false;
let mentionUsers = [];

// URL BACKEND ASLI (khusus login)
const RAW_BACKEND_URL = "https://dashboard-so.fastapicloud.dev";

function getToken() { return localStorage.getItem(AUTH_KEYS.TOKEN) || ""; }
function getUser() { if (AppCache.user) return AppCache.user; try { const raw = localStorage.getItem(AUTH_KEYS.USER); AppCache.user = raw ? JSON.parse(raw) : null; return AppCache.user; } catch (e) { return null; } }
function setAuth(token, user) { if (token) localStorage.setItem(AUTH_KEYS.TOKEN, token); if (user) { localStorage.setItem(AUTH_KEYS.USER, JSON.stringify(user)); AppCache.user = user; } localStorage.setItem("so_login_timestamp", Date.now().toString()); }
function clearAuth() { Object.values(AUTH_KEYS).forEach(k => localStorage.removeItem(k)); localStorage.removeItem("so_logged_in"); localStorage.removeItem("so_login_timestamp"); AppCache.user = null; }
function isLoggedIn() { return !!getToken() && !!getUser(); }

// ✅ API FETCH TANPA API KEY (Karena Proxy yang ngurus)
async function apiFetch(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    const _token = getToken();
    if (_token) headers["Authorization"] = `Bearer ${_token}`;
    
    let _resp;
    try { _resp = await fetch(url, { ...options, headers }); } 
    catch (_err) { throw new Error("Koneksi internet bermasalah"); }
    
    // ✅ FIX 401: Auto logout kalau token expired
    if (_resp.status === 401) {
        let _bodyText = await _resp.text(); 
        let _errMsg = "";
        try { 
            const _json = JSON.parse(_bodyText);
            _errMsg = _json.detail || _json.message || ""; 
        } catch (e) {}
        
        // Kalau BUKAN API key issue, berarti token expired. Auto logout!
        if (!_errMsg.toLowerCase().includes("api key")) {
            console.warn("[Auth] 401 — Token expired, auto logout.");
            
            // 1. Stop semua interval biar gak spam request
            if (roomRefreshInterval) clearInterval(roomRefreshInterval);
            if (dashboardRefreshInterval) clearInterval(dashboardRefreshInterval);
            if (clockInterval) clearInterval(clockInterval);
            
            // 2. Hapus token
            clearAuth();
            
            // 3. Tampilkan pesan & lempar ke login
            showToastMini("⚠️ Sesi berakhir. Silakan login ulang.", "error");
            setTimeout(() => { 
                showLoginView(true); 
                showScreen("loginScreen"); 
                pushBackGuard(); 
            }, 500);
        }
        
        return new Response(_bodyText, { status: _resp.status, headers: _resp.headers });
    }
    return _resp;
}

async function initApp() {
    await showSplashScreen(); loadChatHistories();
    autoThemeEnabled = localStorage.getItem("so_auto_theme") !== "false";
    setTheme(localStorage.getItem("so_theme") || "halloween-dark");
    updateTimeTheme(); updateApiKeyDisplay();
    bindLoginForm(); bindPinKeypad(); bindChatInput();
    setTimeout(() => checkForUpdate(false), 3000);
    if (isLoggedIn()) { resetIdleTimer(); await loadDashboardWithLoading(); } 
    else { await hideSplashScreen(); showScreen("loginScreen"); }
    setInterval(updateTimeTheme, 60 * 1000);
}

function showSplashScreen() { return new Promise(resolve => { const splash = document.getElementById("splashScreen"), progressBar = document.getElementById("splashProgressBar"); if (!splash) return resolve(); splash.classList.add("active"); let pct = 0; const interval = setInterval(() => { pct += 25; if (progressBar) progressBar.style.width = `${pct}%`; if (pct >= 100) { clearInterval(interval); setTimeout(resolve, 300); } }, 150); }); }
function hideSplashScreen() { return new Promise(resolve => { const splash = document.getElementById("splashScreen"); if (!splash) return resolve(); splash.classList.add("fade-out"); setTimeout(() => { splash.remove(); resolve(); }, 400); }); }

function bindLoginForm() { const btnSubmit = document.getElementById("loginBtnSubmit"), inputUser = document.getElementById("loginUsername"), inputPass = document.getElementById("loginPassword"); if (inputUser) inputUser.addEventListener("keydown", (e) => { if (e.key === "Enter") inputPass?.focus(); }); if (inputPass) inputPass.addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); }); if (btnSubmit) btnSubmit.addEventListener("click", doLogin); }
async function doLogin() {
    const inputUser = document.getElementById("loginUsername"), inputPass = document.getElementById("loginPassword"), btnSubmit = document.getElementById("loginBtnSubmit"), errEl = document.getElementById("loginError");
    const _username = (inputUser?.value || "").trim().toUpperCase(), _password = (inputPass?.value || "").trim();
    if (errEl) errEl.textContent = "";
    if (!_username || !_password) { if (errEl) errEl.textContent = "❌ Username & password wajib diisi"; return; }
    if (btnSubmit) { btnSubmit.disabled = true; btnSubmit.innerHTML = '<span class="btn-spinner"></span> Memproses...'; }
    try {
        // ✅ LOGIN PAKE URL ASLI (Gak lewat proxy, karena gak butuh API Key)
        const resp = await fetch(`${RAW_BACKEND_URL}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: _username, password: _password, device_info: "WebView" }) });
        const data = await resp.json(); if (!resp.ok || !data.success) throw new Error(data.detail || "Login gagal");
        localStorage.setItem(AUTH_KEYS.TEMP_TOKEN, data.temp_token); localStorage.setItem(AUTH_KEYS.USERNAME, _username);
        pinInput = ""; updatePinDisplay(); if (document.querySelector(".pin-hint")) document.querySelector(".pin-hint").textContent = `Login sebagai: ${_username}`;
        showLoginView(false); if (inputPass) inputPass.value = "";
    } catch (err) { if (errEl) errEl.textContent = `❌ ${err.message}`; } finally { if (btnSubmit) { btnSubmit.disabled = false; btnSubmit.innerHTML = "🔓 MASUK"; } }
}
function showLoginView(showLogin) { document.getElementById("loginFormView")?.classList.toggle("hidden", !showLogin); document.getElementById("pinFormView")?.classList.toggle("hidden", showLogin); }
function bindPinKeypad() { document.querySelectorAll(".pin-key").forEach(btn => { btn.addEventListener("click", () => { const num = btn.getAttribute("data-num"), action = btn.getAttribute("data-action"); if (action === "back") pinInput = pinInput.slice(0, -1); else if (num && pinInput.length < 6) pinInput += num; updatePinDisplay(); if (pinInput.length === 6) setTimeout(verifyPin, 200); }); }); }
function updatePinDisplay() { document.querySelectorAll(".pin-dot").forEach((dot, idx) => dot.classList.toggle("filled", idx < pinInput.length)); }
async function verifyPin() {
    const _tempToken = localStorage.getItem(AUTH_KEYS.TEMP_TOKEN), pinError = document.getElementById("pinError"); if (pinError) pinError.textContent = ""; if (!_tempToken) { if (pinError) pinError.textContent = "❌ Session hilang, ulangi login"; return; }
    try {
        // ✅ VERIFY PIN PAKE URL ASLI
        const resp = await fetch(`${RAW_BACKEND_URL}/api/auth/verify-pin`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ temp_token: _tempToken, pin: pinInput }) });
        const data = await resp.json(); if (!resp.ok || !data.success) throw new Error(data.detail || "PIN salah");
        setAuth(data.token, data.user); localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN); localStorage.removeItem(AUTH_KEYS.USERNAME);
        pinInput = ""; updatePinDisplay(); resetIdleTimer(); await loadDashboardWithLoading();
    } catch (err) { if (pinError) pinError.textContent = `❌ ${err.message}`; pinInput = ""; updatePinDisplay(); if (navigator.vibrate) navigator.vibrate(200); }
}

function logout() { document.getElementById("exitModal")?.classList.add("active"); exitModalShown = true; }
function closeExitModal() { document.getElementById("exitModal")?.classList.remove("active"); exitModalShown = false; pushBackGuard(); }
async function confirmLogout() {
    document.getElementById("exitModal")?.classList.remove("active");
    try { await apiFetch(`${CONFIG.BACKEND_URL}/auth/logout`, { method: "POST" }); } catch (e) {}
    clearAuth(); if (idleTimer) clearTimeout(idleTimer);
    pinInput = ""; updatePinDisplay(); if (clockInterval) clearInterval(clockInterval); stopDashboardAutoRefresh();
    showToastMini("👋 Logout berhasil!", "success"); setTimeout(() => { showLoginView(true); showScreen("loginScreen"); pushBackGuard(); }, 300);
}

async function loadDashboardWithLoading() {
    const overlay = document.getElementById("dataLoadingOverlay"), statusEl = document.getElementById("dataLoadingStatus");
    if (!overlay) { showScreen("homeScreen"); startLiveClock(); loadHomeDataLazy(); startDashboardAutoRefresh(); await hideSplashScreen(); return; }
    hideSplashScreen(); await new Promise(r => setTimeout(r, 400)); overlay.classList.add("active"); resetLoadingSteps();
    try {
        await updateLoadingStep("config", "running", "Mengecek konfigurasi..."); await new Promise(r => setTimeout(r, 300)); await updateLoadingStep("config", "success", "Konfigurasi OK");
        await updateLoadingStep("dashboard", "running", "Memuat dashboard..."); await loadHomeDataLazy(); await updateLoadingStep("dashboard", "success", "Dashboard siap");
        await updateLoadingStep("shift", "running", "Memuat jadwal shift..."); await new Promise(r => setTimeout(r, 400)); await updateLoadingStep("shift", "success", "Jadwal siap");
        if (statusEl) statusEl.textContent = "Siap! 🚀"; await new Promise(r => setTimeout(r, 500)); overlay.classList.add("fade-out"); await new Promise(r => setTimeout(r, 400)); overlay.classList.remove("active", "fade-out");
        showScreen("homeScreen"); startLiveClock(); startDashboardAutoRefresh();
    } catch (e) { if (statusEl) statusEl.textContent = "Error, lanjut..."; await new Promise(r => setTimeout(r, 1000)); overlay.classList.remove("active"); showScreen("homeScreen"); startLiveClock(); startDashboardAutoRefresh(); }
}
function resetLoadingSteps() { document.querySelectorAll(".data-loading-step").forEach(step => { step.classList.remove("running", "success", "error"); const icon = step.querySelector(".step-icon"); if (icon) icon.textContent = "⏳"; }); }
async function updateLoadingStep(stepId, status, msg) { const step = document.querySelector(`.data-loading-step[data-step="${stepId}"]`); if (!step) return; step.classList.remove("running", "success", "error"); step.classList.add(status); const icon = step.querySelector(".step-icon"), text = step.querySelector(".step-text"); if (icon) icon.textContent = status === "running" ? "⏳" : status === "success" ? "✅" : "❌"; if (text && msg) text.textContent = msg; }

function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active")); document.getElementById(screenId)?.classList.add("active");
    const bottomNav = document.getElementById("bottomNav");
    if (bottomNav) {
        bottomNav.style.display = (screenId === "loginScreen") ? "none" : "flex";
        document.querySelectorAll(".nav-item").forEach(item => { item.classList.remove("active"); item.style.color = "#a39e93"; });
        let activeId = ""; if (screenId === "homeScreen") activeId = "navHome"; else if (screenId === "chatScreen") activeId = "navChat"; else if (screenId === "masterShiftScreen") activeId = "navShift"; else if (["settingsScreen", "userManagementScreen", "profileScreen"].includes(screenId)) activeId = "navSettings";
        if (activeId) { const el = document.getElementById(activeId); if (el) { el.classList.add("active"); el.style.color = "#ff7b00"; } }
    }
}
function goToHomeScreen() { 
    closeSidebar(); 
    showScreen("homeScreen"); 
    startLiveClock(); 
    loadHomeDataLazy(); 
    startDashboardAutoRefresh();
    
    startRealtimeNotifications(); // ✅ PASTIIN ADA INI
    updateNotifBadge(); 
}
function goToChatScreen() { stopDashboardAutoRefresh(); showScreen("chatScreen"); if (!currentBot || !BOTS[currentBot]) currentBot = "yui"; switchBot(currentBot); }
async function goToSettingsScreen() { closeSidebar(); await refreshUserData(); updateSettingsUserInfo(); updateAvatarUI(); showScreen("settingsScreen"); }
function goToMasterShiftScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("masterShiftScreen"); loadShiftDataLazy(); }
function goToRakListScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("rakListScreen"); loadRakList(); }
function goToSpdListScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("spdListScreen"); loadSpdList(); }
function goToTopMinusScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("topMinusScreen"); loadTopMinus(); }
function goToStatusScreen() { closeSidebar(); stopDashboardAutoRefresh(); showScreen("statusScreen"); loadStatusAnalysis(); }
function goToStreamlitScreen() { closeSidebar(); showScreen("streamlitScreen"); }

function startDashboardAutoRefresh() { stopDashboardAutoRefresh(); dashboardRefreshInterval = setInterval(() => { if (document.querySelector(".screen.active")?.id === "homeScreen") loadMiniDashboard(); }, 5 * 60 * 1000); }
function stopDashboardAutoRefresh() { if (dashboardRefreshInterval) { clearInterval(dashboardRefreshInterval); dashboardRefreshInterval = null; } }
function loadHomeDataLazy() { if (!AppCache.user) loadUserDataIfNeeded(); if (!AppCache.rekap) loadMiniDashboard(); }
async function loadUserDataIfNeeded() { const _user = getUser(); if (AppCache.user && _user && _user.avatar_url) { updateAvatarUI(_user); return; } await refreshUserData(); }
async function refreshUserData() { try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/me`, { method: "GET" }); if (resp.ok) { const data = await resp.json(); if (data.success && data.user) { setAuth(getToken(), data.user); updateAvatarUI(data.user); } } } catch (e) {} }
function updateAvatarUI(user) {
    const _user = user || getUser(); if (!_user) return; const inisial = (_user.nama_lengkap || _user.username || "?").substring(0, 2).toUpperCase();
    const homeAvatar = document.getElementById("homeAvatarPreview"), setAvatar = document.getElementById("settingsAvatar");
    [homeAvatar, setAvatar].forEach(el => { if (!el) return; if (_user.avatar_url) { el.style.backgroundImage = `url('${_user.avatar_url}')`; el.style.backgroundColor = "transparent"; el.textContent = ""; } else { el.style.backgroundImage = "none"; el.textContent = inisial; } });
    const _menuAdmin = document.getElementById("menuKelolaUser"); if (_menuAdmin) _menuAdmin.style.display = (_user.role === "admin") ? "flex" : "none";
}
function updateSettingsUserInfo() {
    const _user = getUser();
    if (document.getElementById("settingsNamaLengkap")) document.getElementById("settingsNamaLengkap").textContent = _user ? (_user.nama_lengkap || "-") : "-";
    if (document.getElementById("settingsUsername")) document.getElementById("settingsUsername").textContent = _user ? `@${_user.username}` : "-";
    if (document.getElementById("settingsRole")) document.getElementById("settingsRole").textContent = _user ? (_user.role || "-").toUpperCase() : "-";
}

async function loadMiniDashboard() {
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/rekap`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) });
        const data = await resp.json(); AppCache.rekap = data.data || data; const _d = AppCache.rekap;
        const totalRak = _d.total_rak || 0, totalNominal = _d.total_nominal || 0, salesPeriode = _d.sales_periode || 0, totalRakMaster = 145, persenSo = (totalRak / totalRakMaster) * 100;
        const statusPersen = salesPeriode > 0 ? (Math.abs(totalNominal) / salesPeriode) * 100 : 0;
        let statusKey = "aman", statusEmoji = "✅", statusText = "AMAN", statusColor = "hijau";
        if (statusPersen > 0.15) { statusKey = "bahaya"; statusEmoji = "🚨"; statusText = "BAHAYA"; statusColor = "merah"; } else if (statusPersen >= 0.13) { statusKey = "waspada"; statusEmoji = "⚠️"; statusText = "WASPADA"; statusColor = "kuning"; }
        if (document.getElementById("statRak")) document.getElementById("statRak").textContent = `${totalRak}/${totalRakMaster}`;
        if (document.getElementById("statSpd")) document.getElementById("statSpd").textContent = formatRupiahRingkas(salesPeriode);
        if (document.getElementById("statNominal")) document.getElementById("statNominal").textContent = formatRupiahRingkas(totalNominal);
        if (document.getElementById("statusIcon")) document.getElementById("statusIcon").textContent = statusEmoji;
        if (document.getElementById("statusValue")) document.getElementById("statusValue").textContent = `${statusText} (${statusColor})`;
        if (document.getElementById("statusPercent")) document.getElementById("statusPercent").textContent = `${statusPersen.toFixed(2)}%`;
        const statusBar = document.getElementById("statusBar"); if (statusBar) { statusBar.classList.remove("status-aman", "status-waspada", "status-bahaya"); statusBar.classList.add(`status-${statusKey}`); }
        if (document.getElementById("progressFill")) document.getElementById("progressFill").style.width = `${Math.min(persenSo, 100)}%`;
        if (document.getElementById("progressLabel")) document.getElementById("progressLabel").textContent = `Progress SO: ${persenSo.toFixed(1)}% dari target ${CONFIG.TARGET_SO_PERSEN}%`;
        const runningParts = [`📦 Total Rak: <b>${totalRak}/${totalRakMaster}</b>`, `💰 SPD: <b>${formatRupiahRingkas(salesPeriode)}</b>`, `📉 Nominal Adjust: <b>${formatRupiahRingkas(totalNominal)}</b>`, `📊 Status: <b>${statusEmoji} ${statusText}</b> (${statusPersen.toFixed(2)}%)`];
        startRunningText(runningParts.join("  •  ") + "  •  ");
    } catch (err) {}
}
async function loadHomeSchedule() {
    const container = document.getElementById("homeScheduleList"); if (!container) return; if (AppCache.shiftHariIni) { renderHomeSchedule(AppCache.shiftHariIni, container); return; }
    try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/shift-hari-ini`, { method: "GET" }); const data = await resp.json(); AppCache.shiftHariIni = data; renderHomeSchedule(data, container); } catch (err) { container.innerHTML = `<p style="text-align:center; color:var(--danger);">Gagal load jadwal.</p>`; }
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

document.addEventListener('DOMContentLoaded', () => {
    const carousel = document.getElementById('homeCarousel'); if (!carousel) return; let isScheduleLoaded = false;
    carousel.addEventListener('scroll', () => { const slideWidth = carousel.clientWidth + 16; const activeIndex = Math.round(carousel.scrollLeft / slideWidth); document.querySelectorAll('.carousel-dots .dot').forEach((dot, i) => dot.classList.toggle('active', i === activeIndex)); if (activeIndex === 2 && !isScheduleLoaded) { isScheduleLoaded = true; loadHomeSchedule(); } });
});
function goToSlide(index) { const container = document.getElementById("homeCarousel"); if (!container) return; container.scrollTo({ left: index * (container.clientWidth + 16), behavior: "smooth" }); }

async function loadShiftDataLazy() {
    if (!AppCache.personil) { try { const pResp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/personil`, { method: "GET" }); const pData = await pResp.json(); AppCache.personil = pData.data || []; personilData = AppCache.personil; const filterSelect = document.getElementById("personilFilter"); if (filterSelect) { filterSelect.innerHTML = '<option value="">👥 Semua Personil</option>'; personilData.forEach(p => filterSelect.innerHTML += `<option value="${p.nama}">👤 ${p.nama}</option>`); } } catch (e) {} } else { personilData = AppCache.personil; }
    loadMasterShift();
}

function formatRupiahRingkas(nominal) { const abs = Math.abs(nominal); if (abs >= 1_000_000_000) return (nominal / 1_000_000_000).toFixed(2) + "M"; if (abs >= 1_000_000) return (nominal / 1_000_000).toFixed(1) + "jt"; if (abs >= 1_000) return (nominal / 1_000).toFixed(0) + "rb"; return nominal.toFixed(0); }
function formatRupiahFull(nominal) { if (nominal === 0) return "Rp 0"; return `${nominal < 0 ? "-" : ""}Rp ${Math.abs(nominal).toLocaleString("id-ID")}`; }
function startRunningText(text) { const container = document.getElementById("runningTextContainer"); if (!container) return; container.innerHTML = `<div class="running-icon">📢</div><div class="running-viewport"><div class="running-track"><span class="running-inner">${text}</span><span class="running-inner">${text}</span></div></div>`; }
function showToastMini(message, type = "success") { document.querySelector(".toast-mini")?.remove(); const toast = document.createElement("div"); toast.className = `toast-mini ${type}`; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.classList.add("show"), 100); setTimeout(() => { toast.classList.remove("show"); setTimeout(() => toast.remove(), 400); }, 3000); }
function formatTime(timestamp) { if (!timestamp) return ""; const d = new Date(timestamp); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; }
function getSessionDate() { const d = new Date(); return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`; }
function formatMessage(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Ganti **bold** jadi <b>
    html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    // Ganti *italic* jadi <i>
    html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");
    // Ganti `code` jadi <code>
    html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.25);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');
    // Ganti list jadi bullet
    html = html.replace(/^[\-\*]\s+(.+)$/gm, "• $1");
    // Ganti newline jadi <br>
    html = html.replace(/\n/g, "<br>");
    
    // ✅ TAMBAHIN: Rapihin format SO yang berantakan
    html = html.replace(/List SO:/g, "<br><b>List SO:</b><br>");
    html = html.replace(/\s-\s(SO-\d+)/g, "<br>• $1");
    html = html.replace(/Breakdown per kategori:/g, "<br><br><b>Breakdown per kategori:</b><br>");
    
    return html;
}
function cleanHtmlEntities(str) { if (!str) return ""; return str.replace(/&#39;/g, "'").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&nbsp;/g, " ").replace(/&#x27;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">"); }
function escapeHtml(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }
function getWelcomeText(botId) { const b = BOTS[botId]; return b ? `Aku ${b.name}, ${b.role}. Siap bantu!` : ""; }

function toggleTheme() { setTheme(document.documentElement.getAttribute("data-theme") === "halloween-dark" ? "halloween-light" : "halloween-dark"); }
function setTheme(theme) { document.documentElement.setAttribute("data-theme", theme); localStorage.setItem("so_theme", theme); document.querySelectorAll("#themeIcon, #themeIcon2, #sidebarThemeIcon").forEach(el => el.textContent = theme === "halloween-dark" ? "🌙" : "☀️"); }
function updateTimeTheme() { if (!autoThemeEnabled) return; const hour = new Date().getHours(); document.documentElement.setAttribute("data-time-theme", hour < 11 ? "pagi" : hour < 15 ? "siang" : hour < 18 ? "sore" : "malam"); }
function toggleSidebar() { document.getElementById("sidebar")?.classList.toggle("open"); document.getElementById("sidebarOverlay")?.classList.toggle("active"); }
function closeSidebar() { document.getElementById("sidebar")?.classList.remove("open"); document.getElementById("sidebarOverlay")?.classList.remove("active"); }
function updateApiKeyDisplay() { const el = document.getElementById("settingsApiKey"); if (!el) return; el.textContent = "🔒 Hidden (Proxy)"; }

function loadChatHistories() { try { chatHistories = JSON.parse(localStorage.getItem("so_chat_histories")) || {}; } catch (e) { chatHistories = {}; } Object.keys(BOTS).forEach(botId => { if (!chatHistories[botId]) chatHistories[botId] = []; }); }
function saveChatHistories() { try { localStorage.setItem("so_chat_histories", JSON.stringify(chatHistories)); } catch (e) {} }
function switchBot(botId) {
    if (!BOTS[botId]) return; currentBot = botId;
    
    // ✅ FIX FOTO BOT DI HEADER
    const emojiEl = document.getElementById("chatBotEmoji");
    if (emojiEl) {
        const bot = BOTS[botId];
        if (bot.foto) {
            emojiEl.style.backgroundImage = `url('${bot.foto}')`;
            emojiEl.style.backgroundSize = "cover";
            emojiEl.style.borderRadius = "50%";
            emojiEl.style.width = "32px";
            emojiEl.style.height = "32px";
            emojiEl.textContent = "";
        } else {
            emojiEl.textContent = bot.emoji;
        }
    }
    
    if (document.getElementById("chatBotName")) document.getElementById("chatBotName").textContent = BOTS[botId].name;
    document.querySelectorAll(".bot-item").forEach(item => item.classList.toggle("active", item.getAttribute("data-bot") === botId));
    renderChatHistory(); closeSidebar();
}

function renderChatHistory() {
    const container = document.getElementById("chatMessages"); if (!container) return; let history = chatHistories[currentBot] || [];
    if (history.length === 0) { container.innerHTML = `<div class="chat-message-wrapper ai"><div class="chat-avatar">${BOTS[currentBot].emoji}</div><div class="bubble-content ai"><div class="bubble bubble-ai bubble-welcome">Halo Bos! 👋<br>Aku <b>${BOTS[currentBot].name}</b>.<br>${getWelcomeText(currentBot)}</div></div></div>`; return; }
    container.innerHTML = ""; let lastDate = "";
    const _user = getUser(); const userAvatar = _user?.avatar_url ? `background-image: url('${_user.avatar_url}'); background-size: cover; background-position: center; background-color: transparent;` : "";
    history.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        const msgDate = new Date(msg.timestamp || Date.now()).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
        if (msgDate !== lastDate) { container.innerHTML += `<div class="chat-date-divider"><span>${msgDate}</span></div>`; lastDate = msgDate; }
        const wrapper = document.createElement("div"); wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;
        const avatar = document.createElement("div"); avatar.className = isUser ? "chat-avatar avatar-user" : "chat-avatar";
        if (isUser) { if (_user?.avatar_url) { avatar.style = userAvatar; avatar.textContent = ""; } else avatar.textContent = "👤"; } 
        else { avatar.textContent = BOTS[currentBot].emoji; }
        const bubbleContent = document.createElement("div"); bubbleContent.className = `bubble-content ${isUser ? "user" : "ai"}`;
        if (msg.isConfirm && msg.confirmData) { bubbleContent.appendChild(renderConfirmBubble(msg, idx)); } else {
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

function formatSuccessMessage(text) { if (!text) return ""; const lines = text.split("\n"); let html = "", inSummary = false, summaryLines = []; lines.forEach(line => { const trimmed = line.trim(); if (trimmed.startsWith("✅")) html += `<div class="success-header">${escapeHtml(trimmed)}</div>`; else if (trimmed.startsWith("🌸")) { inSummary = true; summaryLines = []; } else if (inSummary && trimmed) summaryLines.push(trimmed); else if (trimmed) html += `<div style="margin-top: 4px;">${escapeHtml(trimmed)}</div>`; }); if (summaryLines.length > 0) { html += `<div class="shift-summary-chat">`; summaryLines.forEach(line => { html += `<div class="shift-summary-chat-line">${escapeHtml(line)}</div>`; }); html += `</div>`; } return html; }
function renderConfirmBubble(msg, idx) { const bubble = document.createElement("div"); bubble.className = "bubble bubble-ai bubble-confirm"; if (msg.resolved) bubble.classList.add("resolved"); const data = msg.confirmData, items = data.items || []; const itemsHtml = items.slice(0, 4).map(it => `<span class="confirm-chip">👤 ${it.nama} → ${it.shift_nama || it.kode_shift}</span>`).join(""); const moreHtml = items.length > 4 ? `<span class="confirm-chip confirm-chip-more">+${items.length - 4}</span>` : ""; let actionsHtml = !msg.resolved ? `<div class="confirm-actions"><button class="confirm-btn confirm-btn-cancel" onclick="handleConfirmCancel(${idx})">❌ Batal</button><button class="confirm-btn confirm-btn-save" onclick="handleConfirmSave(${idx})" id="confirmBtnSave_${idx}">✅ Simpan</button></div>` : ""; let statusHtml = msg.resolved ? (msg.resolvedStatus === "saved" ? `<div class="confirm-status confirm-status-saved">✅ Tersimpan</div>` : `<div class="confirm-status confirm-status-cancelled">❌ Dibatalkan</div>`) : ""; bubble.innerHTML = `<div class="confirm-header"><span class="confirm-title-icon">🌸</span><span class="confirm-title">KONFIRMASI UPDATE</span><span class="confirm-date">📅 ${formatTanggalShort(data.tanggal)}</span></div><div class="confirm-chips">${itemsHtml}${moreHtml}</div>${actionsHtml}${statusHtml}`; return bubble; }
function bindChatInput() { const input = document.getElementById("chatInput"); if (!input) return; input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 100) + "px"; }); input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }); }

async function sendMessage() {
    const input = document.getElementById("chatInput"), sendBtn = document.getElementById("chatSend"); if (!input || !sendBtn) return;
    const text = input.value.trim(); if (!text) return;
    input.value = ""; input.style.height = "auto"; sendBtn.disabled = true; const _msgLower = text.toLowerCase().trim();
    if (_msgLower === "konfirmasi baru" || _msgLower === "ya konfirmasi") { if (window._pendingUploadSo) { window._pendingUploadSo.force_new_pic = true; chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }, { role: "assistant", content: `✅ Oke, PIC baru dikonfirmasi. Ketik **"simpan so"**.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); sendBtn.disabled = false; return; } }
    if (window._pendingUploadSo && (_msgLower.startsWith("tanggal") || _msgLower.startsWith("pic ") || _msgLower.includes(" pic "))) { const _handled = await handleTanggalPicInput(text); if (_handled) { sendBtn.disabled = false; return; } }
    if (_msgLower === "simpan so" || _msgLower === "save so") { await confirmSaveSo(); sendBtn.disabled = false; return; }
    if (_msgLower === "simpan spd" || _msgLower === "save spd") { await confirmSaveSpd(); sendBtn.disabled = false; return; }
    if (_msgLower === "batal" || _msgLower === "cancel") { if (window._pendingUploadSo) { cancelUploadSo(); sendBtn.disabled = false; return; } if (window._pendingSpd) { window._pendingSpd = null; chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }, { role: "assistant", content: `Oke, SPD dibatalkan.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); sendBtn.disabled = false; return; } }
    const _isSpdInput = currentBot === "yui" && ((_msgLower.includes("spd") || _msgLower.includes("sales")) && (_msgLower.includes("input") || _msgLower.includes("catat") || _msgLower.includes("simpan") || _msgLower.includes("tambah") || /\d{3,}/.test(_msgLower.replace(/[.,]/g, ""))));
    if (_isSpdInput) { chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); await handleSpdChat(text); sendBtn.disabled = false; return; }

    chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); scrollToBottom(); showLoadingBubble();
    try {
        const history = chatHistories[currentBot].slice(-7, -1).filter(m => !m.isConfirm).map(m => ({ role: m.role, content: m.content }));
        const payload = { message: text, session_id: `so_${currentBot}_${getSessionDate()}`, history, custom_persona: BOTS[currentBot].persona };
        // ✅ ENDPOINT PAKE PATH PROXY (Gak ada /api/ lagi)
        const response = await apiFetch(`${CONFIG.BACKEND_URL}${BOTS[currentBot].endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        hideLoadingBubble(); if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.detail || `Error ${response.status}`); }
        const data = await response.json();
        if (data.needs_confirm && data.parsed && data.parsed.items) { chatHistories[currentBot].push({ role: "assistant", content: data.text || `Oke, catat shift.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); setTimeout(() => openConfirmShiftModal({ tanggal: data.parsed.tanggal, items: data.parsed.items }), 400); } 
        else { chatHistories[currentBot].push({ role: "assistant", content: data.text || "(kosong)", timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); }
    } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Error: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); }
    sendBtn.disabled = false; input.focus();
}

async function handleConfirmSave(idx) { const history = chatHistories[currentBot] || [], msg = history[idx]; if (!msg || !msg.confirmData) return; const btnSave = document.getElementById(`confirmBtnSave_${idx}`); if (btnSave) { btnSave.disabled = true; btnSave.innerHTML = '<span class="btn-spinner"></span> Menyimpan...'; } try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/save-batch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: msg.confirmData.tanggal, items: msg.confirmData.items.map(it => ({ nama: it.nama, kode_shift: it.kode_shift })) }) }); const result = await resp.json(); if (!resp.ok || !result.success) throw new Error(result.detail || `HTTP ${resp.status}`); msg.resolved = true; msg.resolvedStatus = "saved"; history.push({ role: "assistant", content: `✅ ${result.saved || msg.confirmData.items.length} shift tersimpan!\n\n${getShiftSummaryText(msg.confirmData.items)}`, timestamp: Date.now(), isSuccess: true }); saveChatHistories(); renderChatHistory(); if (document.getElementById("masterShiftScreen")?.classList.contains("active")) loadMasterShift(); showToastMini(`✅ Shift tersimpan`, "success"); } catch (err) { msg.resolved = true; msg.resolvedStatus = "error"; history.push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); } }
function handleConfirmCancel(idx) { const history = chatHistories[currentBot] || [], msg = history[idx]; if (!msg || !msg.confirmData) return; msg.resolved = true; msg.resolvedStatus = "cancelled"; history.push({ role: "assistant", content: `❌ Dibatalkan.`, timestamp: Date.now(), isCancel: true }); saveChatHistories(); renderChatHistory(); showToastMini("❌ Dibatalkan", "error"); }
function getShiftSummaryText(items) { const grouped = { P7: [], S15: [], M22: [], O: [], CUTI: [] }; items.forEach(it => { if (grouped[it.kode_shift]) grouped[it.kode_shift].push(it.nama); }); const lines = ["🌸 Shift terbaru:"]; if (grouped.P7.length) lines.push(`🟢 Pagi: ${grouped.P7.join(", ")}`); if (grouped.S15.length) lines.push(`🟡 Siang: ${grouped.S15.join(", ")}`); if (grouped.M22.length) lines.push(`🔴 Malam: ${grouped.M22.join(", ")}`); if (grouped.O.length) lines.push(`⚪ Off: ${grouped.O.join(", ")}`); if (grouped.CUTI.length) lines.push(`⚫ Cuti: ${grouped.CUTI.join(", ")}`); return lines.join("\n"); }

function showLoadingBubble() { const container = document.getElementById("chatMessages"); if (!container) return; document.getElementById("loadingBubble")?.remove(); const el = document.createElement("div"); el.className = "bubble bubble-ai bubble-loading"; el.id = "loadingBubble"; el.innerHTML = "<span></span><span></span><span></span>"; container.appendChild(el); scrollToBottom(); }
function hideLoadingBubble() { document.getElementById("loadingBubble")?.remove(); }
function scrollToBottom(force = false) { const container = document.getElementById("chatMessages"); if (!container) return; if (force) { setTimeout(() => { container.scrollTop = container.scrollHeight; document.getElementById("scrollBottomBtn")?.classList.remove("show"); }, 50); return; } setTimeout(() => { const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100; const btn = document.getElementById("scrollBottomBtn"); if (btn) { if (isNearBottom) btn.classList.remove("show"); else btn.classList.add("show"); } }, 50); }

async function loadPersonilMaster() { if (_personilCache && (Date.now() - _personilCacheTime) < 5 * 60 * 1000) return _personilCache; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/personil`, { method: "GET" }); const data = await resp.json(); _personilCache = (data.data || []).filter(p => p.aktif !== false).map(p => String(p.nama).trim().toUpperCase()); _personilCacheTime = Date.now(); return _personilCache; } catch (e) { return _personilCache || []; } }
async function autoCorrectPic(userInput) { const _input = String(userInput).trim().toUpperCase(); if (!_input) return { status: "empty", pic: null, suggestions: [], original: _input }; const _list = await loadPersonilMaster(); if (_list.length === 0) return { status: "exact", pic: _input, suggestions: [], original: _input }; if (_list.includes(_input)) return { status: "exact", pic: _input, suggestions: [], original: _input }; const _matches = _list.filter(p => p.startsWith(_input) || p.includes(_input) || _input.includes(p)); if (_matches.length === 1) return { status: "corrected", pic: _matches[0], original: _input, suggestions: _matches }; if (_matches.length > 1) return { status: "multiple", pic: null, original: _input, suggestions: _matches.slice(0, 5) }; return { status: "not_found", pic: null, original: _input, suggestions: [] }; }
function groupItemsByRak(items) { const grouped = {}; (items || []).forEach(it => { const rak = (it.rak_id || "UNKNOWN").toUpperCase(); if (!grouped[rak]) grouped[rak] = []; grouped[rak].push(it); }); return grouped; }
async function parseTanggalPicInput(text) { const _lower = text.toLowerCase().trim(); const _result = { tanggal: null, pic_per_rak: null, pic_issues: [], is_new_pic: false }; let _match = _lower.match(/tanggal\s+(\d{4})-(\d{1,2})-(\d{1,2})/); if (_match) _result.tanggal = `${_match[1]}-${String(_match[2]).padStart(2,'0')}-${String(_match[3]).padStart(2,'0')}`; let _picRaw = {}; const _picMatch = text.match(/pic\s+(.+?)(?:\s+tanggal|$)/i); if (_picMatch) { let _picStr = _picMatch[1].trim(); const _picStrLower = _picStr.toLowerCase(); if (_picStrLower.startsWith("semua ")) _picRaw["_ALL"] = _picStr.substring(6).trim(); else if (_picStrLower.startsWith("baru ")) { _picRaw["_ALL"] = _picStr.substring(5).trim(); _result.is_new_pic = true; } else if (_picStr.includes(",")) _picStr.split(",").map(p => p.trim()).forEach(part => { const m = part.match(/^([A-Za-z0-9]+)\s*[:]?\s+(.+)$/); if (m) _picRaw[m[1].toUpperCase()] = m[2].trim(); }); else { const _rakMatch = _picStr.match(/^([A-Za-z0-9]+)\s+(.+)$/); if (_rakMatch && /^[A-Z]{1,3}\d{1,4}$/i.test(_rakMatch[1])) _picRaw[_rakMatch[1].toUpperCase()] = _rakMatch[2].trim(); else _picRaw["_ALL"] = _picStr; } } if (Object.keys(_picRaw).length > 0) { _result.pic_per_rak = {}; for (const [key, namaRaw] of Object.entries(_picRaw)) { const _corrected = await autoCorrectPic(namaRaw); if (_corrected.status === "exact") _result.pic_per_rak[key] = _corrected.pic; else if (_corrected.status === "corrected") { _result.pic_per_rak[key] = _corrected.pic; _result.pic_issues.push({ type: "corrected", key, original: namaRaw, corrected: _corrected.pic }); } else if (_corrected.status === "multiple") _result.pic_issues.push({ type: "multiple", key, original: namaRaw, suggestions: _corrected.suggestions }); else if (_corrected.status === "not_found") _result.pic_issues.push({ type: "not_found", key, original: namaRaw, is_new: _result.is_new_pic }); } } return _result; }
async function handleTanggalPicInput(text) { const _pending = window._pendingUploadSo; if (!_pending) return false; const _lower = text.toLowerCase().trim(); if (!_lower.startsWith("tanggal") && !_lower.includes("pic ")) return false; const _parsed = await parseTanggalPicInput(text); chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() }); if (_parsed.tanggal) _pending.tanggal = _parsed.tanggal; let _responseText = ""; if (_parsed.pic_issues.some(i => i.type === "corrected")) { _responseText += `🔍 **Auto-correct PIC:**\n\n`; _parsed.pic_issues.filter(i => i.type === "corrected").forEach(i => { _responseText += `- "${i.original}" → **${i.corrected}** ✅\n`; }); _responseText += `\n`; } if (_parsed.pic_issues.some(i => i.type === "multiple")) { _responseText += `⚠️ **Nama ambigu, pilih:**\n\n`; _parsed.pic_issues.filter(i => i.type === "multiple").forEach(i => { i.suggestions.forEach(s => { _responseText += `   • \`pic ${i.key} ${s}\`\n`; }); }); chatHistories[currentBot].push({ role: "assistant", content: _responseText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return true; } if (_parsed.pic_issues.some(i => i.type === "not_found")) { const _notFound = _parsed.pic_issues.filter(i => i.type === "not_found"); _responseText += `⚠️ **Nama gak ada:**\n\n`; _notFound.forEach(i => { _responseText += `- "${i.original}" ❌\n`; }); _responseText += `\n**Ketik ulang:** \`pic ${_notFound[0].key} NAMA\``; chatHistories[currentBot].push({ role: "assistant", content: _responseText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return true; } if (_parsed.pic_per_rak && Object.keys(_parsed.pic_per_rak).length > 0) { if (_parsed.pic_per_rak["_ALL"]) { const _rakList = Object.keys(groupItemsByRak(_pending.items)); _pending.pic_per_rak = {}; _rakList.forEach(rak => { _pending.pic_per_rak[rak] = _parsed.pic_per_rak["_ALL"]; }); } else _pending.pic_per_rak = { ...(_pending.pic_per_rak || {}), ..._parsed.pic_per_rak }; } window._pendingUploadSo = _pending; const _rakList = Object.keys(groupItemsByRak(_pending.items)); const _picPerRak = _pending.pic_per_rak || {}; const _rakMissing = _rakList.filter(rak => !_picPerRak[rak]); _responseText += `📝 **Update konfirmasi:**\n\n`; if (_pending.tanggal) _responseText += `📅 Tanggal: ✅ **${_pending.tanggal}**\n\n`; else _responseText += `📅 Tanggal: ❌ Belum\n\n`; _responseText += `👤 **PIC per Rak:**\n`; _rakList.forEach(rak => { if (_picPerRak[rak]) _responseText += `   • ${rak} → **${_picPerRak[rak]}** ✅\n`; else _responseText += `   • ${rak} → ❌ belum\n`; }); _responseText += `\n`; if (_pending.tanggal && _rakMissing.length === 0) { _responseText += `🎉 **Lengkap!** Ketik **"simpan so"**.`; } else { _responseText += `⚠️ Masih ada yang kosong.`; } chatHistories[currentBot].push({ role: "assistant", content: _responseText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return true; }

async function confirmSaveSo() { const _pending = window._pendingUploadSo; if (!_pending || !_pending.items) { showToastMini("❌ Gak ada data", "error"); return; } if (!_pending.tanggal) { showToastMini("❌ Tanggal belum!", "error"); return; } const _rakList = Object.keys(groupItemsByRak(_pending.items)); const _picPerRak = _pending.pic_per_rak || {}; const _rakMissing = _rakList.filter(rak => !_picPerRak[rak]); if (_rakMissing.length > 0) { showToastMini(`❌ PIC belum: ${_rakMissing.join(", ")}`, "error"); return; } const _listMaster = await loadPersonilMaster(); const _picNotInMaster = []; for (const rak of _rakList) { const _pic = _picPerRak[rak]; if (_pic && !_listMaster.includes(_pic) && !_picNotInMaster.includes(_pic)) _picNotInMaster.push(_pic); } if (_picNotInMaster.length > 0 && !_pending.force_new_pic) { let _warnText = `⚠️ **Konfirmasi PIC Baru:**\n\nNama ini gak ada di master:\n`; _picNotInMaster.forEach(p => { _warnText += `   • **${p}**\n`; }); _warnText += `\nKetik \`konfirmasi baru\` atau typo: \`pic ${_rakList[0]} NAMA_BENER\``; chatHistories[currentBot].push({ role: "assistant", content: _warnText, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return; } chatHistories[currentBot].push({ role: "user", content: `💾 simpan so`, timestamp: Date.now() }, { role: "assistant", content: `⏳ Menyimpan...`, timestamp: Date.now(), isTemp: true }); saveChatHistories(); renderChatHistory(); const _itemsWithPic = _pending.items.map(it => ({ ...it, pic: _picPerRak[(it.rak_id || "").toUpperCase()] || "" })); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/save-so`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: _pending.tanggal, items: _itemsWithPic, keterangan: _pending.keterangan }) }); const data = await resp.json(); chatHistories[currentBot] = chatHistories[currentBot].filter(m => !m.isTemp); if (!resp.ok || !data.success) throw new Error(data.detail || data.error || "Gagal simpan"); const _saved = data.saved_count || 0; const _total = data.total_nominal || 0; let _picSummary = ""; Object.entries(_picPerRak).forEach(([rak, pic]) => { _picSummary += `   • **${rak}** → ${pic}\n`; }); chatHistories[currentBot].push({ role: "assistant", content: `🎉 **Beres!**\n- 📅 Tanggal: **${_pending.tanggal}**\n- ✅ **${_saved} rak**\n- 💰 Total: **${formatRupiahFull(_total)}**\n\n**PIC:**\n${_picSummary}`, timestamp: Date.now(), isSuccess: true }); saveChatHistories(); renderChatHistory(); window._pendingUploadSo = null; if (document.getElementById("homeScreen")?.classList.contains("active")) loadMiniDashboard(); showToastMini(`✅ ${_saved} rak tersimpan`, "success"); } catch (err) { chatHistories[currentBot] = chatHistories[currentBot].filter(m => !m.isTemp); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); } }

async function handleChatFileUpload(file) { if (!file || currentBot !== "yui") return showToastMini("❌ Upload cuma di chat Yui", "error"); chatHistories[currentBot].push({ role: "user", content: `📎 **Upload file:** ${file.name}`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showLoadingBubble(); try { const formData = new FormData(); formData.append("file", file); const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/upload-so`, { method: "POST", body: formData }); hideLoadingBubble(); if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || `HTTP ${resp.status}`); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal parse"); window._pendingUploadSo = { tanggal: data.tanggal, items: data.items, keterangan: `Upload ${file.name}`, filename: file.name }; const _grouped = {}; (data.items || []).forEach(it => { const rak = (it.rak_id || "UNKNOWN").toUpperCase(); if (!_grouped[rak]) _grouped[rak] = []; _grouped[rak].push(it); }); const _rakList = Object.keys(_grouped).sort(); let _previewText = ""; _rakList.forEach((rak, idx) => { _previewText += `**${idx + 1}. 🏪 ${rak}** (${_grouped[rak].length} item)\n`; }); let _aiContent = `✅ File **${file.name}** dibaca!\n📅 Tanggal: **${data.tanggal || "❌ belum ada"}**\n🏪 Rak: **${_rakList.length}**\n📦 Item: **${data.total_items || 0}**\n\n`; if (!data.tanggal) _aiContent += `⚠️ **Isi tanggal:** \`tanggal 2026-10-14\`\n\n`; _aiContent += `⚠️ **Isi PIC:** \`pic ZAKI\` atau \`pic ${_rakList[0]} ZAKI\``; chatHistories[currentBot].push({ role: "assistant", content: _aiContent, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showToastMini(`✅ Item siap`, "success"); } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); } }
function cancelUploadSo() { window._pendingUploadSo = null; chatHistories[currentBot].push({ role: "user", content: `❌ batal`, timestamp: Date.now() }, { role: "assistant", content: `Oke, dibuang. 👍`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showToastMini("❌ Dibatalkan", "error"); }

async function handleSpdChat(text) { showLoadingBubble(); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/parse-spd`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }); const parse = await resp.json(); hideLoadingBubble(); if (!parse.success || !parse.nominal) { chatHistories[currentBot].push({ role: "assistant", content: `Hmm, gak nemu nominal SPD.\nContoh: \`input spd 12.750.800\``, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); return; } window._pendingSpd = { tanggal: parse.tanggal, nominal: parse.nominal }; chatHistories[currentBot].push({ role: "assistant", content: `💰 **Konfirmasi Input SPD**\n📅 Tanggal: **${parse.tanggal}**\n💵 SPD: **${formatRupiahFull(parse.nominal)}**\n🎯 Budget SO (0,15%): **${formatRupiahFull(parse.nominal * 0.0015)}**\n\nKetik **"simpan spd"**.`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Error: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); } }
async function confirmSaveSpd() { const _pending = window._pendingSpd; if (!_pending) return showToastMini("❌ Gak ada SPD", "error"); chatHistories[currentBot].push({ role: "user", content: `💾 simpan spd`, timestamp: Date.now() }); saveChatHistories(); renderChatHistory(); showLoadingBubble(); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/save-spd`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: _pending.tanggal, nominal: _pending.nominal, keterangan: "Input via APK" }) }); const data = await resp.json(); hideLoadingBubble(); if (!resp.ok || !data.success) throw new Error(data.detail || data.message || "Gagal"); chatHistories[currentBot].push({ role: "assistant", content: `✅ **SPD tersimpan!**\n📅 Tanggal: **${_pending.tanggal}**\n💰 SPD: **${formatRupiahFull(_pending.nominal)}**\n🎯 Budget SO: **${formatRupiahFull(data.budget_so)}**`, timestamp: Date.now(), isSuccess: true }); saveChatHistories(); renderChatHistory(); window._pendingSpd = null; showToastMini(`✅ SPD tersimpan`, "success"); } catch (err) { hideLoadingBubble(); chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); showToastMini(`❌ Gagal`, "error"); } }

function setShiftPeriod(period) { shiftPeriod = period; document.querySelectorAll(".filter-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period)); const customRow = document.getElementById("customDateRow"); if (customRow) { if (period === "custom") customRow.classList.remove("hidden"); else customRow.classList.add("hidden"); } loadMasterShift(); }
function setRakFilter(filter) { rakFilterCurrent = filter; document.querySelectorAll(".rak-filter-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-filter") === filter)); renderRakList(); }
function filterRakList() { const input = document.getElementById("rakSearchInput"), clearBtn = document.getElementById("rakSearchClear"); if (!input) return; rakSearchQuery = input.value.trim().toLowerCase(); if (clearBtn) { if (rakSearchQuery) clearBtn.classList.remove("hidden"); else clearBtn.classList.add("hidden"); } renderRakList(); }
function clearRakSearch() { const input = document.getElementById("rakSearchInput"); if (input) input.value = ""; rakSearchQuery = ""; const clearBtn = document.getElementById("rakSearchClear"); if (clearBtn) clearBtn.classList.add("hidden"); renderRakList(); }
function setSpdPeriod(period) { spdPeriodCurrent = period; document.querySelectorAll("#spdListScreen .spd-period-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period)); const customRow = document.getElementById("spdCustomDateRow"); if (customRow) { if (period === "custom") { customRow.classList.remove("hidden"); const s = document.getElementById("spdCustomStart"), e = document.getElementById("spdCustomEnd"), today = new Date(); if (s && !s.value) s.value = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10); if (e && !e.value) e.value = today.toISOString().slice(0, 10); } else customRow.classList.add("hidden"); } loadSpdList(); }
function setSpdSort(sortValue) { spdSortValue = sortValue; document.querySelectorAll("#spdListScreen .spd-sort-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue)); loadSpdList(); }
function setTopPeriod(period) { topPeriodCurrent = period; document.querySelectorAll("#topMinusScreen .spd-period-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period)); const customRow = document.getElementById("topCustomDateRow"); if (customRow) { if (period === "custom") { customRow.classList.remove("hidden"); const s = document.getElementById("topCustomStart"), e = document.getElementById("topCustomEnd"), today = new Date(); if (s && !s.value) s.value = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10); if (e && !e.value) e.value = today.toISOString().slice(0, 10); } else customRow.classList.add("hidden"); } loadTopMinus(); }
function setTopTab(tab) { topTabCurrent = tab; document.querySelectorAll(".top-subtab").forEach(t => t.classList.toggle("active", t.getAttribute("data-tab") === tab)); const searchWrapper = document.getElementById("topSearchWrapper"), filterSign = document.getElementById("topFilterSign"); if (searchWrapper) { if (tab === "item") searchWrapper.classList.remove("hidden"); else searchWrapper.classList.add("hidden"); } if (filterSign) { if (tab === "item") filterSign.classList.remove("hidden"); else filterSign.classList.add("hidden"); } topSearchQuery = ""; const searchInput = document.getElementById("topSearchInput"); if (searchInput) searchInput.value = ""; loadTopMinus(); }
function setTopSign(sign) { topSignCurrent = sign; document.querySelectorAll(".top-filter-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sign") === sign)); loadTopMinus(); }
function setTopSort(sortValue) { topSortValue = sortValue; document.querySelectorAll("#topMinusScreen .spd-sort-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue)); loadTopMinus(); }
function searchTopItems() { const input = document.getElementById("topSearchInput"), clearBtn = document.getElementById("topSearchClear"); if (!input) return; topSearchQuery = input.value.trim(); if (clearBtn) { if (topSearchQuery) clearBtn.classList.remove("hidden"); else clearBtn.classList.add("hidden"); } clearTimeout(topSearchTimeout); topSearchTimeout = setTimeout(() => { loadTopMinus(); }, 500); }
function clearTopSearch() { const input = document.getElementById("topSearchInput"); if (input) input.value = ""; topSearchQuery = ""; const clearBtn = document.getElementById("topSearchClear"); if (clearBtn) clearBtn.classList.add("hidden"); loadTopMinus(); }
function setStatusPeriod(period) { statusPeriodCurrent = period; document.querySelectorAll("#statusScreen .spd-period-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period)); const customRow = document.getElementById("statusCustomDateRow"); if (customRow) { if (period === "custom") { customRow.classList.remove("hidden"); const s = document.getElementById("statusCustomStart"), e = document.getElementById("statusCustomEnd"), today = new Date(); if (s && !s.value) s.value = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10); if (e && !e.value) e.value = today.toISOString().slice(0, 10); } else customRow.classList.add("hidden"); } loadStatusAnalysis(); }

async function loadRakList() { const container = document.getElementById("rakList"); if (!container) return; container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data rak...</p></div>`; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/rak-status`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) }); if (!resp.ok) throw new Error(`HTTP ${resp.status}`); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal load data rak"); rakListData = data.list_rak || []; if (document.getElementById("rakSummaryTotal")) document.getElementById("rakSummaryTotal").textContent = data.total_rak; if (document.getElementById("rakSummarySudah")) document.getElementById("rakSummarySudah").textContent = data.sudah_so; if (document.getElementById("rakSummaryBelum")) document.getElementById("rakSummaryBelum").textContent = data.belum_so; renderRakList(); } catch (err) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${escapeHtml(err.message)}</p></div>`; } }
function renderRakList() { const container = document.getElementById("rakList"); if (!container) return; let filtered = rakListData || []; if (rakFilterCurrent === "sudah") filtered = filtered.filter(r => r.status === "SUDAH"); else if (rakFilterCurrent === "belum") filtered = filtered.filter(r => r.status === "BELUM"); if (rakSearchQuery) filtered = filtered.filter(r => (r.rak_id || "").toLowerCase().includes(rakSearchQuery) || (r.pic || "").toLowerCase().includes(rakSearchQuery)); if (filtered.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">🔍</span><p>Tidak ada rak yang cocok</p></div>`; return; } container.innerHTML = filtered.map(rak => { if (rak.status === "SUDAH") { const nominalText = formatRupiahFull(rak.nominal); const nominalClass = rak.nominal < 0 ? "rak-nominal-minus" : "rak-nominal-plus"; const tglShort = rak.tgl_so ? formatTanggalShort(rak.tgl_so) : "-"; return `<div class="rak-card rak-card-sudah"><div class="rak-card-header"><span class="rak-card-badge rak-badge-sudah">✅</span><span class="rak-card-id">${escapeHtml(rak.rak_id)}</span><span class="rak-card-status">Sudah SO</span></div><div class="rak-card-body"><div class="rak-card-row"><span class="rak-card-label">📅 Tanggal</span><span class="rak-card-value">${tglShort}</span></div><div class="rak-card-row"><span class="rak-card-label">💰 Nominal</span><span class="rak-card-value ${nominalClass}">${nominalText}</span></div><div class="rak-card-row"><span class="rak-card-label">👤 PIC</span><span class="rak-card-value">${escapeHtml(rak.pic || "-")}</span></div></div></div>`; } else { return `<div class="rak-card rak-card-belum"><div class="rak-card-header"><span class="rak-card-badge rak-badge-belum">❌</span><span class="rak-card-id">${escapeHtml(rak.rak_id)}</span><span class="rak-card-status">Belum SO</span></div></div>`; } }).join(""); }
async function loadSpdList() { const container = document.getElementById("spdList"); if (!container) return; container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data SPD...</p></div>`; try { const today = new Date(); let start = spdPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1); let end = spdPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0); if (spdPeriodCurrent === "custom") { const s = document.getElementById("spdCustomStart"), e = document.getElementById("spdCustomEnd"); if (s && s.value) start = new Date(s.value); if (e && e.value) end = new Date(e.value); } const body = { mode: spdPeriodCurrent }; if (spdPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); } const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/spd-list`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); if (!resp.ok) throw new Error(`HTTP ${resp.status}`); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal load SPD"); spdListData = data.list_spd || []; if (document.getElementById("spdSummaryTotal")) document.getElementById("spdSummaryTotal").textContent = formatRupiahFull(data.total_spd || 0); if (document.getElementById("spdSummaryMeta")) document.getElementById("spdSummaryMeta").textContent = `📅 ${data.periode || "—"}`; if (document.getElementById("spdSummaryHari")) document.getElementById("spdSummaryHari").textContent = data.total_hari || 0; if (document.getElementById("spdSummaryAvg")) document.getElementById("spdSummaryAvg").textContent = formatRupiahFull(data.avg_spd || 0); renderSpdList(); } catch (err) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${escapeHtml(err.message)}</p></div>`; } }
function renderSpdList() { const container = document.getElementById("spdList"); if (!container) return; if (!spdListData || spdListData.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">💰</span><p>Belum ada data SPD di periode ini</p></div>`; return; } container.innerHTML = spdListData.map(item => { const spdText = formatRupiahFull(item.spd); const deltaNominal = item.delta_nominal || 0, deltaPersen = item.delta_persen || 0, trend = item.trend || "flat"; let deltaHtml = trend === "flat" ? `<span class="spd-delta spd-delta-flat">— Flat</span>` : `<span class="spd-delta spd-delta-${trend}">${trend === "up" ? "↑" : "↓"} ${deltaNominal >= 0 ? "+" : ""}${formatRupiahFull(deltaNominal)} (${deltaNominal >= 0 ? "+" : ""}${deltaPersen.toFixed(2)}%)</span>`; return `<div class="spd-item"><div class="spd-item-header"><div class="spd-item-tgl">📅 ${formatTanggalLong(item.tanggal)}</div><div class="spd-item-spd">${spdText}</div></div><div class="spd-item-delta-row">${deltaHtml}</div></div>`; }).join(""); }
async function loadTopMinus() { const container = document.getElementById("topList"); if (!container) return; container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data...</p></div>`; try { const today = new Date(); let start = topPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1); let end = topPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0); const body = { mode: topPeriodCurrent }; if (topPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); } if (topTabCurrent === "rak") body.limit = 500; else { body.limit = null; body.search = topSearchQuery || ""; body.order_by = topSortValue; body.sign = topSignCurrent; } if (topTabCurrent === "rak") body.limit = 500; else { body.limit = null; body.search = topSearchQuery || ""; body.order_by = topSortValue; body.sign = topSignCurrent; } const resp = await apiFetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal"); topData = topTabCurrent === "rak" ? (data.list_rak || []) : (data.items || []); if (document.getElementById("topSummaryTotal")) document.getElementById("topSummaryTotal").textContent = formatRupiahFull(data.total_nominal || 0); if (document.getElementById("topSummaryMeta")) document.getElementById("topSummaryMeta").textContent = `${topTabCurrent === "rak" ? data.total_rak : data.total_items} item • ${data.periode}`; if (topData.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">💰</span><p>Belum ada data.</p></div>`; return; } container.innerHTML = topData.map((item, idx) => { const isRak = topTabCurrent === "rak"; const title = isRak ? item.rak_id : cleanHtmlEntities(item.nama_produk || item.nama || item.plu || "-"); const subTitle = isRak ? "" : `<div class="top-item-meta"><span>🏪 ${item.rak_id || "-"}</span><span>🔢 ${item.plu || "-"}</span></div>`; const nominal = item.nominal_adjust || 0; const nominalClass = nominal < 0 ? "top-nominal-minus" : "top-nominal-plus"; const clickAction = isRak ? `onclick="openRakDetail('${escapeHtml(item.rak_id)}')" style="cursor:pointer;"` : ""; return `<div class="top-item-card" ${clickAction}><div class="top-item-header"><span class="top-item-rank">#${idx + 1}</span><span class="top-item-title">${escapeHtml(title)}</span><span class="top-item-nominal ${nominalClass}">${formatRupiahFull(nominal)}</span></div>${subTitle}${isRak ? `<div class="top-item-hint">Tap untuk detail item →</div>` : ""}</div>`; }).join(""); } catch (err) { container.innerHTML = `<p style="color:red;text-align:center;">Gagal: ${err.message}</p>`; } }
async function loadStatusAnalysis() { try { const today = new Date(); let start = statusPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1); let end = statusPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0); const body = { mode: statusPeriodCurrent }; if (statusPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); } const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/status-analysis`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal"); if (document.getElementById("statusBigEmoji")) document.getElementById("statusBigEmoji").textContent = data.status_emoji || "⏳"; if (document.getElementById("statusBigLabel")) document.getElementById("statusBigLabel").textContent = data.status_label || "—"; if (document.getElementById("statusBigPersen")) document.getElementById("statusBigPersen").textContent = `${(data.persen || 0).toFixed(3)}%`; if (document.getElementById("statusBigMeta")) document.getElementById("statusBigMeta").textContent = data.periode || "—"; if (document.getElementById("metricNSB")) document.getElementById("metricNSB").textContent = formatRupiahFull(data.net_sales || 0); if (document.getElementById("metricAdjust")) document.getElementById("metricAdjust").textContent = formatRupiahFull(data.total_adjust || 0); if (document.getElementById("metricBTSB")) document.getElementById("metricBTSB").textContent = formatRupiahFull(data.btsb_rupiah || 0); if (document.getElementById("metricNSBPersonil")) document.getElementById("metricNSBPersonil").textContent = formatRupiahFull(data.nsb_personil || 0); if (document.getElementById("statusRekomendasi")) document.getElementById("statusRekomendasi").textContent = data.rekomendasi || "Tidak ada rekomendasi."; } catch (err) { console.error("Error Status:", err); } }

async function openRakDetail(rakId) { if (!rakId) return; rakDetailCurrentRak = rakId; rakDetailFilter = "semua"; rakDetailSearchQuery = ""; rakDetailData = []; const titleEl = document.getElementById("rakDetailTitle"); if (titleEl) titleEl.textContent = `Detail ${rakId}`; document.querySelectorAll(".rak-detail-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-filter") === "semua")); const searchInput = document.getElementById("rakDetailSearchInput"); if (searchInput) searchInput.value = ""; const clearBtn = document.getElementById("rakDetailSearchClear"); if (clearBtn) clearBtn.classList.add("hidden"); showScreen("rakDetailScreen"); const container = document.getElementById("rakDetailList"); if (!container) return; container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat item...</p></div>`; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/items-by-rak/${encodeURIComponent(rakId)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) }); if (!resp.ok) throw new Error(`HTTP ${resp.status}`); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal load data"); rakDetailData = data.items || []; if (document.getElementById("rakDetailInfoRak")) document.getElementById("rakDetailInfoRak").textContent = data.rak_id || "-"; if (document.getElementById("rakDetailInfoTgl")) document.getElementById("rakDetailInfoTgl").textContent = data.tgl_so ? formatTanggalLong(data.tgl_so) : "-"; if (document.getElementById("rakDetailInfoPic")) document.getElementById("rakDetailInfoPic").textContent = data.pic || "-"; if (document.getElementById("rakDetailStatMinus")) document.getElementById("rakDetailStatMinus").textContent = formatRupiahFull(data.total_minus || 0); if (document.getElementById("rakDetailStatPlus")) document.getElementById("rakDetailStatPlus").textContent = formatRupiahFull(data.total_plus || 0); if (document.getElementById("rakDetailStatNet")) document.getElementById("rakDetailStatNet").textContent = formatRupiahFull(data.total_nominal || 0); renderRakDetailList(); } catch (err) { container.innerHTML = `<p style="color:red;text-align:center;">Gagal: ${err.message}</p>`; } }
function renderRakDetailList() { const container = document.getElementById("rakDetailList"); if (!container) return; let filtered = [...(rakDetailData || [])]; if (rakDetailFilter === "minus") filtered = filtered.filter(it => (it.nominal_adjust || 0) < 0); else if (rakDetailFilter === "plus") filtered = filtered.filter(it => (it.nominal_adjust || 0) > 0); if (rakDetailSearchQuery) { filtered = filtered.filter(it => (it.plu || "").toLowerCase().includes(rakDetailSearchQuery) || (it.nama_produk || "").toLowerCase().includes(rakDetailSearchQuery)); } if (filtered.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><p>Tidak ada item.</p></div>`; return; } container.innerHTML = filtered.map((item, idx) => { const nominal = item.nominal_adjust || 0; const nominalClass = nominal < 0 ? "top-nominal-minus" : "top-nominal-plus"; return `<div class="rak-detail-item"><div class="rak-detail-item-header"><span class="rak-detail-item-rank">${idx + 1}</span><span class="rak-detail-item-plu">${item.plu}</span><span class="top-item-nominal ${nominalClass}">${formatRupiahFull(nominal)}</span></div><div class="rak-detail-item-name">${item.nama_produk || "-"}</div></div>`; }).join(""); }
function setRakDetailFilter(filter) { rakDetailFilter = filter; document.querySelectorAll(".rak-detail-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-filter") === filter)); renderRakDetailList(); }
function filterRakDetail() { const input = document.getElementById("rakDetailSearchInput"), clearBtn = document.getElementById("rakDetailSearchClear"); if (!input) return; rakDetailSearchQuery = input.value.trim().toLowerCase(); if (clearBtn) { if (rakDetailSearchQuery) clearBtn.classList.remove("hidden"); else clearBtn.classList.add("hidden"); } renderRakDetailList(); }
function clearRakDetailSearch() { const input = document.getElementById("rakDetailSearchInput"); if (input) input.value = ""; rakDetailSearchQuery = ""; const clearBtn = document.getElementById("rakDetailSearchClear"); if (clearBtn) clearBtn.classList.add("hidden"); renderRakDetailList(); }

async function loadMasterShift() { const container = document.getElementById("shiftList"); if (!container) return; container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat jadwal shift...</p></div>`; try { const today = new Date(); let start = shiftPeriod === "hari_ini" ? today : new Date(today.getFullYear(), today.getMonth(), 1); let end = shiftPeriod === "hari_ini" ? today : new Date(today.getFullYear(), today.getMonth() + 1, 0); if (shiftPeriod === "minggu") { const day = today.getDay(); start = new Date(today); start.setDate(today.getDate() + (day === 0 ? -6 : 1 - day)); end = new Date(start); end.setDate(start.getDate() + 6); } if (shiftPeriod === "custom") { const s = document.getElementById("customStart"), e = document.getElementById("customEnd"); if (s && s.value) start = new Date(s.value); if (e && e.value) end = new Date(e.value); } const startStr = start.getFullYear() + "-" + String(start.getMonth() + 1).padStart(2, '0') + "-" + String(start.getDate()).padStart(2, '0'); const endStr = end.getFullYear() + "-" + String(end.getMonth() + 1).padStart(2, '0') + "-" + String(end.getDate()).padStart(2, '0'); const filterSelect = document.getElementById("personilFilter"), namaFilter = filterSelect ? filterSelect.value : ""; const body = { tgl_start: startStr, tgl_end: endStr }; if (namaFilter) body.nama_filter = namaFilter; const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/master-shift`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal"); masterShiftData = data.data || []; if (masterShiftData.length === 0) { container.innerHTML = `<div class="shift-summary-empty"><p>Belum ada data shift</p></div>`; return; } const grouped = {}; masterShiftData.forEach(r => { if (!grouped[r.tanggal]) grouped[r.tanggal] = []; grouped[r.tanggal].push(r); }); container.innerHTML = Object.keys(grouped).sort().map(tgl => `<div class="date-group"><div class="date-group-header"><span class="date-group-date">📅 ${formatTanggalLong(tgl)}</span><span class="date-group-count">${grouped[tgl].length} orang</span></div>${grouped[tgl].map(r => `<div class="shift-row"><span class="shift-emoji">${r.shift_emoji || "❓"}</span><span class="shift-name">${r.nama}</span><span class="shift-badge ${getBadgeClass(r.kode_shift)}">${r.shift_nama || r.kode_shift}</span></div>`).join("")}</div>`).join(""); } catch (err) { container.innerHTML = `<p style="color:red;text-align:center;">Gagal: ${err.message}</p>`; } }
function getBadgeClass(kode) { return kode === "P7" ? "shift-badge-p7" : kode === "S15" ? "shift-badge-s15" : kode === "M22" ? "shift-badge-m22" : kode === "CUTI" ? "shift-badge-cuti" : "shift-badge-o"; }

function startLiveClock() { updateClock(); if (clockInterval) clearInterval(clockInterval); clockInterval = setInterval(updateClock, 1000); }
function updateClock() { const now = new Date(); const hh = String(now.getHours()).padStart(2, "0"); const mm = String(now.getMinutes()).padStart(2, "0"); if (document.getElementById("clockTime")) document.getElementById("clockTime").textContent = `${hh}:${mm}`; const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]; const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]; if (document.getElementById("clockDate")) document.getElementById("clockDate").textContent = `${hari[now.getDay()]}, ${now.getDate()} ${bulan[now.getMonth()]} ${now.getFullYear()}`; const hour = now.getHours(); let greeting = hour < 11 ? "Selamat Pagi 🌅" : hour < 15 ? "Selamat Siang ☀️" : hour < 18 ? "Selamat Sore 🌆" : "Selamat Malam 🌙"; const _user = getUser(); if (document.getElementById("clockGreeting")) document.getElementById("clockGreeting").textContent = `${greeting}, ${_user?.nama_lengkap || "Bos"}!`; }
function setTheme(theme) { document.documentElement.setAttribute("data-theme", theme); localStorage.setItem("so_theme", theme); document.querySelectorAll("#themeIcon, #themeIcon2, #sidebarThemeIcon").forEach(el => el.textContent = theme === "halloween-dark" ? "🌙" : "☀️"); }
function updateTimeTheme() { if (!autoThemeEnabled) return; const hour = new Date().getHours(); document.documentElement.setAttribute("data-time-theme", hour < 11 ? "pagi" : hour < 15 ? "siang" : hour < 18 ? "sore" : "malam"); }
function toggleSidebar() { document.getElementById("sidebar")?.classList.toggle("open"); document.getElementById("sidebarOverlay")?.classList.toggle("active"); }
function closeSidebar() { document.getElementById("sidebar")?.classList.remove("open"); document.getElementById("sidebarOverlay")?.classList.remove("active"); }
function formatTanggalLong(dateStr) { const d = new Date(dateStr); const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"], bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]; return `${d.getDate()} ${bulan[d.getMonth()]} ${d.getFullYear()} — ${hari[d.getDay()]}`; }
function formatTanggalShort(dateStr) { const d = new Date(dateStr), bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]; return `${d.getDate()} ${bulan[d.getMonth()]}`; }

window.addEventListener("popstate", (e) => { const activeScreen = document.querySelector(".screen.active"); if (!activeScreen) return; if (document.getElementById("sidebar")?.classList.contains("open")) { closeSidebar(); pushBackGuard(); return; } const modalOpen = document.querySelector(".modal-overlay.active:not(#exitModal)"); if (modalOpen) { modalOpen.classList.remove("active"); pushBackGuard(); return; } if (activeScreen.id === "homeScreen" || activeScreen.id === "loginScreen") { e.preventDefault(); document.getElementById("exitModal")?.classList.add("active"); exitModalShown = true; pushBackGuard(); return; } e.preventDefault(); goToHomeScreen(); pushBackGuard(); });
function pushBackGuard() { try { history.pushState({ guard: true, ts: Date.now() }, "", ""); } catch (e) {} }
setTimeout(pushBackGuard, 800);
function resetIdleTimer() { if (idleTimer) clearTimeout(idleTimer); if (!isLoggedIn() || document.querySelector(".screen.active")?.id === "loginScreen") return; idleTimer = setTimeout(() => { autoLogout(); }, IDLE_TIMEOUT); }
function autoLogout() { clearAuth(); showToastMini("⏰ Idle 5 menit — auto logout", "error"); setTimeout(() => { showLoginView(true); showScreen("loginScreen"); pushBackGuard(); }, 300); }
["click", "touchstart", "keydown", "scroll"].forEach(evt => document.addEventListener(evt, resetIdleTimer, { passive: true }));

function openChatSelectionModal() { document.getElementById("chatModeModal").classList.add("active"); }
function closeChatModeModal() { document.getElementById("chatModeModal").classList.remove("active"); }
function selectChatMode(mode) { closeChatModeModal(); if (mode === 'bot') goToChatScreen(); else showToastMini("Fitur Room Chat segera hadir!", "error"); }

function goToProfileScreen() { const _user = getUser(); if (!_user) return; document.getElementById("editNamaLengkap").value = _user.nama_lengkap || ""; const preview = document.getElementById("editAvatarPreview"); if (preview) { if (_user.avatar_url) { preview.style.backgroundImage = `url(${_user.avatar_url})`; preview.textContent = ""; } else { preview.textContent = (_user.nama_lengkap || _user.username || "?").substring(0, 2).toUpperCase(); preview.style.backgroundImage = "none"; } } showScreen("profileScreen"); }
async function submitUpdateProfile() { const btn = document.getElementById("btnSaveProfile"), namaBaru = document.getElementById("editNamaLengkap").value.trim(); if (!namaBaru) return showToastMini("❌ Nama nggak boleh kosong", "error"); btn.disabled = true; btn.textContent = "Menyimpan..."; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/me/update`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nama_lengkap: namaBaru }) }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); await refreshUserData(); showToastMini("✅ Nama diupdate", "success"); goToSettingsScreen(); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } finally { btn.disabled = false; btn.textContent = "Simpan Perubahan"; } }
async function uploadAvatar(input) { const file = input.files[0]; if (!file) return; if (file.size > 2 * 1024 * 1024) { showToastMini("⚠️ Maksimal 2MB", "error"); input.value = ""; return; } if (!file.type.startsWith("image/")) { showToastMini("❌ Harus gambar", "error"); input.value = ""; return; } showToastMini("📸 Mengupload...", "success"); try { const formData = new FormData(); formData.append("file", file); const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/me/upload-avatar`, { method: "POST", body: formData }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); await refreshUserData(); const _user = getUser(); const preview = document.getElementById("editAvatarPreview"); if (preview) { preview.style.backgroundImage = `url('${_user.avatar_url}?t=${Date.now()}')`; preview.style.backgroundColor = "transparent"; preview.textContent = ""; } showToastMini("✅ Foto diupdate", "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } }
function openImagePreview(url) { if (!url) return; const modal = document.getElementById("imagePreviewModal"), img = document.getElementById("imagePreviewImg"); if (modal && img) { img.src = url; modal.classList.add("active"); } }
function closeImagePreview() { document.getElementById("imagePreviewModal")?.classList.remove("active"); }

async function checkForUpdate(manual = false) { if (manual) showToastMini("🔍 Cek update...", "success"); try { const resp = await fetch(`${RAW_BACKEND_URL}/api/config/`); const data = await resp.json(); if (data.app && isNewerVersion(data.app.latest_version, CONFIG.APP_VERSION)) { if (manual) showToastMini("✅ Update tersedia!", "success"); } } catch (e) {} }
function isNewerVersion(latest, current) { const l = String(latest).split(".").map(Number), c = String(current).split(".").map(Number); for (let i = 0; i < 3; i++) { if ((l[i] || 0) > (c[i] || 0)) return true; if ((l[i] || 0) < (c[i] || 0)) return false; } return false; }

function goToUserManagementScreen() { const _user = getUser(); if (!_user || _user.role !== "admin") { showToastMini("❌ Akses ditolak. Khusus Admin.", "error"); return; } showScreen("userManagementScreen"); loadUsers(); }
async function loadUsers() { const container = document.getElementById("userListContainer"); if (!container) return; container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data user...</p></div>`; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/users`, { method: "GET" }); if (!resp.ok) throw new Error(`HTTP ${resp.status}`); const data = await resp.json(); if (!data.success) throw new Error(data.detail || "Gagal load user"); renderUserList(data.users); } catch (err) { console.error("[UserMgmt] Error:", err); container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${err.message}</p></div>`; } }
function renderUserList(users) { const container = document.getElementById("userListContainer"); if (!container) return; if (!users || users.length === 0) { container.innerHTML = `<p style="text-align:center; padding: 20px;">Belum ada user.</p>`; return; } const html = users.map(u => { const isMe = u.id === getUser().id, statusClass = u.aktif ? "shift-badge-p7" : "shift-badge-m22", statusText = u.aktif ? "Aktif" : "Nonaktif"; return `<div class="rak-card" style="margin-bottom: 10px;"><div class="rak-card-header"><span class="rak-card-id">${u.username}</span><span class="shift-badge ${statusClass}">${statusText}</span></div><div class="rak-card-body"><div class="rak-card-row"><span class="rak-card-label">Nama</span><span class="rak-card-value">${u.nama_lengkap}</span></div><div class="rak-card-row"><span class="rak-card-label">Role</span><span class="rak-card-value" style="text-transform: uppercase;">${u.role}</span></div><div class="rak-card-row"><span class="rak-card-label">Last Login</span><span class="rak-card-value">${u.last_login ? formatTanggalLong(u.last_login.split('T')[0]) : "-"}</span></div>${!isMe ? `<div style="display: flex; gap: 8px; margin-top: 12px;"><button class="settings-btn" style="padding: 8px; font-size: 12px;" onclick="resetUserPin(${u.id}, '${u.username}')">🔑 Reset PIN</button><button class="settings-btn" style="padding: 8px; font-size: 12px;" onclick="resetUserPassword(${u.id}, '${u.username}')">🔒 Reset Pass</button><button class="settings-btn settings-btn-danger" style="padding: 8px; font-size: 12px;" onclick="forceLogoutUser(${u.id}, '${u.username}')">🚪 Force Out</button></div>` : `<p style="font-size: 12px; color: var(--accent-orange); margin-top: 12px; text-align: center;">(Ini akun Anda)</p>`}</div></div>`; }).join(""); container.innerHTML = html; }
async function resetUserPin(userId, username) { const newPin = prompt(`Masukkan PIN baru untuk ${username} (6 digit):`); if (!newPin || newPin.length !== 6 || !/^\d+$/.test(newPin)) return showToastMini("❌ PIN harus 6 digit angka", "error"); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/users/${userId}/reset-pin`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ new_pin: newPin }) }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); showToastMini(`✅ PIN ${username} direset`, "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } }
async function resetUserPassword(userId, username) { const newPass = prompt(`Masukkan Password baru untuk ${username} (min 6 char):`); if (!newPass || newPass.length < 6) return showToastMini("❌ Password minimal 6 karakter", "error"); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/users/${userId}/reset-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ new_password: newPass }) }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); showToastMini(`✅ Password ${username} direset`, "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } }
async function forceLogoutUser(userId, username) { if (!confirm(`Tendang ${username} dari semua device?`)) return; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/users/${userId}/force-logout`, { method: "POST" }); const data = await resp.json(); if (!resp.ok) throw new Error(data.detail || "Gagal"); showToastMini(`✅ ${username} ditendang`, "success"); } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } }

function openAddUserModal() { document.getElementById("newUserUsername").value = ""; document.getElementById("newUserNama").value = ""; document.getElementById("newUserPassword").value = ""; document.getElementById("newUserPin").value = "123456"; document.getElementById("newUserRole").value = "operator"; document.getElementById("addUserError").textContent = ""; document.getElementById("addUserModal").classList.add("active"); }
function closeAddUserModal() { document.getElementById("addUserModal").classList.remove("active"); }
async function submitAddUser() { const btn = document.getElementById("btnSaveUser"), errEl = document.getElementById("addUserError"), username = document.getElementById("newUserUsername").value.trim().toUpperCase(), nama = document.getElementById("newUserNama").value.trim(), password = document.getElementById("newUserPassword").value, pin = document.getElementById("newUserPin").value, role = document.getElementById("newUserRole").value; if (!username || !nama || !password) { errEl.textContent = "❌ Semua field wajib diisi!"; return; } btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...'; errEl.textContent = ""; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password, nama_lengkap: nama, role, pin }) }); const data = await resp.json(); if (!resp.ok || !data.success) throw new Error(data.detail || data.error || "Gagal menambah user"); showToastMini(`✅ User ${username} berhasil dibuat`, "success"); closeAddUserModal(); loadUsers(); } catch (err) { console.error("[AddUser] Error:", err); errEl.textContent = `❌ ${err.message}`; } finally { btn.disabled = false; btn.innerHTML = '✅ Simpan'; } }

function goToNotificationsScreen() { 
    document.getElementById("notificationModal").classList.add("active");
    loadNotifications();
}
function closeNotificationModal() {
    document.getElementById("notificationModal").classList.remove("active");
}
function openPersonilModal() { document.getElementById("personilModal").classList.add("active"); loadPersonilList(); }
function closePersonilModal(event) { if (event && event.target !== event.currentTarget) return; document.getElementById("personilModal").classList.remove("active"); }
function openStreamlitInBrowser() { try { window.open(CONFIG.STREAMLIT_URL, "_blank"); } catch (e) { window.location.href = CONFIG.STREAMLIT_URL; } }

async function loadPersonilList() { const filterSelect = document.getElementById("personilFilter"), personilList = document.getElementById("personilList"); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/personil`, { method: "GET" }); if (!resp.ok) throw new Error(`HTTP ${resp.status}`); const data = await resp.json(); personilData = data.data || []; if (filterSelect) { const currentValue = filterSelect.value; filterSelect.innerHTML = '<option value="">👥 Semua Personil</option>'; personilData.forEach(p => { filterSelect.innerHTML += `<option value="${p.nama}">👤 ${p.nama}</option>`; }); filterSelect.value = currentValue; } if (!personilList) return; if (!personilData || personilData.length === 0) { personilList.innerHTML = `<div class="loading-state"><p>Belum ada personil</p></div>`; return; } personilList.innerHTML = personilData.map(p => { const isActive = p.aktif !== false; return `<div class="personil-item ${isActive ? '' : 'inactive'}"><span class="personil-item-emoji">👤</span><span class="personil-item-name">${p.nama}</span><span class="personil-item-status ${isActive ? 'personil-status-active' : 'personil-status-inactive'}">${isActive ? 'Aktif' : 'Off'}</span>${isActive ? `<div class="personil-item-actions"><button class="personil-item-btn delete" onclick="deletePersonilConfirm('${p.nama}')">🗑️</button></div>` : ''}</div>`; }).join(""); } catch (err) { if (personilList) personilList.innerHTML = `<div class="loading-state"><p style="color: var(--danger);">⚠️ Gagal load personil: ${err.message}</p></div>`; } }
async function addNewPersonil() { const input = document.getElementById("newPersonilName"); if (!input) return; const nama = input.value.trim().toUpperCase(); if (!nama || nama.length < 2) return showToastMini("❌ Nama minimal 2 karakter", "error"); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/personil/add`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nama: nama }) }); const data = await resp.json(); if (!resp.ok || !data.success) throw new Error(data.detail || `HTTP ${resp.status}`); input.value = ""; showToastMini(`✅ ${nama} ditambahkan`, "success"); _personilCache = null; await loadPersonilList(); } catch (err) { showToastMini(`❌ Gagal: ${err.message}`, "error"); } }
function deletePersonilConfirm(nama) { const html = `<div style="text-align: left;"><p style="font-size: 14px; margin-bottom: 12px;">Hapus personil <b style="color: var(--accent-orange);">${nama}</b>?</p><label style="display: flex; align-items: center; gap: 8px; padding: 10px; background: var(--bg-tertiary); border-radius: 8px; cursor: pointer; margin-bottom: 12px;"><input type="checkbox" id="forceDeleteCheck" style="width: 18px; height: 18px; accent-color: var(--danger);"><span style="font-size: 12px;">⚠️ <b>Force delete</b> — hapus history juga</span></label><div style="display: flex; gap: 8px;"><button class="confirm-btn confirm-btn-cancel" onclick="closeDeleteModal()">❌ Batal</button><button class="confirm-btn confirm-btn-save" style="background: linear-gradient(135deg, #ee5253, #c73133);" onclick="deletePersonilExecute('${nama}')">🗑️ Hapus</button></div></div>`; let confirmModal = document.getElementById("deleteConfirmModal"); if (!confirmModal) { confirmModal = document.createElement("div"); confirmModal.id = "deleteConfirmModal"; confirmModal.className = "modal-overlay active"; confirmModal.style.zIndex = "300"; confirmModal.innerHTML = `<div class="modal-content" onclick="event.stopPropagation()" style="max-width: 400px;"><div class="modal-header"><div class="modal-title">⚠️ Konfirmasi Hapus</div><button class="modal-close" onclick="closeDeleteModal()">✕</button></div><div class="modal-body" id="deleteConfirmBody"></div></div>`; document.body.appendChild(confirmModal); confirmModal.onclick = (e) => { if (e.target === confirmModal) closeDeleteModal(); }; } document.getElementById("deleteConfirmBody").innerHTML = html; }
function closeDeleteModal() { const modal = document.getElementById("deleteConfirmModal"); if (modal) modal.remove(); }
async function deletePersonilExecute(nama) { const checkbox = document.getElementById("forceDeleteCheck"); const force = checkbox ? checkbox.checked : false; closeDeleteModal(); try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/personil/delete`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nama: nama, force: force }) }); const data = await resp.json(); if (!resp.ok || !data.success) throw new Error(data.detail || `HTTP ${resp.status}`); showToastMini(data.message || `✅ ${nama} dihapus`, "success"); _personilCache = null; await loadPersonilList(); } catch (err) { showToastMini(`❌ Gagal: ${err.message}`, "error"); } }

function openThemeModal() { const isDark = document.documentElement.getAttribute("data-theme") === "halloween-dark"; const pesan = isDark ? "Mode sekarang: DARK. Ganti ke LIGHT?" : "Mode sekarang: LIGHT. Ganti ke DARK?"; if (confirm(pesan)) { toggleTheme(); showToastMini("✅ Tema berhasil diubah", "success"); } }
function openSystemModal() { const aksi = prompt("Menu Sistem:\n1. Cek Update\n2. Reset Semua Chat\n\nKetik angka (1/2):"); if (aksi === "1") checkForUpdate(true); else if (aksi === "2") resetAllChat(); }
function resetAllChat() { if (!confirm("Hapus SEMUA chat dengan 4 bot?")) return; Object.keys(BOTS).forEach(botId => { chatHistories[botId] = []; }); saveChatHistories(); showToastMini("✅ Semua chat dihapus", "success"); if (document.querySelector(".screen.active")?.id === "chatScreen") renderChatHistory(); }

function openEditBotModal() { const modal = document.getElementById("editBotModal"); if (!modal) return; const bot = BOTS[currentBot]; document.getElementById("editBotName").value = bot.name; document.getElementById("editBotEmoji").value = bot.emoji; document.getElementById("editBotPersona").value = bot.persona; modal.classList.add("active"); }
function closeEditBotModal() { document.getElementById("editBotModal")?.classList.remove("active"); }
function saveBotSettings() { const name = document.getElementById("editBotName").value.trim(); const emoji = document.getElementById("editBotEmoji").value.trim(); const persona = document.getElementById("editBotPersona").value.trim(); if (!name || !emoji || !persona) return showToastMini("❌ Semua field wajib diisi", "error"); BOTS[currentBot].name = name; BOTS[currentBot].emoji = emoji; BOTS[currentBot].persona = persona; localStorage.setItem("so_bots_custom", JSON.stringify(BOTS)); showToastMini("✅ Bot berhasil diupdate", "success"); closeEditBotModal(); switchBot(currentBot); }

function openConfirmShiftModal(data) { const modal = document.getElementById("confirmShiftModal"); if (!modal) return; currentConfirmData = data; const tglEl = document.getElementById("confirmModalDate"); if (tglEl) tglEl.textContent = formatTanggalLong(data.tanggal); const countEl = document.getElementById("confirmModalCount"); if (countEl) countEl.textContent = `${data.items.length} orang`; const container = document.getElementById("confirmModalList"); if (container) { container.innerHTML = data.items.map(it => { const kode = it.kode_shift || "O"; const shiftClass = getShiftModalClass(kode); return `<div class="confirm-modal-item ${shiftClass}"><span class="confirm-modal-item-icon">👤</span><span class="confirm-modal-item-name">${it.nama}</span><span class="confirm-modal-item-arrow">→</span><span class="confirm-modal-item-shift">${it.shift_nama || kode}</span></div>`; }).join(""); } const saveBtn = document.getElementById("confirmModalSaveBtn"); if (saveBtn) { saveBtn.disabled = false; saveBtn.innerHTML = "✅ Konfirmasi"; } modal.classList.add("active"); }
function closeConfirmShiftModal() { document.getElementById("confirmShiftModal")?.classList.remove("active"); currentConfirmData = null; }
function getShiftModalClass(kode) { switch (kode) { case "P7": return "shift-p7"; case "S15": return "shift-s15"; case "M22": return "shift-m22"; case "O": return "shift-o"; case "CUTI": return "shift-cuti"; default: return "shift-o"; } }
async function executeConfirmShift() { if (!currentConfirmData) return showToastMini("❌ Tidak ada data", "error"); const saveBtn = document.getElementById("confirmModalSaveBtn"); if (saveBtn) { saveBtn.disabled = true; saveBtn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...'; } const data = currentConfirmData; try { const resp = await apiFetch(`${CONFIG.BACKEND_URL}/hana/save-batch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tanggal: data.tanggal, items: data.items.map(it => ({ nama: it.nama, kode_shift: it.kode_shift })) }) }); const result = await resp.json(); if (!resp.ok || !result.success) throw new Error(result.detail || `HTTP ${resp.status}`); const savedCount = result.saved || data.items.length; closeConfirmShiftModal(); chatHistories[currentBot].push({ role: "assistant", content: `✅ ${savedCount} shift tersimpan!\n\n${getShiftSummaryText(data.items)}`, timestamp: Date.now(), isSuccess: true }); saveChatHistories(); renderChatHistory(); scrollToBottom(); if (document.getElementById("masterShiftScreen")?.classList.contains("active")) loadMasterShift(); showToastMini(`✅ ${savedCount} shift tersimpan`, "success"); } catch (err) { if (saveBtn) { saveBtn.disabled = false; saveBtn.innerHTML = "✅ Konfirmasi"; } chatHistories[currentBot].push({ role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true }); saveChatHistories(); renderChatHistory(); scrollToBottom(); showToastMini(`❌ Gagal: ${err.message}`, "error"); } }

// =========================================================
// TAMBALAN v11.1: MODAL SETTING & PROFIL RAPI
// =========================================================

// --- 1. MODAL TEMA ---
function openThemeModal() { document.getElementById("themeModal").classList.add("active"); }
function closeThemeModal() { document.getElementById("themeModal").classList.remove("active"); }

// --- 2. MODAL SISTEM ---
function openSystemModal() { document.getElementById("systemModal").classList.add("active"); }
function closeSystemModal() { document.getElementById("systemModal").classList.remove("active"); }

// --- 3. MODAL GANTI API KEY ---
function openChangeApiKeyModal() { 
    closeSystemModal();
    document.getElementById("newApiKeyInput").value = "";
    document.getElementById("changeApiKeyModal").classList.add("active"); 
}
function closeChangeApiKeyModal() { document.getElementById("changeApiKeyModal").classList.remove("active"); }
function submitChangeApiKey() {
    const newKey = document.getElementById("newApiKeyInput").value.trim();
    if (!newKey) return showToastMini("❌ API Key tidak boleh kosong", "error");
    // Simpan ke localStorage (opsional, karena proxy gak butuh key)
    localStorage.setItem("so_api_key", newKey);
    showToastMini("✅ API Key disimpan di device", "success");
    closeChangeApiKeyModal();
    updateApiKeyDisplay();
}

// --- 4. MODAL GANTI PIN ---
function openChangePinModal() {
    document.getElementById("pinLama").value = "";
    document.getElementById("pinBaru").value = "";
    document.getElementById("pinKonfirmasi").value = "";
    document.getElementById("changePinModal").classList.add("active");
}
function closeChangePinModal() { document.getElementById("changePinModal").classList.remove("active"); }
async function submitChangePin() {
    const oldPin = document.getElementById("pinLama").value.trim();
    const newPin = document.getElementById("pinBaru").value.trim();
    const confirmPin = document.getElementById("pinKonfirmasi").value.trim();

    if (!oldPin || !newPin || !confirmPin) return showToastMini("❌ Semua field wajib diisi", "error");
    if (newPin.length !== 6 || !/^\d+$/.test(newPin)) return showToastMini("❌ PIN baru harus 6 digit angka", "error");
    if (newPin !== confirmPin) return showToastMini("❌ Konfirmasi PIN tidak sama", "error");

    const btn = document.getElementById("btnSavePin");
    btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/change-pin`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_pin: oldPin, new_pin: newPin })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Gagal ganti PIN");
        showToastMini("✅ PIN berhasil diubah", "success");
        closeChangePinModal();
    } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } 
    finally { btn.disabled = false; btn.innerHTML = '✅ Simpan PIN'; }
}

// --- 5. MODAL GANTI PASSWORD ---
function openChangePasswordModal() {
    document.getElementById("passLama").value = "";
    document.getElementById("passBaru").value = "";
    document.getElementById("passKonfirmasi").value = "";
    document.getElementById("changePasswordModal").classList.add("active");
}
function closeChangePasswordModal() { document.getElementById("changePasswordModal").classList.remove("active"); }
async function submitChangePassword() {
    const oldPass = document.getElementById("passLama").value.trim();
    const newPass = document.getElementById("passBaru").value.trim();
    const confirmPass = document.getElementById("passKonfirmasi").value.trim();

    if (!oldPass || !newPass || !confirmPass) return showToastMini("❌ Semua field wajib diisi", "error");
    if (newPass.length < 6) return showToastMini("❌ Password baru minimal 6 karakter", "error");
    if (newPass !== confirmPass) return showToastMini("❌ Konfirmasi Password tidak sama", "error");

    const btn = document.getElementById("btnSavePassword");
    btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/change-password`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password: oldPass, new_password: newPass })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Gagal ganti Password");
        showToastMini("✅ Password berhasil diubah", "success");
        closeChangePasswordModal();
    } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } 
    finally { btn.disabled = false; btn.innerHTML = '✅ Simpan Password'; }
}

// --- 6. MODAL GANTI USERNAME ---
function openChangeUsernameModal() {
    const _user = getUser();
    document.getElementById("usernameLama").value = _user ? _user.username : "";
    document.getElementById("usernameBaru").value = "";
    document.getElementById("passwordKonfirmasiUser").value = "";
    document.getElementById("changeUsernameModal").classList.add("active");
}
function closeChangeUsernameModal() { document.getElementById("changeUsernameModal").classList.remove("active"); }
async function submitChangeUsername() {
    const usernameBaru = document.getElementById("usernameBaru").value.trim().toUpperCase();
    const password = document.getElementById("passwordKonfirmasiUser").value.trim();

    if (!usernameBaru || !password) return showToastMini("❌ Semua field wajib diisi", "error");
    if (usernameBaru.length < 3) return showToastMini("❌ Username minimal 3 karakter", "error");
    if (!/^[A-Z0-9_]+$/.test(usernameBaru)) return showToastMini("❌ Username hanya boleh huruf, angka, underscore", "error");

    const btn = document.getElementById("btnSaveUsername");
    btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/change-username`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_username: usernameBaru, password: password })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Gagal ganti Username");
        showToastMini("✅ Username berhasil diubah", "success");
        closeChangeUsernameModal();
        await refreshUserData(); // Tarik data user baru
        updateSettingsUserInfo(); // Update tampilan
    } catch (err) { showToastMini(`❌ ${err.message}`, "error"); } 
    finally { btn.disabled = false; btn.innerHTML = '✅ Simpan Username'; }
}
// =========================================================
// TAMBALAN v11.2: FIX FILTER SPD, SORT TOP, & INFO TOP RAK
// =========================================================

// --- 1. FIX FILTER & SORT SPD ---
function setSpdPeriod(period) {
    spdPeriodCurrent = period;
    document.querySelectorAll("#spdListScreen .spd-period-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period));
    const customRow = document.getElementById("spdCustomDateRow");
    if (customRow) {
        if (period === "custom") {
            customRow.classList.remove("hidden");
            const s = document.getElementById("spdCustomStart"), e = document.getElementById("spdCustomEnd"), today = new Date();
            if (s && !s.value) s.value = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
            if (e && !e.value) e.value = today.toISOString().slice(0, 10);
        } else customRow.classList.add("hidden");
    }
    loadSpdList(); // Ini yang tadi ilang/eror
}

function setSpdSort(sortValue) {
    spdSortValue = sortValue;
    document.querySelectorAll("#spdListScreen .spd-sort-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue));
    loadSpdList(); // Ini juga
}

// --- 2. FIX LOAD SPD (Biar gak error pas render) ---
async function loadSpdList() {
    const container = document.getElementById("spdList"); if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data SPD...</p></div>`;
    try {
        const today = new Date();
        let start = spdPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1);
        let end = spdPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0);
        if (spdPeriodCurrent === "custom") { const s = document.getElementById("spdCustomStart"), e = document.getElementById("spdCustomEnd"); if (s && s.value) start = new Date(s.value); if (e && e.value) end = new Date(e.value); }
        const body = { mode: spdPeriodCurrent };
        if (spdPeriodCurrent === "custom") { body.tgl_start = start.toISOString().slice(0, 10); body.tgl_end = end.toISOString().slice(0, 10); }
        
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/yui/spd-list`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json(); if (!data.success) throw new Error(data.error || "Gagal load SPD");
        
        spdListData = data.list_spd || [];
        
        // ✅ FIX: Sort data sebelum render
        spdListData = sortSpdData(spdListData, spdSortValue);
        
        if (document.getElementById("spdSummaryTotal")) document.getElementById("spdSummaryTotal").textContent = formatRupiahFull(data.total_spd || 0);
        if (document.getElementById("spdSummaryMeta")) document.getElementById("spdSummaryMeta").textContent = `📅 ${data.periode || "—"}`;
        if (document.getElementById("spdSummaryHari")) document.getElementById("spdSummaryHari").textContent = data.total_hari || 0;
        if (document.getElementById("spdSummaryAvg")) document.getElementById("spdSummaryAvg").textContent = formatRupiahFull(data.avg_spd || 0);
        
        renderSpdList();
    } catch (err) { container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${escapeHtml(err.message)}</p></div>`; }
}

// --- 3. FIX SORTING SPD ---
function sortSpdData(data, sortBy) {
    const arr = [...data];
    if (sortBy === "tanggal_asc") {
        arr.sort((a, b) => (a.tanggal || "").localeCompare(b.tanggal || ""));
    } else if (sortBy === "tanggal_desc") {
        arr.sort((a, b) => (b.tanggal || "").localeCompare(a.tanggal || ""));
    } else if (sortBy === "spd_desc") {
        arr.sort((a, b) => (b.spd || 0) - (a.spd || 0));
    } else if (sortBy === "spd_asc") {
        arr.sort((a, b) => (a.spd || 0) - (b.spd || 0));
    }
    return arr;
}

// =========================================================
// FINAL FIX: TOP MINUS (Sort + Info Tanggal & PIC)
// =========================================================
async function loadTopMinus() {
    const container = document.getElementById("topList"); 
    if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat data...</p></div>`;
    
    try {
        const today = new Date();
        let start = topPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth() - 1, 1);
        let end = topPeriodCurrent === "bulan_ini" ? new Date(today.getFullYear(), today.getMonth() + 1, 0) : new Date(today.getFullYear(), today.getMonth(), 0);
        
        const body = { mode: topPeriodCurrent };
        if (topPeriodCurrent === "custom") { 
            body.tgl_start = start.toISOString().slice(0, 10); 
            body.tgl_end = end.toISOString().slice(0, 10); 
        }
        
        // ✅ KUNCI UTAMA: Selalu kirim order_by ke backend
        body.order_by = topSortValue;

        let url = "";
        if (topTabCurrent === "rak") {
            url = `${CONFIG.BACKEND_URL}/yui/top-rak`;
            body.limit = 500;
        } else {
            url = `${CONFIG.BACKEND_URL}/yui/top-items-extended`;
            body.limit = null;
            body.search = topSearchQuery || "";
            body.sign = topSignCurrent;
        }
        
        // Debugging: Cek body yang dikirim
        console.log("[TopMinus] Body dikirim:", body);

        const resp = await apiFetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await resp.json(); 
        
        if (!data.success) throw new Error(data.error || "Gagal");
        
        topData = topTabCurrent === "rak" ? (data.list_rak || []) : (data.items || []);
        
        // Update Summary
        if (document.getElementById("topSummaryTotal")) document.getElementById("topSummaryTotal").textContent = formatRupiahFull(data.total_nominal || 0);
        if (document.getElementById("topSummaryMeta")) document.getElementById("topSummaryMeta").textContent = `${topTabCurrent === "rak" ? data.total_rak : data.total_items} item • ${data.periode}`;
        
        if (topData.length === 0) { 
            container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">💰</span><p>Belum ada data.</p></div>`; 
            return; 
        }
        
        // Render List
        container.innerHTML = topData.map((item, idx) => {
            const isRak = topTabCurrent === "rak";
            const title = isRak ? item.rak_id : cleanHtmlEntities(item.nama_produk || item.nama || item.plu || "-");
            const nominal = item.nominal_adjust || 0;
            const nominalClass = nominal < 0 ? "top-nominal-minus" : "top-nominal-plus";
            const clickAction = isRak ? `onclick="openRakDetail('${escapeHtml(item.rak_id)}')" style="cursor:pointer;"` : "";
            
            let metaHtml = "";
            if (isRak) {
                const tglShort = item.tgl_so ? formatTanggalShort(item.tgl_so) : "-";
                const pic = item.pic || "-";
                metaHtml = `<div class="top-item-meta" style="margin-top: 8px; display: flex; gap: 12px; font-size: 11px; color: var(--text-muted);">
                    <span>📅 ${tglShort}</span>
                    <span>👤 ${escapeHtml(pic)}</span>
                </div>`;
            } else {
                metaHtml = `<div class="top-item-meta" style="margin-top: 8px; display: flex; gap: 12px; font-size: 11px; color: var(--text-muted);">
                    <span>🏪 ${escapeHtml(item.rak_id || "-")}</span>
                    <span>🔢 ${escapeHtml(item.plu || "-")}</span>
                </div>`;
            }
            
            return `<div class="top-item-card" ${clickAction}>
                <div class="top-item-header">
                    <span class="top-item-rank">#${idx + 1}</span>
                    <span class="top-item-title">${escapeHtml(title)}</span>
                    <span class="top-item-nominal ${nominalClass}">${formatRupiahFull(nominal)}</span>
                </div>
                ${metaHtml}
                ${isRak ? `<div class="top-item-hint" style="font-size: 10px; color: var(--accent-flame); margin-top: 6px; font-style: italic;">Tap untuk detail item →</div>` : ""}
            </div>`;
        }).join("");
        
    } catch (err) { 
        console.error("[TopMinus] Error:", err);
        container.innerHTML = `<p style="color:red;text-align:center;">Gagal: ${err.message}</p>`; 
    }
}

// --- 5. FIX FILTER & SORT TOP (Biar Gak Eror) ---
function setTopPeriod(period) {
    topPeriodCurrent = period;
    document.querySelectorAll("#topMinusScreen .spd-period-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period));
    const customRow = document.getElementById("topCustomDateRow");
    if (customRow) {
        if (period === "custom") {
            customRow.classList.remove("hidden");
            const s = document.getElementById("topCustomStart"), e = document.getElementById("topCustomEnd"), today = new Date();
            if (s && !s.value) s.value = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
            if (e && !e.value) e.value = today.toISOString().slice(0, 10);
        } else customRow.classList.add("hidden");
    }
    loadTopMinus();
}

function setTopSort(sortValue) {
    topSortValue = sortValue;
    document.querySelectorAll("#topMinusScreen .spd-sort-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue));
    loadTopMinus();
}
// =========================================================
// TAMBALAN v11.3: FIX TOP FILTER, CHAT HISTORY, AUTO THEME
// =========================================================

// --- 1. FIX: Filter Top Rak & Top Item (Maksa Reload) ---
function setTopPeriod(period) {
    topPeriodCurrent = period;
    document.querySelectorAll("#topMinusScreen .spd-period-tab").forEach(tab => tab.classList.toggle("active", tab.getAttribute("data-period") === period));
    const customRow = document.getElementById("topCustomDateRow");
    if (customRow) {
        if (period === "custom") {
            customRow.classList.remove("hidden");
            const s = document.getElementById("topCustomStart"), e = document.getElementById("topCustomEnd"), today = new Date();
            if (s && !s.value) s.value = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
            if (e && !e.value) e.value = today.toISOString().slice(0, 10);
        } else customRow.classList.add("hidden");
    }
    loadTopMinus(); // ✅ PASTIIN INI ADA
}

function setTopSort(sortValue) {
    topSortValue = sortValue;
    document.querySelectorAll("#topMinusScreen .spd-sort-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue));
    loadTopMinus(); // ✅ PASTIIN INI ADA
}

function setTopTab(tab) {
    topTabCurrent = tab;
    document.querySelectorAll(".top-subtab").forEach(t => t.classList.toggle("active", t.getAttribute("data-tab") === tab));
    const searchWrapper = document.getElementById("topSearchWrapper"), filterSign = document.getElementById("topFilterSign");
    if (searchWrapper) { if (tab === "item") searchWrapper.classList.remove("hidden"); else searchWrapper.classList.add("hidden"); }
    if (filterSign) { if (tab === "item") filterSign.classList.remove("hidden"); else filterSign.classList.add("hidden"); }
    topSearchQuery = ""; const searchInput = document.getElementById("topSearchInput"); if (searchInput) searchInput.value = "";
    loadTopMinus(); // ✅ PASTIIN INI ADA
}

function setTopSign(sign) {
    topSignCurrent = sign;
    document.querySelectorAll(".top-filter-btn").forEach(btn => btn.classList.toggle("active", btn.getAttribute("data-sign") === sign));
    loadTopMinus(); // ✅ PASTIIN INI ADA
}

// --- 2. FIX: Chat History Hilang Pas Ganti Bot ---
function renderChatHistory() {
    const container = document.getElementById("chatMessages"); if (!container) return; let history = chatHistories[currentBot] || [];
    // Kalau gak ada history, tampilin welcome
    if (history.length === 0) { 
        container.innerHTML = `<div class="chat-message-wrapper ai"><div class="chat-avatar">${BOTS[currentBot].emoji}</div><div class="bubble-content ai"><div class="bubble bubble-ai bubble-welcome">Halo Bos! 👋<br>Aku <b>${BOTS[currentBot].name}</b>.<br>${getWelcomeText(currentBot)}</div></div></div>`; 
        return; 
    }
    
    container.innerHTML = ""; let lastDate = "";
    const _user = getUser(); const userAvatar = _user?.avatar_url ? `background-image: url('${_user.avatar_url}'); background-size: cover; background-position: center; background-color: transparent;` : "";
    
    // Iterasi semua history
    history.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        const msgDate = new Date(msg.timestamp || Date.now()).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
        
        // Divider tanggal
        if (msgDate !== lastDate) { 
            const dateDiv = document.createElement("div");
            dateDiv.className = "chat-date-divider";
            dateDiv.innerHTML = `<span>${msgDate}</span>`;
            container.appendChild(dateDiv);
            lastDate = msgDate; 
        }
        
        const wrapper = document.createElement("div"); wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;
        const avatar = document.createElement("div"); avatar.className = isUser ? "chat-avatar avatar-user" : "chat-avatar";
        if (isUser) { if (_user?.avatar_url) { avatar.style = userAvatar; avatar.textContent = ""; } else avatar.textContent = "👤"; } 
        else { avatar.textContent = BOTS[currentBot].emoji; }
        
        const bubbleContent = document.createElement("div"); bubbleContent.className = `bubble-content ${isUser ? "user" : "ai"}`;
        
        if (msg.isConfirm && msg.confirmData) { 
            bubbleContent.appendChild(renderConfirmBubble(msg, idx)); 
        } else {
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


// --- 3. FIX: Auto Theme (toggleAutoTheme yang hilang) ---
function toggleAutoTheme() {
    autoThemeEnabled = !autoThemeEnabled;
    localStorage.setItem("so_auto_theme", String(autoThemeEnabled));
    if (autoThemeEnabled) {
        updateTimeTheme();
        showToastMini("✅ Auto Tema Jam Aktif", "success");
    } else {
        showToastMini("⚠️ Auto Tema Jam Dimatikan", "error");
    }
    // Update tampilan tombol jika ada
    const el = document.getElementById("autoThemeValue");
    if (el) el.textContent = autoThemeEnabled ? "Aktif" : "Nonaktif";
}
// =========================================================
// PHASE 3: BROADCAST & ROOM CHAT
// =========================================================

// --- 1. BROADCAST ---
function goToBroadcastScreen() {
    closeSidebar();
    showScreen("broadcastScreen");
    
    const _user = getUser();
    const btnAdd = document.getElementById("btnAddBroadcast");
    if (btnAdd) btnAdd.style.display = (_user?.role === "admin") ? "flex" : "none";
    
    loadBroadcastList();
    markBroadcastAsRead(); // ✅ TAMBAHIN INI
}

async function loadBroadcastList() {
    const container = document.getElementById("broadcastList"); 
    if (!container) return;
    
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat broadcast...</p></div>`;
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/broadcast/list`, { method: "GET" });
        
        // Debugging: Liat response mentah
        console.log("[Broadcast] HTTP Status:", resp.status);
        
        const data = await resp.json();
        console.log("[Broadcast] Response:", data);
        
        if (!data.success) throw new Error(data.detail || "Gagal load broadcast");
        
        // Kalau sukses tapi array kosong
        if (!data.data || data.data.length === 0) {
            container.innerHTML = `
                <div class="shift-summary-empty">
                    <span class="empty-icon">📢</span>
                    <p>Belum ada broadcast.</p>
                </div>
            `;
            return;
        }
        
        // Render data
        container.innerHTML = data.data.map(b => {
            let icon = "📢", color = "var(--accent-flame)";
            if (b.tipe === "update") { icon = "🚀"; color = "#06d6a0"; }
            else if (b.tipe === "warning") { icon = "⚠️"; color = "#ee5253"; }
            
            return `
                <div class="settings-card" style="padding: 16px; margin-bottom: 12px; border-left: 4px solid ${color};">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 20px;">${icon}</span>
                        <div style="font-size: 16px; font-weight: 800; color: ${color};">${escapeHtml(b.judul)}</div>
                    </div>
                    <div style="font-size: 13px; color: var(--text-bone); line-height: 1.6;">${escapeHtml(b.pesan)}</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 12px; text-align: right;">
                        ${formatTanggalLong(b.created_at.split('T')[0])} • ${formatTime(b.created_at)}
                    </div>
                </div>
            `;
        }).join("");
        
    } catch (err) {
        console.error("[Broadcast] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load broadcast: ${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

// --- 2. ROOM CHAT ---
function goToRoomListScreen() {
    closeSidebar();
    showScreen("roomListScreen");
    loadRoomList();
}

async function loadRoomList() {
    const container = document.getElementById("roomList"); if (!container) return;
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat room...</p></div>`;
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/room/list`, { method: "GET" });
        const data = await resp.json();
        if (!data.success) throw new Error("Gagal load room");
        
        container.innerHTML = data.data.map(r => `
            <div class="settings-card" onclick="openRoomChat(${r.id}, '${escapeHtml(r.nama_room)}')" style="padding: 16px; margin-bottom: 12px; cursor: pointer;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="font-size: 24px;">👥</div>
                    <div>
                        <div style="font-size: 16px; font-weight: 800; color: var(--text-bone);"># ${escapeHtml(r.nama_room)}</div>
                        <div style="font-size: 12px; color: var(--text-muted);">${escapeHtml(r.deskripsi || "")}</div>
                    </div>
                </div>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = `<p style="color:red;">Gagal: ${err.message}</p>`;
    }
}

let currentRoomId = null;
let roomRefreshInterval = null;

async function openRoomChat(roomId, roomName) {
    // ✅ Clear interval lama biar gak spam request
    if (roomRefreshInterval) { 
        clearInterval(roomRefreshInterval); 
        roomRefreshInterval = null; 
    }
    
    currentRoomId = roomId;
    document.getElementById("roomChatTitle").textContent = `# ${roomName}`;
    
    const container = document.getElementById("roomMessages");
    if (container) container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat...</p></div>`;
    
    showScreen("roomChatScreen");
    
    // ✅ Init sistem mention (autocomplete @)
    initMentionSystem(); 
    
    await loadRoomMessages();
    
    // ✅ Auto refresh tiap 5 detik
    roomRefreshInterval = setInterval(loadRoomMessages, 5000);
}

async function loadRoomMessages() {
    if (!currentRoomId) return;
    const container = document.getElementById("roomMessages"); 
    if (!container) return;
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/room/messages/${currentRoomId}`, { method: "GET" });
        const data = await resp.json();
        if (!data.success) throw new Error("Gagal load pesan");
        
        const _user = getUser();
        const myUsername = _user?.username; // ✅ Ambil username buat cek tag
        const isFirstLoad = container.innerHTML.includes("loading-state") || container.innerHTML.trim() === "";
        
        const newHtml = data.data.map(m => {
            const isBot = m.user_id === null;
            const isMe = m.user_id === _user?.id;
            const nama = isBot ? "🤖 Bot AI" : (m.users?.nama_lengkap || m.users?.username || "User");
            const avatarUrl = m.users?.avatar_url;
            
            // ✅ CEK APAKAH PESAN INI NGE-TAG KITA
            const isTagged = m.pesan.includes(`@${myUsername}`) && !isMe;
            
            let wrapperClass = isMe ? "user" : "ai";
            let avatarHtml = "";
            
            if (isBot) {
                wrapperClass = "ai";
                avatarHtml = `<div class="chat-avatar" style="background: linear-gradient(135deg, #a259ff, #ff6b1a); font-size: 18px;">🤖</div>`;
            } else if (avatarUrl) {
                avatarHtml = `<div class="chat-avatar ${isMe ? "avatar-user" : ""}" style="background-image: url('${avatarUrl}'); background-size: cover; background-position: center; background-color: transparent;"></div>`;
            } else {
                const inisial = nama.substring(0, 2).toUpperCase();
                avatarHtml = `<div class="chat-avatar ${isMe ? "avatar-user" : ""}">${inisial}</div>`;
            }

            // ✅ STYLE DEFAULT & STYLE KHUSUS MENTION
            let bubbleStyle = isBot ? 'border: 1px solid #a259ff; background: rgba(162,89,255,0.1);' : '';
            if (isTagged) {
                // Warna ungu ngejreng kalau di-tag (mirip Discord)
                bubbleStyle = 'border: 2px solid #a259ff; background: rgba(162,89,255,0.25); box-shadow: 0 0 10px rgba(162,89,255,0.4);';
            }

            return `
                <div class="chat-message-wrapper ${wrapperClass}" style="margin-bottom: 8px;">
                    ${avatarHtml}
                    <div class="bubble-content ${wrapperClass}">
                        <div style="font-size: 10px; color: ${isBot ? '#a259ff' : 'var(--text-muted)'}; margin-bottom: 2px; ${isMe ? "text-align: right;" : ""}">
                            ${escapeHtml(nama)} ${isTagged ? '<span style="background:#a259ff; color:white; font-size:8px; padding:2px 4px; border-radius:4px; margin-left:4px;">TAG KAMU</span>' : ''}
                        </div>
                        <div class="bubble bubble-${wrapperClass}" style="${bubbleStyle}">${formatMentions(m.pesan)}</div>
                        <div class="bubble-time">${formatTime(m.created_at)}</div>
                    </div>
                </div>
            `;
        }).join("");

        if (isFirstLoad) {
            container.innerHTML = newHtml;
            container.scrollTop = container.scrollHeight;
        } else {
            const currentMessageCount = container.querySelectorAll(".chat-message-wrapper").length;
            if (data.data.length > currentMessageCount) {
                const wasNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
                container.innerHTML = newHtml;
                if (wasNearBottom) container.scrollTop = container.scrollHeight;
            }
        }
        
        // ✅ HAPUS NOTIF MENTION DARI LOCALSTORAGE & UPDATE BADGE
        if (_user) {
            const mentionKey = `so_mention_${_user.username}`;
            let mentions = JSON.parse(localStorage.getItem(mentionKey) || "[]");
            
            // Filter: Buang SEMUA mention yang room_id-nya sama dengan room yang lagi dibuka
            const initialLength = mentions.length;
            const filteredMentions = mentions.filter(m => m.room_id !== currentRoomId);
            
            if (mentions.length !== filteredMentions.length) {
                localStorage.setItem(mentionKey, JSON.stringify(filteredMentions));
                // Update lonceng langsung!
                if (typeof updateNotifBadge === 'function') updateNotifBadge();
            }
        }
        
    } catch (err) {
        console.error("Gagal load pesan:", err);
    }
}

async function sendRoomMessage() {
    const input = document.getElementById("roomInput");
    if (!input || !currentRoomId) return;
    const text = input.value.trim();
    if (!text) return;
    
    input.value = "";
    try {
        await apiFetch(`${CONFIG.BACKEND_URL}/room/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ room_id: currentRoomId, pesan: text })
        });
        await loadRoomMessages();
    } catch (err) {
        showToastMini("❌ Gagal kirim pesan", "error");
    }
}

// --- 3. UPDATE MODAL CHAT SELECTION ---
function openChatSelectionModal() {
    document.getElementById("chatModeModal").classList.add("active");
}
function closeChatModeModal() {
    document.getElementById("chatModeModal").classList.remove("active");
}
function selectChatMode(mode) {
    closeChatModeModal();
    if (mode === 'bot') goToChatScreen();
    else if (mode === 'room') goToRoomListScreen();
}

// --- 4. UPDATE FOTO BOT DI CHAT ---
// Cari fungsi renderChatHistory, ganti bagian avatar jadi ini:
function renderChatHistory() {
    const container = document.getElementById("chatMessages"); if (!container) return; let history = chatHistories[currentBot] || [];
    if (history.length === 0) { 
        container.innerHTML = `<div class="chat-message-wrapper ai"><div class="chat-avatar">${BOTS[currentBot].emoji}</div><div class="bubble-content ai"><div class="bubble bubble-ai bubble-welcome">Halo Bos! 👋<br>Aku <b>${BOTS[currentBot].name}</b>.<br>${getWelcomeText(currentBot)}</div></div></div>`; 
        return; 
    }
    container.innerHTML = ""; let lastDate = "";
    const _user = getUser(); const userAvatar = _user?.avatar_url ? `background-image: url('${_user.avatar_url}'); background-size: cover; background-position: center; background-color: transparent;` : "";
    history.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        const msgDate = new Date(msg.timestamp || Date.now()).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
        if (msgDate !== lastDate) { container.innerHTML += `<div class="chat-date-divider"><span>${msgDate}</span></div>`; lastDate = msgDate; }
        const wrapper = document.createElement("div"); wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;
        const avatar = document.createElement("div"); avatar.className = isUser ? "chat-avatar avatar-user" : "chat-avatar";
        
        // ✅ FOTO BOT
        if (isUser) { 
            if (_user?.avatar_url) { avatar.style = userAvatar; avatar.textContent = ""; } else avatar.textContent = "👤"; 
        } else { 
            const bot = BOTS[currentBot];
            if (bot.foto) {
                avatar.style.backgroundImage = `url('${bot.foto}')`;
                avatar.style.backgroundSize = "cover";
                avatar.style.backgroundPosition = "center";
                avatar.style.backgroundColor = "transparent";
                avatar.textContent = "";
            } else {
                avatar.textContent = bot.emoji; 
            }
        }
        
        const bubbleContent = document.createElement("div"); bubbleContent.className = `bubble-content ${isUser ? "user" : "ai"}`;
        if (msg.isConfirm && msg.confirmData) { bubbleContent.appendChild(renderConfirmBubble(msg, idx)); } else {
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
// =========================================================
// ADMIN: BUAT BROADCAST
// =========================================================
function openCreateBroadcastModal() {
    const _user = getUser();
    if (!_user || _user.role !== "admin") {
        showToastMini("❌ Akses ditolak. Khusus Admin.", "error");
        return;
    }
    document.getElementById("broadcastJudul").value = "";
    document.getElementById("broadcastPesan").value = "";
    document.getElementById("broadcastTipe").value = "info";
    document.getElementById("createBroadcastError").textContent = "";
    document.getElementById("createBroadcastModal").classList.add("active");
}

function closeCreateBroadcastModal() {
    document.getElementById("createBroadcastModal").classList.remove("active");
}

async function submitCreateBroadcast() {
    const btn = document.getElementById("btnSaveBroadcast");
    const errEl = document.getElementById("createBroadcastError");
    const judul = document.getElementById("broadcastJudul").value.trim();
    const pesan = document.getElementById("broadcastPesan").value.trim();
    const tipe = document.getElementById("broadcastTipe").value;

    if (!judul || !pesan) {
        errEl.textContent = "❌ Judul & pesan wajib diisi";
        return;
    }

    btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Mengirim...';
    errEl.textContent = "";

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/broadcast/create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ judul, pesan, tipe })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Gagal buat broadcast");
        
        showToastMini("✅ Broadcast terkirim!", "success");
        closeCreateBroadcastModal();
        loadBroadcastList(); // Reload list
    } catch (err) {
        errEl.textContent = `❌ ${err.message}`;
    } finally {
        btn.disabled = false; btn.innerHTML = '✅ Kirim';
    }
}
// =========================================================
// FASE B: MENTION SYSTEM (@) — DI LUAR FUNGSI LAIN
// =========================================================

function initMentionSystem() {
    const input = document.getElementById("roomInput");
    const list = document.getElementById("mentionList");
    if (!input || !list) return;

    fetchMentionUsers();

    input.addEventListener("input", () => {
        const val = input.value;
        const cursorPos = input.selectionStart;
        const textBeforeCursor = val.substring(0, cursorPos);
        const lastAtPos = textBeforeCursor.lastIndexOf("@");

        if (lastAtPos !== -1 && (lastAtPos === 0 || textBeforeCursor[lastAtPos - 1] === " ")) {
            const query = textBeforeCursor.substring(lastAtPos + 1).toLowerCase();
            if (!query.includes(" ")) {
                showMentionList(query, lastAtPos);
                return;
            }
        }
        list.style.display = "none";
        mentionActive = false;
    });

    input.addEventListener("keydown", (e) => {
        if (!mentionActive) return;
        const items = list.querySelectorAll(".mention-item");
        if (items.length === 0) return;
        
        let active = Array.from(items).find(i => i.classList.contains("active"));
        let idx = active ? Array.from(items).indexOf(active) : -1;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (active) active.classList.remove("active");
            idx = (idx + 1) % items.length;
            items[idx].classList.add("active");
            items[idx].scrollIntoView({ block: "nearest" });
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (active) active.classList.remove("active");
            idx = (idx - 1 + items.length) % items.length;
            items[idx].classList.add("active");
            items[idx].scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter" && active) {
            e.preventDefault();
            active.click();
        } else if (e.key === "Escape") {
            list.style.display = "none";
            mentionActive = false;
        }
    });
}

async function fetchMentionUsers() {
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/auth/users`, { method: "GET" });
        const data = await resp.json();
        if (data.success) {
            mentionUsers = data.users.map(u => ({
                type: 'user',
                id: u.id,
                name: u.nama_lengkap || u.username,
                username: u.username,
                emoji: '👤'
            }));
        }
    } catch (e) { console.log("Gagal load users buat mention", e); }
    
    const bots = Object.keys(BOTS).map(k => ({
        type: 'bot',
        id: k,
        name: BOTS[k].name,
        username: k,
        emoji: BOTS[k].emoji
    }));
    
    mentionUsers = [...bots, ...mentionUsers];
}

function showMentionList(query, atPos) {
    const list = document.getElementById("mentionList");
    if (!list) return;

    const filtered = mentionUsers.filter(u => 
        u.name.toLowerCase().includes(query) || 
        u.username.toLowerCase().includes(query)
    );

    if (filtered.length === 0) {
        list.style.display = "none";
        mentionActive = false;
        return;
    }

    mentionActive = true;
    list.style.display = "block";
    list.innerHTML = filtered.map((u, i) => `
        <div class="mention-item ${i === 0 ? 'active' : ''}" onclick="insertMention('${u.username}', ${atPos})" style="padding: 10px 14px; display: flex; align-items: center; gap: 10px; cursor: pointer; border-bottom: 1px solid var(--border-stone); background: ${i === 0 ? 'rgba(255,123,0,0.1)' : 'transparent'};">
            <span style="font-size: 18px;">${u.emoji}</span>
            <div>
                <div style="font-size: 14px; font-weight: 700; color: var(--text-bone);">${escapeHtml(u.name)}</div>
                <div style="font-size: 11px; color: var(--text-muted);">@${escapeHtml(u.username)}</div>
            </div>
        </div>
    `).join("");
}

function insertMention(username, atPos) {
    const input = document.getElementById("roomInput");
    const val = input.value;
    const before = val.substring(0, atPos);
    const after = val.substring(input.selectionStart);
    
    input.value = `${before}@${username} ${after}`;
    document.getElementById("mentionList").style.display = "none";
    mentionActive = false;
    input.focus();
}
// =========================================================
// FASE 3: NOTIFIKASI (Badge Lonceng)
// =========================================================

// Cek broadcast baru sejak terakhir user buka
async function updateNotifBadge() {
    const _user = getUser();
    if (!_user) return;

    try {
        // ✅ Nembak API Backend (lewat proxy)
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/realtime/unread-count/${_user.username}`, { method: "GET" });
        const data = await resp.json();

        const badge = document.getElementById("notifBadge");
        if (badge) {
            if (data.success && data.count > 0) {
                badge.style.display = "block";
                badge.textContent = data.count > 9 ? "9+" : String(data.count);
            } else {
                badge.style.display = "none";
            }
        }
    } catch (e) {
        console.warn("[Notif] Gagal update badge:", e);
    }
}

// Tandai broadcast udah dibaca (pas buka halaman Broadcast)
async function markBroadcastAsRead() {
    try {
        const _user = getUser();
        const _key = _user ? `so_last_broadcast_${_user.username}` : "so_last_broadcast_guest";

        // Fetch data dengan await
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/broadcast/list`, { method: "GET" });
        const data = await resp.json();

        if (data.success && data.data && data.data.length > 0) {
            localStorage.setItem(_key, String(data.data[0].id));
        }

        // Sembunyiin badge (dengan null check)
        const badge = document.getElementById("notifBadge");
        if (badge) badge.style.display = "none";
    } catch (e) {
        console.warn("[Notif] Gagal mark read:", e);
    }
}
async function loadNotifications() {
    const container = document.getElementById("notificationList");
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat...</p></div>`;
    
    try {
        const _user = getUser();
        let notifArray = []; 

        // 1. TARIK BROADCAST (Tetep nampilin semua biar user bisa baca)
        const respB = await apiFetch(`${CONFIG.BACKEND_URL}/broadcast/list`, { method: "GET" });
        const dataB = await respB.json();
        
        if (dataB.success && dataB.data) {
            dataB.data.forEach(b => {
                notifArray.push({
                    type: "broadcast",
                    timestamp: new Date(b.created_at).getTime(),
                    judul: b.judul,
                    pesan: b.pesan,
                    tipe: b.tipe
                });
            });
        }

        // 2. TARIK MENTION DARI DATABASE (Ganti localStorage!)
        // Kita panggil API baru yang tadi lo debug (atau bikin endpoint list)
        const respM = await apiFetch(`${CONFIG.BACKEND_URL}/realtime/list/${_user.username}`, { method: "GET" });
        const dataM = await respM.json();
        
        if (dataM.success && dataM.data) {
            dataM.data.forEach(m => {
                notifArray.push({
                    type: "mention",
                    timestamp: new Date(m.created_at).getTime(),
                    sender: m.sender_name,
                    text: m.message,
                    room_id: m.room_id || 1,
                    room_name: "Server"
                });
            });
        }

        // 3. SORTIR DARI YANG PALING BARU
        notifArray.sort((a, b) => b.timestamp - a.timestamp);

        // 4. RENDER KE HTML
        let html = "";
        if (notifArray.length === 0) {
            html = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Belum ada notifikasi.</div>`;
        } else {
            notifArray.forEach(n => {
                if (n.type === "broadcast") {
                    let icon = n.tipe === "update" ? "🚀" : (n.tipe === "warning" ? "⚠️" : "📢");
                    html += `
                        <div class="settings-card" style="padding: 12px; margin-bottom: 8px; border-left: 4px solid #ff7b00; cursor: pointer;" onclick="goToBroadcastScreen(); closeNotificationModal();">
                            <div style="font-size: 14px; font-weight: bold; color: #ff7b00;">${icon} ${escapeHtml(n.judul)}</div>
                            <div style="font-size: 12px; color: var(--text-muted);">${escapeHtml(n.pesan.substring(0, 50))}...</div>
                        </div>
                    `;
                } else if (n.type === "mention") {
                    html += `
                        <div class="settings-card" style="padding: 12px; margin-bottom: 8px; border-left: 4px solid #a259ff; cursor: pointer; background: rgba(162,89,255,0.1);" onclick="openRoomChat(${n.room_id}, '${n.room_name}'); closeNotificationModal();">
                            <div style="font-size: 14px; font-weight: bold; color: #a259ff;">🔔 Anda di-tag oleh ${escapeHtml(n.sender)}</div>
                            <div style="font-size: 12px; color: var(--text-muted);">"${escapeHtml(n.text)}"</div>
                        </div>
                    `;
                }
            });
        }
        
        container.innerHTML = html;
        
    } catch (e) {
        console.error("Gagal load notif:", e);
        container.innerHTML = `<p style="color: red; text-align: center;">Gagal memuat notifikasi.</p>`;
    }
}

// ✅ FUNGSI BUAT MEWARNAI TAG @USERNAME
function formatMentions(text) {
    // 1. Escape HTML dulu biar aman dari XSS
    let safeText = escapeHtml(text);
    
    // 2. Cari pola @username (huruf, angka, underscore)
    // Kita bungkus pakai <span> dengan warna ungu dan background transparan
    const regex = /(@[a-zA-Z0-9_]+)/g;
    
    return safeText.replace(regex, (match) => {
        return `<span style="color: #a259ff; font-weight: 700; background: rgba(162,89,255,0.15); padding: 2px 6px; border-radius: 6px; display: inline-block;">${match}</span>`;
    });
}
// ✅ SISTEM PENYADAP MENTION (REAL-TIME SIMULATION)
let mentionPollingInterval = null;

function startMentionPolling() {
    if (mentionPollingInterval) clearInterval(mentionPollingInterval);
    
    mentionPollingInterval = setInterval(async () => {
        const _user = getUser();
        if (!_user) return;

        try {
            // Tarik pesan terbaru dari room 1 (asumsi room utama)
            const resp = await apiFetch(`${CONFIG.BACKEND_URL}/room/messages/1`, { method: "GET" });
            const data = await resp.json();
            if (!data.success || !data.data) return;

            const mentionKey = `so_mention_${_user.username}`;
            let savedMentions = JSON.parse(localStorage.getItem(mentionKey) || "[]");
            
            let hasNew = false;

            // Scan pesan-pesan terbaru
            data.data.forEach(m => {
                // ✅ FIX BUG #2: Jangan catat notif kalau kita lagi buka room ini
                if (currentRoomId == 1) return; 
                
                // Kalau pesan nge-tag username kita, DAN bukan dari kita sendiri
                if (m.pesan.includes(`@${_user.username}`) && m.user_id !== _user.id) {
                    // Cek apakah pesan ini udah pernah dicatat
                    const isAlreadySaved = savedMentions.some(sm => sm.message_id === m.id);
                    
                    if (!isAlreadySaved) {
                        savedMentions.push({
                            message_id: m.id,
                            room_id: 1,
                            room_name: "Server",
                            sender: m.users?.nama_lengkap || m.users?.username || "User",
                            text: m.pesan,
                            timestamp: new Date(m.created_at || Date.now()).getTime() // ✅ FIX BUG #1: Tambahin timestamp!
                        });
                        hasNew = true;
                    }
                }
            });

            // Kalau ada tag baru, simpan dan update lonceng!
            if (hasNew) {
                localStorage.setItem(mentionKey, JSON.stringify(savedMentions));
                updateNotifBadge(); // Lonceng langsung nambah!
            }

        } catch (e) {
            // Diam aja kalau error (biar gak nyampah di console)
        }
    }, 10000); // Cek tiap 10 detik
}
// ✅ FUNGSI REALTIME WEBSOCKET (ANTI LOOP)
let wsRealtime = null;

function startRealtimeNotifications() {
    const _user = getUser();
    if (!_user) return;

    // ✅ FIX: Kalau udah ada koneksi yang aktif, JANGAN bikin koneksi baru!
    if (wsRealtime && wsRealtime.readyState === WebSocket.OPEN) {
        console.log("✅ WebSocket sudah terhubung, skip.");
        return;
    }

    // Tutup koneksi lama kalau ada (tapi udah gak aktif)
    if (wsRealtime) {
        wsRealtime.close();
    }

    // Pake URL wss://
    const wsUrl = RAW_BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://") + `/api/realtime/ws/${_user.username}`;
    
    console.log("🔌 Menyambungkan ke WebSocket:", wsUrl);
    wsRealtime = new WebSocket(wsUrl);

    wsRealtime.onopen = () => {
        console.log("✅ Terhubung ke Realtime Server!");
    };

    wsRealtime.onmessage = (event) => {
    try {
        const payload = JSON.parse(event.data);
        
        if (payload.event === "new_notification") {
            const notif = payload.data;
            console.log("🔔 NOTIF MASUK (Via WebSocket):", notif);
            
            // 1. Update badge lonceng (panggil API lagi biar akurat)
            updateNotifBadge(); 
            
            // 2. Munculin toast
            if (notif.type === "broadcast") {
                showToastMini(`📢 Broadcast Baru: ${notif.message.substring(0, 30)}...`, "success");
            } else if (notif.type === "mention") {
                showToastMini(`🔔 ${notif.sender_name} nge-tag kamu!`, "success");
            }
            
            // 3. Kalau lagi buka room chat, refresh chat
            if (document.querySelector(".screen.active")?.id === "roomChatScreen" && currentRoomId == notif.room_id) {
                loadRoomMessages();
            }
        }
    } catch (e) {
        console.error("Gagal parse pesan WebSocket:", e);
    }
};
}
// Boot
document.addEventListener("DOMContentLoaded", initApp);