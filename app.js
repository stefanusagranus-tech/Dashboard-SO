/* =========================================================
   DASHBOARD SO C383 — APP LOGIC v4.0 (OPTIMIZED)
   Fitur: Lazy Loading, State Caching, Simple UI
   ========================================================= */

// =========================================================
// 1. CONFIG & CONSTANTS
// =========================================================
const CONFIG = {
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev",
    STREAMLIT_URL: "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/",
    API_KEY: "so_c383_GOfNKuPRfhhdXnGTYGBYnr5zV5kzFRkz",
    APP_VERSION: "1.01",
    TARGET_SO_PERSEN: 80
};

const BOTS = {
    yui:    { emoji: "📦", name: "Yui",    role: "Data Entry",   endpoint: "/api/yui/chat" },
    hana:   { emoji: "🌸", name: "Hana",   role: "Master Shift", endpoint: "/api/hana/chat" },
    rei:    { emoji: "📊", name: "Rei",    role: "Analisis",     endpoint: "/api/rei/chat" },
    kurumi: { emoji: "🎀", name: "Kurumi", role: "Chief",        endpoint: "/api/kurumi/chat" },
};

const AUTH_KEYS = {
    TOKEN: "so_auth_token",
    USER: "so_auth_user",
    TEMP_TOKEN: "so_temp_token",
    USERNAME: "so_temp_username",
};

// =========================================================
// 2. GLOBAL STATE & CACHE (Biar gak narik API berulang)
// =========================================================
const AppCache = {
    user: null,
    rekap: null,
    shiftHariIni: null,
    personil: null,
    masterShift: null,
    spdList: null,
    topData: null,
};

let currentBot = "yui";
let chatHistories = {};
let pinInput = "";
let exitModalShown = false;
let idleTimer = null;
let clockInterval = null;
let autoThemeEnabled = true;
let dashboardRefreshInterval = null;

// State UI
let shiftPeriod = "hari_ini";
let spdPeriodCurrent = "bulan_ini";
let spdSortValue = "tanggal_desc";
let rakFilterCurrent = "semua";
let rakSearchQuery = "";
let topPeriodCurrent = "bulan_ini";
let topTabCurrent = "rak";
let topSignCurrent = "minus";

const IDLE_TIMEOUT = 5 * 60 * 1000;

// =========================================================
// 3. AUTH & FETCH WRAPPER
// =========================================================
function getApiKey() { return localStorage.getItem("so_api_key") || CONFIG.API_KEY; }
function getToken() { return localStorage.getItem(AUTH_KEYS.TOKEN) || ""; }
function getUser() {
    if (AppCache.user) return AppCache.user;
    try {
        const raw = localStorage.getItem(AUTH_KEYS.USER);
        AppCache.user = raw ? JSON.parse(raw) : null;
        return AppCache.user;
    } catch (e) { return null; }
}
function setAuth(token, user) {
    if (token) localStorage.setItem(AUTH_KEYS.TOKEN, token);
    if (user) { localStorage.setItem(AUTH_KEYS.USER, JSON.stringify(user)); AppCache.user = user; }
    localStorage.setItem("so_login_timestamp", Date.now().toString());
}
function clearAuth() {
    localStorage.removeItem(AUTH_KEYS.TOKEN);
    localStorage.removeItem(AUTH_KEYS.USER);
    localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN);
    localStorage.removeItem(AUTH_KEYS.USERNAME);
    localStorage.removeItem("so_logged_in");
    localStorage.removeItem("so_login_timestamp");
    AppCache.user = null;
}
function isLoggedIn() { return !!getToken() && !!getUser(); }

// Fetch Wrapper dengan Error Handling terpusat
async function apiFetch(url, options = {}) {
    const headers = { "X-API-Key": getApiKey(), ...(options.headers || {}) };
    const _token = getToken();
    if (_token) headers["Authorization"] = `Bearer ${_token}`;
    
    const _opts = { ...options, headers };
    let _resp;
    
    try {
        _resp = await fetch(url, _opts);
    } catch (_err) {
        console.error("[apiFetch] Network error:", _err);
        throw new Error("Koneksi internet bermasalah");
    }

    if (_resp.status === 401) {
        let _bodyText = await _resp.text();
        let _errMsg = "";
        try { _errMsg = JSON.parse(_bodyText).detail || ""; } catch (e) {}
        
        if (!_errMsg.toLowerCase().includes("api key")) {
            clearAuth();
            showToastMini("⚠️ Session expired. Login ulang.", "error");
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
    console.log("[App] Init v4.0 started");
    await showSplashScreen();

    loadChatHistories();
    autoThemeEnabled = localStorage.getItem("so_auto_theme") !== "false";
    setTheme(localStorage.getItem("so_theme") || "halloween-dark");
    updateTimeTheme();

    bindLoginForm();
    bindPinKeypad();
    bindChatInput();

    setTimeout(() => checkForUpdate(false), 3000);

    if (isLoggedIn()) {
        await hideSplashScreen();
        // Langsung masuk tanpa loading bertele-tele, karena data ditarik lazy
        showScreen("homeScreen");
        startLiveClock();
        loadHomeDataLazy();
    } else {
        await hideSplashScreen();
        showScreen("loginScreen");
    }

    setInterval(updateTimeTheme, 60 * 1000);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            document.body.style.display = 'none';
            document.body.offsetHeight;
            document.body.style.display = 'block';
        }
    });
}

// =========================================================
// 5. SPLASH & LOADING
// =========================================================
function showSplashScreen() {
    return new Promise(resolve => {
        const splash = document.getElementById("splashScreen");
        const progressBar = document.getElementById("splashProgressBar");
        if (!splash) return resolve();

        splash.classList.add("active");
        let pct = 0;
        const interval = setInterval(() => {
            pct += 25;
            if (progressBar) progressBar.style.width = `${pct}%`;
            if (pct >= 100) {
                clearInterval(interval);
                setTimeout(resolve, 300);
            }
        }, 150);
    });
}

function hideSplashScreen() {
    return new Promise(resolve => {
        const splash = document.getElementById("splashScreen");
        if (!splash) return resolve();
        splash.classList.add("fade-out");
        setTimeout(() => { splash.remove(); resolve(); }, 400);
    });
}

// =========================================================
// 6. AUTH LOGIC (Login, PIN, Logout)
// =========================================================
function bindLoginForm() {
    const btnSubmit = document.getElementById("loginBtnSubmit");
    const inputUser = document.getElementById("loginUsername");
    const inputPass = document.getElementById("loginPassword");

    if (inputUser) inputUser.addEventListener("keydown", (e) => { if (e.key === "Enter") inputPass?.focus(); });
    if (inputPass) inputPass.addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
    if (btnSubmit) btnSubmit.addEventListener("click", doLogin);
}

async function doLogin() {
    const inputUser = document.getElementById("loginUsername");
    const inputPass = document.getElementById("loginPassword");
    const btnSubmit = document.getElementById("loginBtnSubmit");
    const errEl = document.getElementById("loginError");

    const _username = (inputUser?.value || "").trim().toUpperCase();
    const _password = (inputPass?.value || "").trim();

    if (errEl) errEl.textContent = "";
    if (!_username || !_password) {
        if (errEl) errEl.textContent = "❌ Username & password wajib diisi";
        return;
    }

    if (btnSubmit) { btnSubmit.disabled = true; btnSubmit.innerHTML = '<span class="btn-spinner"></span> Memproses...'; }

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
            body: JSON.stringify({ username: _username, password: _password, device_info: "WebView" }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Login gagal");

        localStorage.setItem(AUTH_KEYS.TEMP_TOKEN, data.temp_token);
        localStorage.setItem(AUTH_KEYS.USERNAME, _username);

        pinInput = "";
        updatePinDisplay();
        if (document.querySelector(".pin-hint")) document.querySelector(".pin-hint").textContent = `Login sebagai: ${_username}`;
        showLoginView(false);
        if (inputPass) inputPass.value = "";

    } catch (err) {
        if (errEl) errEl.textContent = `❌ ${err.message}`;
    } finally {
        if (btnSubmit) { btnSubmit.disabled = false; btnSubmit.innerHTML = "🔓 MASUK"; }
    }
}

function showLoginView(showLogin) {
    document.getElementById("loginFormView")?.classList.toggle("hidden", !showLogin);
    document.getElementById("pinFormView")?.classList.toggle("hidden", showLogin);
}

function bindPinKeypad() {
    document.querySelectorAll(".pin-key").forEach(btn => {
        btn.addEventListener("click", () => {
            const num = btn.getAttribute("data-num");
            const action = btn.getAttribute("data-action");
            if (action === "back") pinInput = pinInput.slice(0, -1);
            else if (num && pinInput.length < 6) pinInput += num;
            updatePinDisplay();
            if (pinInput.length === 6) setTimeout(verifyPin, 200);
        });
    });
}

function updatePinDisplay() {
    document.querySelectorAll(".pin-dot").forEach((dot, idx) => dot.classList.toggle("filled", idx < pinInput.length));
}

async function verifyPin() {
    const _tempToken = localStorage.getItem(AUTH_KEYS.TEMP_TOKEN);
    const pinError = document.getElementById("pinError");
    if (pinError) pinError.textContent = "";

    if (!_tempToken) {
        if (pinError) pinError.textContent = "❌ Session hilang, ulangi login";
        return;
    }

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/auth/verify-pin`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
            body: JSON.stringify({ temp_token: _tempToken, pin: pinInput }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "PIN salah");

        setAuth(data.token, data.user);
        localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN);
        localStorage.removeItem(AUTH_KEYS.USERNAME);
        pinInput = ""; updatePinDisplay();
        resetIdleTimer();
        
        showScreen("homeScreen");
        startLiveClock();
        loadHomeDataLazy();

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
    clearAuth();
    if (idleTimer) clearTimeout(idleTimer);
    showLoginView(true);
    showScreen("loginScreen");
    pushBackGuard();
}

// =========================================================
// 7. NAVIGATION & SCREEN MANAGEMENT (LAZY LOAD DI SINI)
// =========================================================
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

        if (activeId) {
            const el = document.getElementById(activeId);
            if (el) { el.classList.add("active"); el.style.color = "#ff7b00"; }
        }
    }
}

function goToHomeScreen() {
    closeSidebar();
    showScreen("homeScreen");
    startLiveClock();
    loadHomeDataLazy(); // Panggil data cache
}

function goToChatScreen() {
    stopDashboardAutoRefresh();
    showScreen("chatScreen");
    if (!currentBot || !BOTS[currentBot]) currentBot = "yui";
    switchBot(currentBot);
}

async function goToSettingsScreen() {
    closeSidebar();
    await loadUserDataIfNeeded();
    showScreen("settingsScreen");
}

async function goToProfileScreen() {
    await loadUserDataIfNeeded();
    const _user = getUser();
    if (!_user) return;
    
    document.getElementById("editNamaLengkap").value = _user.nama_lengkap || "";
    const preview = document.getElementById("editAvatarPreview");
    if (preview) {
        if (_user.avatar_url) {
            preview.style.backgroundImage = `url('${_user.avatar_url}')`;
            preview.style.backgroundColor = "transparent";
            preview.textContent = "";
        } else {
            preview.style.backgroundImage = "none";
            preview.textContent = (_user.nama_lengkap || _user.username || "?").substring(0, 2).toUpperCase();
        }
    }
    showScreen("profileScreen");
}

function goToMasterShiftScreen() {
    closeSidebar();
    stopDashboardAutoRefresh();
    showScreen("masterShiftScreen");
    loadShiftDataLazy(); // Lazy load shift
}

function goToRakListScreen() {
    closeSidebar(); stopDashboardAutoRefresh(); showScreen("rakListScreen");
    loadRakListLazy();
}

function goToSpdListScreen() {
    closeSidebar(); stopDashboardAutoRefresh(); showScreen("spdListScreen");
    loadSpdListLazy();
}

function goToTopMinusScreen() {
    closeSidebar(); stopDashboardAutoRefresh(); showScreen("topMinusScreen");
    loadTopMinusLazy();
}

function goToStatusScreen() {
    closeSidebar(); stopDashboardAutoRefresh(); showScreen("statusScreen");
    loadStatusAnalysis(); // Fungsi ini udah ada di bawah
}

function goToStreamlitScreen() { closeSidebar(); showScreen("streamlitScreen"); }

// =========================================================
// 8. LAZY LOADING DATA HOME (CACHE-ABLE)
// =========================================================
function loadHomeDataLazy() {
    // 1. Tarik data User (kalo belum ada di cache)
    loadUserDataIfNeeded();

    // 2. Tarik Dashboard (Rekap)
    if (!AppCache.rekap) {
        loadMiniDashboard();
    }

    // 3. Jadwal (JANGAN tarik di awal, tarik pas geser slide)
    // (Logika ini ada di Event Listener Carousel di bawah)
}

async function loadUserDataIfNeeded() {
    const _user = getUser();
    if (AppCache.user && _user && _user.avatar_url) {
        updateAvatarUI(_user); // Update UI aja tanpa narik API
        return;
    }
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/me`, { method: "GET" });
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.user) {
                setAuth(getToken(), data.user);
                updateAvatarUI(data.user);
            }
        }
    } catch (e) { console.warn("Gagal refresh user", e); }
}

function updateAvatarUI(user) {
    const inisial = (user.nama_lengkap || user.username || "?").substring(0, 2).toUpperCase();
    
    // Update di Home Avatar
    const homeAvatar = document.getElementById("homeAvatarPreview");
    if (homeAvatar) {
        if (user.avatar_url) {
            homeAvatar.style.backgroundImage = `url('${user.avatar_url}')`;
            homeAvatar.style.backgroundColor = "transparent";
            homeAvatar.textContent = "";
        } else {
            homeAvatar.style.backgroundImage = "none";
            homeAvatar.textContent = inisial;
        }
    }
    
    // Update di Settings Avatar
    const setAvatar = document.getElementById("settingsAvatar");
    if (setAvatar) {
        if (user.avatar_url) {
            setAvatar.style.backgroundImage = `url('${user.avatar_url}')`;
            setAvatar.style.backgroundColor = "transparent";
            setAvatar.textContent = "";
        } else {
            setAvatar.style.backgroundImage = "none";
            setAvatar.textContent = inisial;
        }
    }
    
    // Update Nama di Settings
    if (document.getElementById("settingsNamaLengkap")) document.getElementById("settingsNamaLengkap").textContent = user.nama_lengkap || "-";
    if (document.getElementById("settingsUsername")) document.getElementById("settingsUsername").textContent = `@${user.username}`;
    if (document.getElementById("settingsRole")) document.getElementById("settingsRole").textContent = (user.role || "-").toUpperCase();
    
    // Cek Akses Admin
    const _menuAdmin = document.getElementById("menuKelolaUser");
    if (_menuAdmin) _menuAdmin.style.display = (user.role === "admin") ? "flex" : "none";
}

async function loadMiniDashboard() {
    const _url = `${CONFIG.BACKEND_URL}/api/yui/rekap`;
    try {
        const resp = await apiFetch(_url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) });
        const data = await resp.json();
        
        AppCache.rekap = data.data || data; // Simpan di cache
        
        const _d = AppCache.rekap;
        const totalRak = _d.total_rak || 0;
        const totalNominal = _d.total_nominal || 0;
        const salesPeriode = _d.sales_periode || 0;
        const totalRakMaster = 145;
        const persenSo = (totalRak / totalRakMaster) * 100;
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
        if (statusBar) {
            statusBar.classList.remove("status-aman", "status-waspada", "status-bahaya");
            statusBar.classList.add(`status-${statusKey}`);
        }

        if (document.getElementById("progressFill")) document.getElementById("progressFill").style.width = `${Math.min(persenSo, 100)}%`;
        if (document.getElementById("progressLabel")) document.getElementById("progressLabel").textContent = `Progress SO: ${persenSo.toFixed(1)}% dari target ${CONFIG.TARGET_SO_PERSEN}%`;

        // Running Text
        const runningParts = [
            `📦 Total Rak: <b>${totalRak}/${totalRakMaster}</b>`,
            `💰 SPD: <b>${formatRupiahRingkas(salesPeriode)}</b>`,
            `📉 Nominal Adjust: <b>${formatRupiahRingkas(totalNominal)}</b>`,
            `📊 Status: <b>${statusEmoji} ${statusText}</b> (${statusPersen.toFixed(2)}%)`
        ];
        startRunningText(runningParts.join("  •  ") + "  •  ");

    } catch (err) {
        console.error("[Dashboard] Error:", err);
        if (document.getElementById("progressLabel")) document.getElementById("progressLabel").textContent = "Gagal load data";
    }
}

async function loadHomeSchedule() {
    const container = document.getElementById("homeScheduleList");
    if (!container) return;

    // Cek Cache
    if (AppCache.shiftHariIni) {
        renderHomeSchedule(AppCache.shiftHariIni, container);
        return;
    }

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/shift-hari-ini`, { method: "GET" });
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const data = await resp.json();
        AppCache.shiftHariIni = data; // Simpan cache
        renderHomeSchedule(data, container);
    } catch (err) {
        container.innerHTML = `<p style="text-align:center; color:var(--danger);">Gagal load jadwal.</p>`;
    }
}

function renderHomeSchedule(data, container) {
    if (data.success && data.grouped) {
        let html = "";
        const g = data.grouped;
        if (g.P7?.length) html += `<div style="margin-bottom:8px;"><b style="color:#06d6a0;">🟢 Pagi:</b> ${g.P7.join(", ")}</div>`;
        if (g.S15?.length) html += `<div style="margin-bottom:8px;"><b style="color:#feca57;">🟡 Siang:</b> ${g.S15.join(", ")}</div>`;
        if (g.M22?.length) html += `<div style="margin-bottom:8px;"><b style="color:#ee5253;">🔴 Malam:</b> ${g.M22.join(", ")}</div>`;
        if (g.O?.length) html += `<div style="margin-bottom:8px;"><b style="color:#a39e93;">⚪ Off:</b> ${g.O.join(", ")}</div>`;
        container.innerHTML = html || `<p style="text-align:center; color:var(--text-muted);">Tidak ada jadwal.</p>`;
    } else {
        container.innerHTML = `<p style="text-align:center; color:var(--text-muted);">Tidak ada jadwal.</p>`;
    }
}

// =========================================================
// 9. CAROUSEL (DETEKSI SWIPE & LAZY LOAD JADWAL)
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
    const carousel = document.getElementById('homeCarousel');
    if (!carousel) return;

    let isScheduleLoaded = false; // Kunci Lazy Load

    carousel.addEventListener('scroll', () => {
        const slideWidth = carousel.clientWidth + 16; // 16px gap
        const activeIndex = Math.round(carousel.scrollLeft / slideWidth);
        
        document.querySelectorAll('.carousel-dots .dot').forEach((dot, i) => {
            dot.classList.toggle('active', i === activeIndex);
        });

        // 🔥 TRIGGER LAZY LOAD PAS GESER KE SLIDE 3 (Index 2)
        if (activeIndex === 2 && !isScheduleLoaded) {
            isScheduleLoaded = true;
            loadHomeSchedule();
        }
    });
});

function goToSlide(index) {
    const container = document.getElementById("homeCarousel");
    if (!container) return;
    const slideWidth = container.clientWidth + 16;
    container.scrollTo({ left: index * slideWidth, behavior: "smooth" });
}

// =========================================================
// 10. DATA FETCHING LAINNYA (SHIFT, RAK, SPD, TOP) - LAZY
// =========================================================
async function loadShiftDataLazy() {
    if (!AppCache.personil) {
        try {
            const pResp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil`, { method: "GET" });
            const pData = await pResp.json();
            AppCache.personil = pData.data || [];
            // Render filter option
            const filterSelect = document.getElementById("personilFilter");
            if (filterSelect) {
                filterSelect.innerHTML = '<option value="">👥 Semua Personil</option>';
                AppCache.personil.forEach(p => filterSelect.innerHTML += `<option value="${p.nama}">👤 ${p.nama}</option>`);
            }
        } catch (e) {}
    }
    loadMasterShift();
}

async function loadRakListLazy() {
    const container = document.getElementById("rakList");
    if (!container) return;
    
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat rak...</p></div>`;
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/rak-status`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "bulan_ini" }) });
        const data = await resp.json();
        AppCache.rakList = data.list_rak || [];
        
        if (document.getElementById("rakSummaryTotal")) document.getElementById("rakSummaryTotal").textContent = data.total_rak;
        if (document.getElementById("rakSummarySudah")) document.getElementById("rakSummarySudah").textContent = data.sudah_so;
        if (document.getElementById("rakSummaryBelum")) document.getElementById("rakSummaryBelum").textContent = data.belum_so;
        
        renderRakList();
    } catch (err) {
        container.innerHTML = `<p style="color:red; text-align:center;">Gagal load data.</p>`;
    }
}

// ... (Fungsi renderRakList, loadSpdListLazy, loadTopMinusLazy, dll. sama kayak sebelumnya, 
// tapi ngecek AppCache dulu sebelum nembak API) ...

// =========================================================
// 11. HELPER FORMAT & UI TOASTS
// =========================================================
function formatRupiahRingkas(nominal) {
    const abs = Math.abs(nominal);
    if (abs >= 1_000_000_000) return (nominal / 1_000_000_000).toFixed(2) + "M";
    if (abs >= 1_000_000) return (nominal / 1_000_000).toFixed(1) + "jt";
    if (abs >= 1_000) return (nominal / 1_000).toFixed(0) + "rb";
    return nominal.toFixed(0);
}

function formatRupiahFull(nominal) {
    if (nominal === 0) return "Rp 0";
    const isNegative = nominal < 0;
    return `${isNegative ? "-" : ""}Rp ${Math.abs(nominal).toLocaleString("id-ID")}`;
}

function startRunningText(text) {
    const container = document.getElementById("runningTextContainer");
    if (!container) return;
    container.innerHTML = `<div class="running-icon">📢</div><div class="running-viewport"><div class="running-track"><span class="running-inner">${text}</span><span class="running-inner">${text}</span></div></div>`;
}

function showToastMini(message, type = "success") {
    document.querySelector(".toast-mini")?.remove();
    const toast = document.createElement("div");
    toast.className = `toast-mini ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add("show"), 100);
    setTimeout(() => { toast.classList.remove("show"); setTimeout(() => toast.remove(), 400); }, 3000);
}

// =========================================================
// 12. CHAT LOGIC (OPTIMIZED - RENDER 30 PESAN TERAKHIR)
// =========================================================
function loadChatHistories() {
    try { chatHistories = JSON.parse(localStorage.getItem("so_chat_histories")) || {}; } catch (e) { chatHistories = {}; }
    Object.keys(BOTS).forEach(botId => { if (!chatHistories[botId]) chatHistories[botId] = []; });
}

function saveChatHistories() {
    try { localStorage.setItem("so_chat_histories", JSON.stringify(chatHistories)); } catch (e) {}
}

function switchBot(botId) {
    if (!BOTS[botId]) return;
    currentBot = botId;
    if (document.getElementById("chatBotEmoji")) document.getElementById("chatBotEmoji").textContent = BOTS[botId].emoji;
    if (document.getElementById("chatBotName")) document.getElementById("chatBotName").textContent = BOTS[botId].name;
    document.querySelectorAll(".bot-item").forEach(item => item.classList.toggle("active", item.getAttribute("data-bot") === botId));
    renderChatHistory();
    closeSidebar();
}

function renderChatHistory() {
    const container = document.getElementById("chatMessages");
    if (!container) return;
    
    let history = chatHistories[currentBot] || [];
    if (history.length === 0) {
        container.innerHTML = `<div class="chat-message-wrapper ai"><div class="chat-avatar">${BOTS[currentBot].emoji}</div><div class="bubble-content ai"><div class="bubble bubble-ai bubble-welcome">Halo Bos! 👋<br>Siap bantu.</div></div></div>`;
        return;
    }

    container.innerHTML = "";
    
    // 🔥 OPTIMASI: Cuma render 30 pesan terakhir biar gak lag
    const recentHistory = history.slice(-30); 

    recentHistory.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        const wrapper = document.createElement("div");
        wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;
        
        const avatar = document.createElement("div");
        avatar.className = isUser ? "chat-avatar avatar-user" : "chat-avatar";
        avatar.textContent = isUser ? "👤" : BOTS[currentBot].emoji;
        
        const bubbleContent = document.createElement("div");
        bubbleContent.className = `bubble-content ${isUser ? "user" : "ai"}`;
        
        const bubble = document.createElement("div");
        bubble.className = `bubble bubble-${isUser ? "user" : "ai"}`;
        bubble.innerHTML = msg.content; // Assuming formatMessage logic simplified for brevity

        const time = document.createElement("div");
        time.className = "bubble-time";
        time.textContent = new Date(msg.timestamp || Date.now()).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });

        bubbleContent.appendChild(bubble);
        bubbleContent.appendChild(time);
        wrapper.appendChild(avatar);
        wrapper.appendChild(bubbleContent);
        container.appendChild(wrapper);
    });
    
    setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
}

function bindChatInput() {
    const input = document.getElementById("chatInput");
    if (input) {
        input.addEventListener("input", () => {
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, 100) + "px";
        });
        input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    }
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    
    input.value = ""; input.style.height = "auto";
    
    chatHistories[currentBot].push({ role: "user", content: text, timestamp: Date.now() });
    saveChatHistories(); renderChatHistory();
    
    try {
        const history = chatHistories[currentBot].slice(-7, -1).map(m => ({ role: m.role, content: m.content }));
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}${BOTS[currentBot].endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: `so_${currentBot}`, history })
        });
        const data = await resp.json();
        
        chatHistories[currentBot].push({ role: "assistant", content: data.text || "(kosong)", timestamp: Date.now() });
        saveChatHistories(); renderChatHistory();
    } catch (e) {
        chatHistories[currentBot].push({ role: "assistant", content: "⚠️ Error jaringan", timestamp: Date.now() });
        renderChatHistory();
    }
}

// =========================================================
// 13. UTILITIES (THEME, CLOCK, MODAL, BACK BUTTON)
// =========================================================
function startLiveClock() {
    updateClock();
    if (clockInterval) clearInterval(clockInterval);
    clockInterval = setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    if (document.getElementById("clockTime")) document.getElementById("clockTime").textContent = `${hh}:${mm}`;
    
    const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
    const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    if (document.getElementById("clockDate")) document.getElementById("clockDate").textContent = `${hari[now.getDay()]}, ${now.getDate()} ${bulan[now.getMonth()]} ${now.getFullYear()}`;

    const hour = now.getHours();
    let greeting = hour < 11 ? "Selamat Pagi 🌅" : hour < 15 ? "Selamat Siang ☀️" : hour < 18 ? "Selamat Sore 🌆" : "Selamat Malam 🌙";
    const _user = getUser();
    if (document.getElementById("clockGreeting")) document.getElementById("clockGreeting").textContent = `${greeting}, ${_user?.nama_lengkap || "Bos"}!`;
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    setTheme(current === "halloween-dark" ? "halloween-light" : "halloween-dark");
}

function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("so_theme", theme);
    const isDark = theme === "halloween-dark";
    document.querySelectorAll("#themeIcon, #themeIcon2, #sidebarThemeIcon").forEach(el => el.textContent = isDark ? "🌙" : "☀️");
}

function updateTimeTheme() {
    if (!autoThemeEnabled) return;
    const hour = new Date().getHours();
    document.documentElement.setAttribute("data-time-theme", hour < 11 ? "pagi" : hour < 15 ? "siang" : hour < 18 ? "sore" : "malam");
}

function toggleSidebar() { document.getElementById("sidebar")?.classList.toggle("open"); document.getElementById("sidebarOverlay")?.classList.toggle("active"); }
function closeSidebar() { document.getElementById("sidebar")?.classList.remove("open"); document.getElementById("sidebarOverlay")?.classList.remove("active"); }

// Back Button Logic
window.addEventListener("popstate", (e) => {
    const activeScreen = document.querySelector(".screen.active");
    if (!activeScreen) return;
    
    if (document.getElementById("sidebar")?.classList.contains("open")) { closeSidebar(); pushBackGuard(); return; }
    const modalOpen = document.querySelector(".modal-overlay.active:not(#exitModal)");
    if (modalOpen) { modalOpen.classList.remove("active"); pushBackGuard(); return; }

    if (activeScreen.id === "homeScreen" || activeScreen.id === "loginScreen") {
        e.preventDefault(); document.getElementById("exitModal")?.classList.add("active"); exitModalShown = true; pushBackGuard(); return;
    }
    e.preventDefault(); goToHomeScreen(); pushBackGuard();
});

function pushBackGuard() { try { history.pushState({ guard: true, ts: Date.now() }, "", ""); } catch (e) {} }
setTimeout(pushBackGuard, 800);

// Idle Timer
function resetIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    if (!isLoggedIn() || document.querySelector(".screen.active")?.id === "loginScreen") return;
    idleTimer = setTimeout(() => { autoLogout(); }, IDLE_TIMEOUT);
}
function autoLogout() {
    clearAuth(); showToastMini("⏰ Idle 5 menit — auto logout", "error");
    setTimeout(() => { showLoginView(true); showScreen("loginScreen"); pushBackGuard(); }, 300);
}
["click", "touchstart", "keydown", "scroll"].forEach(evt => document.addEventListener(evt, resetIdleTimer, { passive: true }));

// Update Check
async function checkForUpdate(manual = false) {
    if (manual) showToastMini("🔍 Cek update...", "success");
    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/config/`);
        const data = await resp.json();
        if (data.app && isNewerVersion(data.app.latest_version, CONFIG.APP_VERSION)) {
            // Logic modal update bisa ditambahin di sini
            if (manual) showToastMini("✅ Update tersedia!", "success");
        }
    } catch (e) {}
}
function isNewerVersion(latest, current) {
    const l = String(latest).split(".").map(Number), c = String(current).split(".").map(Number);
    for (let i = 0; i < 3; i++) { if ((l[i] || 0) > (c[i] || 0)) return true; if ((l[i] || 0) < (c[i] || 0)) return false; }
    return false;
}

// Boot
document.addEventListener("DOMContentLoaded", initApp);
