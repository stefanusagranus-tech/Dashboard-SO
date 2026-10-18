/* =========================================================
   DASHBOARD SO C383 — APP LOGIC v3.0
   Sprint 3 PART 3: Login + PIN 2FA + Token Management
   ========================================================= */

// =========================================================
// CONFIG
// =========================================================
const CONFIG = {
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev",
    STREAMLIT_URL: "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/",
    API_KEY: "so_c383_GOfNKuPRfhhdXnGTYGBYnr5zV5kzFRkV",
    APP_VERSION: "1.0.0",
    TARGET_SO_PERSEN: 70,
};

const BOTS = {
    yui:    { emoji: "📦", name: "Yui",    role: "Data Entry",   endpoint: "/api/yui/chat" },
    hana:   { emoji: "🌸", name: "Hana",   role: "Master Shift", endpoint: "/api/hana/chat" },
    rei:    { emoji: "📊", name: "Rei",    role: "Analisis",     endpoint: "/api/rei/chat" },
    kurumi: { emoji: "🎀", name: "Kurumi", role: "Chief",        endpoint: "/api/kurumi/chat" },
};

// =========================================================
// AUTH STORAGE KEYS
// =========================================================
const AUTH_KEYS = {
    TOKEN: "so_auth_token",
    USER: "so_auth_user",
    TEMP_TOKEN: "so_temp_token",
    USERNAME: "so_temp_username",
};

// =========================================================
// STATE
// =========================================================
let pinInput = "";
let loginUsername = "";
let loginPassword = "";
let currentBot = "yui";
let chatHistories = {};
let clockInterval = null;
let dashboardRefreshInterval = null;
let autoThemeEnabled = true;
let exitModalShown = false;
let idleTimer = null;
let updateInfo = null;
let toastTimer = null;

let _personilCache = null;
let _personilCacheTime = 0;

window._pendingUploadSo = null;
window._pendingSpd = null;

let shiftPeriod = "hari_ini";
let masterShiftData = [];
let personilData = [];

let spdListData = [];
let spdPeriodCurrent = "bulan_ini";
let spdSortValue = "tanggal_desc";

let rakListData = [];
let rakFilterCurrent = "semua";
let rakSearchQuery = "";

let topData = [];
let topPeriodCurrent = "bulan_ini";
let topSortValue = "tanggal_desc";
let topTabCurrent = "rak";
let topSearchQuery = "";
let topSignCurrent = "minus";
let topSearchTimeout = null;

let rakDetailData = [];
let rakDetailCurrentRak = null;
let rakDetailFilter = "semua";
let rakDetailSearchQuery = "";

let statusPeriodCurrent = "bulan_ini";
let currentConfirmData = null;

const IDLE_TIMEOUT = 5 * 60 * 1000;

// =========================================================
// AUTH HELPERS
// =========================================================
function getApiKey() {
    return localStorage.getItem("so_api_key") || CONFIG.API_KEY;
}

function getToken() {
    return localStorage.getItem(AUTH_KEYS.TOKEN) || "";
}

function getUser() {
    try {
        const raw = localStorage.getItem(AUTH_KEYS.USER);
        return raw ? JSON.parse(raw) : null;
    } catch (e) {
        return null;
    }
}

function setAuth(token, user) {
    if (token) localStorage.setItem(AUTH_KEYS.TOKEN, token);
    if (user) localStorage.setItem(AUTH_KEYS.USER, JSON.stringify(user));
    localStorage.setItem("so_login_timestamp", Date.now().toString());
}

function clearAuth() {
    localStorage.removeItem(AUTH_KEYS.TOKEN);
    localStorage.removeItem(AUTH_KEYS.USER);
    localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN);
    localStorage.removeItem(AUTH_KEYS.USERNAME);
    localStorage.removeItem("so_logged_in");
    localStorage.removeItem("so_login_timestamp");
}

function isLoggedIn() {
    return !!getToken() && !!getUser();
}

// =========================================================
// FETCH WRAPPER — Auto-attach X-API-Key + Bearer token
// =========================================================
async function apiFetch(url, options = {}) {
    const headers = {
        "X-API-Key": getApiKey(),
        ...(options.headers || {}),
    };
    
    const _token = getToken();
    if (_token) {
        headers["Authorization"] = `Bearer ${_token}`;
    }
    
    const _opts = { ...options, headers };
    
    let _resp;
    try {
        _resp = await fetch(url, _opts);
    } catch (_err) {
        console.error("[apiFetch] Network error:", _err);
        throw _err;
    }

    // Handle 401 — TAPI jangan clear auth kalau errornya API key
    if (_resp.status === 401) {
        let _bodyText = "";
        try {
            _bodyText = await _resp.text();
        } catch (e) {}
        
        let _errMsg = "";
        try {
            const _parsed = JSON.parse(_bodyText);
            _errMsg = _parsed.message || _parsed.detail || "";
        } catch (e) {}
        
        // Auto logout kalau BUKAN API key issue
        if (!_errMsg.toLowerCase().includes("api key")) {
            console.warn("[Auth] 401 — auto logout:", _errMsg);
            clearAuth();
            showToastMini("⚠️ Session expired. Silakan login ulang.", "error");
            setTimeout(() => showScreen("loginScreen"), 800);
        }
        
        // Return response baru (biar caller bisa baca body)
        return new Response(_bodyText, {
            status: _resp.status,
            statusText: _resp.statusText,
            headers: _resp.headers,
        });
    }

    return _resp;
}
// =========================================================
// INIT
// =========================================================
async function initApp() {
    console.log("[App] Init started");
    await showSplashScreen();

    loadChatHistories();
    autoThemeEnabled = localStorage.getItem("so_auto_theme") !== "false";
    const savedTheme = localStorage.getItem("so_theme") || "halloween-dark";
    setTheme(savedTheme);
    updateTimeTheme();
    updateApiKeyDisplay();
    updateAutoThemeDisplay();

    bindLoginForm();
    bindPinKeypad();
    bindChatInput();

    setTimeout(() => checkForUpdate(false), 3000);

    if (isLoggedIn()) {
        console.log("[Auth] Token found — auto-login");
        resetIdleTimer();
        await loadDashboardWithLoading();
    } else {
        console.log("[Auth] Need login");
        await hideSplashScreen();
        showScreen("loginScreen");
    }

    setInterval(updateTimeTheme, 60 * 1000);
    console.log("[App] Init done");
}

// =========================================================
// SPLASH SCREEN
// =========================================================
function showSplashScreen() {
    return new Promise(resolve => {
        const splash = document.getElementById("splashScreen");
        const progressBar = document.getElementById("splashProgressBar");
        const statusEl = document.getElementById("splashStatus");

        if (!splash) { resolve(); return; }
        splash.classList.add("active");

        const steps = [
            { pct: 20, msg: "Menyiapkan aplikasi..." },
            { pct: 50, msg: "Memuat konfigurasi..." },
            { pct: 80, msg: "Hampir siap..." },
            { pct: 100, msg: "Siap!" },
        ];

        const startTime = Date.now();
        const MIN_DURATION = 1200;
        let i = 0;

        const interval = setInterval(() => {
            if (i < steps.length) {
                const step = steps[i];
                if (progressBar) progressBar.style.width = `${step.pct}%`;
                if (statusEl) statusEl.textContent = step.msg;
                i++;
            } else {
                clearInterval(interval);
                const elapsed = Date.now() - startTime;
                const remaining = Math.max(0, MIN_DURATION - elapsed);
                setTimeout(resolve, remaining);
            }
        }, 300);
    });
}

function hideSplashScreen() {
    return new Promise(resolve => {
        const splash = document.getElementById("splashScreen");
        if (!splash) { resolve(); return; }
        splash.classList.add("fade-out");
        setTimeout(() => {
            splash.remove();
            resolve();
        }, 400);
    });
}

// =========================================================
// LOGIN FORM (username + password)
// =========================================================
function bindLoginForm() {
    const btnSubmit = document.getElementById("loginBtnSubmit");
    const inputUser = document.getElementById("loginUsername");
    const inputPass = document.getElementById("loginPassword");

    if (inputUser) {
        inputUser.addEventListener("input", () => {
            loginUsername = inputUser.value.trim();
        });
        inputUser.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                inputPass && inputPass.focus();
            }
        });
    }

    if (inputPass) {
        inputPass.addEventListener("input", () => {
            loginPassword = inputPass.value;
        });
        inputPass.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                doLogin();
            }
        });
    }

    if (btnSubmit) {
        btnSubmit.addEventListener("click", doLogin);
    }
}

async function doLogin() {
    const inputUser = document.getElementById("loginUsername");
    const inputPass = document.getElementById("loginPassword");
    const btnSubmit = document.getElementById("loginBtnSubmit");
    const errEl = document.getElementById("loginError");

    const _username = (inputUser ? inputUser.value : "").trim().toUpperCase();
    const _password = (inputPass ? inputPass.value : "").trim();

    if (errEl) errEl.textContent = "";

    if (!_username || !_password) {
        if (errEl) errEl.textContent = "❌ Username & password wajib diisi";
        return;
    }

    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<span class="btn-spinner"></span> Memproses...';
    }

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": getApiKey(),
            },
            body: JSON.stringify({
                username: _username,
                password: _password,
                device_info: "WebView APK",
            }),
        });

        const data = await resp.json();

        if (!resp.ok || !data.success) {
            throw new Error(data.detail || "Username atau password salah");
        }

        // Simpan temp_token + user
        localStorage.setItem(AUTH_KEYS.TEMP_TOKEN, data.temp_token);
        localStorage.setItem(AUTH_KEYS.USERNAME, _username);

        // Pindah ke PIN screen
        pinInput = "";
        updatePinDisplay();
        const pinError = document.getElementById("pinError");
        if (pinError) pinError.textContent = "";
        const pinHint = document.querySelector(".pin-hint");
        if (pinHint) pinHint.textContent = `Login sebagai: ${_username}`;

        showScreen("loginScreen");
        // Toggle view login vs pin
        showLoginView(false);

        if (inputPass) inputPass.value = "";
        loginPassword = "";

    } catch (err) {
        console.error("[Login] Error:", err);
        if (errEl) errEl.textContent = `❌ ${err.message}`;
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = "🔓 MASUK";
        }
    }
}

function showLoginView(showLogin) {
    const viewLogin = document.getElementById("loginFormView");
    const viewPin = document.getElementById("pinFormView");
    if (viewLogin) {
        if (showLogin) viewLogin.classList.remove("hidden");
        else viewLogin.classList.add("hidden");
    }
    if (viewPin) {
        if (showLogin) viewPin.classList.add("hidden");
        else viewPin.classList.remove("hidden");
    }
}

function backToLogin() {
    localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN);
    localStorage.removeItem(AUTH_KEYS.USERNAME);
    pinInput = "";
    updatePinDisplay();
    showLoginView(true);
}

// =========================================================
// PIN LOGIN (2FA)
// =========================================================
function bindPinKeypad() {
    document.querySelectorAll(".pin-key").forEach(btn => {
        btn.addEventListener("click", () => {
            const num = btn.getAttribute("data-num");
            const action = btn.getAttribute("data-action");

            if (action === "back") {
                pinInput = pinInput.slice(0, -1);
            } else if (num && pinInput.length < 6) {
                pinInput += num;
            }

            updatePinDisplay();
            checkPinComplete();
        });
    });
}

function updatePinDisplay() {
    document.querySelectorAll(".pin-dot").forEach((dot, idx) => {
        dot.classList.toggle("filled", idx < pinInput.length);
    });
}

function checkPinComplete() {
    const pinError = document.getElementById("pinError");
    if (pinError) pinError.textContent = "";

    if (pinInput.length === 6) {
        setTimeout(verifyPin, 200);
    }
}

async function verifyPin() {
    const _tempToken = localStorage.getItem(AUTH_KEYS.TEMP_TOKEN);
    const _username = localStorage.getItem(AUTH_KEYS.USERNAME) || "ADMIN";

    if (!_tempToken) {
        const pinError = document.getElementById("pinError");
        if (pinError) pinError.textContent = "❌ Session login hilang, ulangi login";
        pinInput = "";
        updatePinDisplay();
        return;
    }

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/auth/verify-pin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": getApiKey(),
            },
            body: JSON.stringify({
                temp_token: _tempToken,
                pin: pinInput,
            }),
        });

        const data = await resp.json();

        if (!resp.ok || !data.success) {
            throw new Error(data.detail || "PIN salah");
        }

        // Simpan full token + user
        setAuth(data.token, data.user);
        localStorage.setItem("so_logged_in", "true");
        localStorage.removeItem(AUTH_KEYS.TEMP_TOKEN);
        localStorage.removeItem(AUTH_KEYS.USERNAME);

        pinInput = "";
        updatePinDisplay();

        resetIdleTimer();
        await loadDashboardWithLoading();

    } catch (err) {
        console.error("[VerifyPIN] Error:", err);
        const pinError = document.getElementById("pinError");
        if (pinError) pinError.textContent = `❌ ${err.message}`;
        pinInput = "";
        updatePinDisplay();
        if (navigator.vibrate) navigator.vibrate(200);
    }
}

// =========================================================
// LOGOUT
// =========================================================
function logout() {
    const modal = document.getElementById("exitModal");
    if (modal) modal.classList.add("active");
    exitModalShown = true;
}

function closeExitModal() {
    exitModalShown = false;
    const modal = document.getElementById("exitModal");
    if (modal) modal.classList.remove("active");
    pushBackGuard();
}

async function confirmLogout() {
    const modal = document.getElementById("exitModal");
    if (modal) modal.classList.remove("active");

    // Call backend logout (best-effort)
    try {
        const _token = getToken();
        if (_token) {
            await fetch(`${CONFIG.BACKEND_URL}/api/auth/logout`, {
                method: "POST",
                headers: {
                    "X-API-Key": getApiKey(),
                    "Authorization": `Bearer ${_token}`,
                },
            });
        }
    } catch (e) {
        console.warn("[Logout] Backend call failed:", e);
    }

    clearAuth();
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    exitModalShown = false;
    pinInput = "";
    updatePinDisplay();

    if (clockInterval) clearInterval(clockInterval);
    stopDashboardAutoRefresh();

    showToastMini("👋 Logout berhasil!", "success");
    setTimeout(() => {
        showLoginView(true);
        showScreen("loginScreen");
        pushBackGuard();
    }, 300);
}

// =========================================================
// DASHBOARD LOADING
// =========================================================
async function loadDashboardWithLoading() {
    const overlay = document.getElementById("dataLoadingOverlay");
    const statusEl = document.getElementById("dataLoadingStatus");

    if (!overlay) {
        showScreen("homeScreen");
        startLiveClock();
        loadMiniDashboard();
        startDashboardAutoRefresh();
        await hideSplashScreen();
        return;
    }

    hideSplashScreen();
    await new Promise(r => setTimeout(r, 400));
    overlay.classList.add("active");
    resetLoadingSteps();

    try {
        await updateLoadingStep("config", "running", "Mengecek konfigurasi...");
        await new Promise(r => setTimeout(r, 300));
        await updateLoadingStep("config", "success", "Konfigurasi OK");

        await updateLoadingStep("dashboard", "running", "Memuat dashboard...");
        await loadMiniDashboard();
        await updateLoadingStep("dashboard", "success", "Dashboard siap");

        await updateLoadingStep("shift", "running", "Memuat jadwal shift...");
        await new Promise(r => setTimeout(r, 400));
        await updateLoadingStep("shift", "success", "Jadwal shift siap");

        if (statusEl) statusEl.textContent = "Siap! 🚀";
        await new Promise(r => setTimeout(r, 500));

        overlay.classList.add("fade-out");
        await new Promise(r => setTimeout(r, 400));
        overlay.classList.remove("active", "fade-out");

        showScreen("homeScreen");
        startLiveClock();
        startDashboardAutoRefresh();
    } catch (e) {
        console.error("[Loading] Error:", e);
        if (statusEl) statusEl.textContent = "Ada error, tapi lanjut...";
        await new Promise(r => setTimeout(r, 1000));
        overlay.classList.remove("active");
        showScreen("homeScreen");
        startLiveClock();
        startDashboardAutoRefresh();
    }
}

function resetLoadingSteps() {
    document.querySelectorAll(".data-loading-step").forEach(step => {
        step.classList.remove("running", "success", "error");
        const icon = step.querySelector(".step-icon");
        if (icon) icon.textContent = "⏳";
    });
}

async function updateLoadingStep(stepId, status, msg) {
    const step = document.querySelector(`.data-loading-step[data-step="${stepId}"]`);
    if (!step) return;
    step.classList.remove("running", "success", "error");
    step.classList.add(status);
    const icon = step.querySelector(".step-icon");
    const text = step.querySelector(".step-text");
    if (status === "running") {
        if (icon) icon.textContent = "⏳";
        if (text && msg) text.textContent = msg;
    } else if (status === "success") {
        if (icon) icon.textContent = "✅";
        if (text && msg) text.textContent = msg;
    } else if (status === "error") {
        if (icon) icon.textContent = "❌";
        if (text && msg) text.textContent = msg;
    }
}

//=========================================================
// SCREEN NAVIGATION
// =========================================================
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(screenId);
    if (target) target.classList.add("active");

    const bottomNav = document.getElementById("bottomNav");
    if (bottomNav) {
        if (screenId === "loginScreen") {
            bottomNav.style.display = "none";
        } else {
            bottomNav.style.display = "flex";
            
            document.querySelectorAll(".nav-item").forEach(item => {
                item.classList.remove("active");
                item.style.color = "#a39e93"; // Warna abu-abu default
            });
            
            let activeId = "";
            if (screenId === "homeScreen") activeId = "navHome";
            else if (screenId === "chatScreen") activeId = "navChat";
            else if (screenId === "masterShiftScreen") activeId = "navShift";
            else if (screenId === "settingsScreen" || screenId === "userManagementScreen") activeId = "navSettings";

            if (activeId) {
                const el = document.getElementById(activeId);
                if (el) {
                    el.classList.add("active");
                    el.style.color = "#ff7b00"; // Warna api saat aktif
                }
            }
        }
    }
}

function goToHomeScreen() {
    closeSidebar();
    showScreen("homeScreen");
    startLiveClock();
    loadMiniDashboard();
    startDashboardAutoRefresh();
}

function goToChatScreen() {
    stopDashboardAutoRefresh();
    showScreen("chatScreen");
    if (!currentBot || !BOTS[currentBot]) currentBot = "yui";
    switchBot(currentBot);
}

function goToSettingsScreen() {
    closeSidebar();
    updateSettingsUserInfo();
    
    // Logic Avatar
    const _user = getUser();
    if (_user) {
        const inisial = (_user.nama_lengkap || _user.username || "?").substring(0, 2).toUpperCase();
        const elAvatar = document.getElementById("settingsAvatar");
        if (elAvatar) elAvatar.textContent = inisial;
    }

    // Tampilkan menu kelola user cuma buat admin
    const _menuAdmin = document.getElementById("menuKelolaUser");
    if (_menuAdmin) {
        _menuAdmin.style.display = (_user && _user.role === "admin") ? "flex" : "none";
    }

    showScreen("settingsScreen");
}
// --- PROFIL (Placeholder) ---
function goToProfileScreen() {
    showToastMini("Fitur Edit Profil segera hadir!", "success");
    // Nanti bisa diarahkan ke halaman profil baru
}

// --- MODAL TEMA ---
function openThemeModal() {
    // Placeholder sederhana pakai prompt dulu, atau bisa bikin modal custom
    const isDark = document.documentElement.getAttribute("data-theme") === "halloween-dark";
    const pesan = isDark ? "Mode sekarang: DARK. Ganti ke LIGHT?" : "Mode sekarang: LIGHT. Ganti ke DARK?";
    if (confirm(pesan)) {
        toggleTheme();
        showToastMini("✅ Tema berhasil diubah", "success");
    }
}

// --- MODAL SISTEM ---
function openSystemModal() {
    const aksi = prompt(
        "Menu Sistem:\n" +
        "1. Cek Update\n" +
        "2. Ganti API Key\n" +
        "3. Reset Semua Chat\n\n" +
        "Ketik angka (1/2/3):"
    );
    
    if (aksi === "1") checkForUpdate(true);
    else if (aksi === "2") changeApiKey();
    else if (aksi === "3") resetAllChat();
}

function goToStreamlitScreen() {
    closeSidebar();
    loadStreamlit();
    showScreen("streamlitScreen");
}

function goToMasterShiftScreen() {
    closeSidebar();
    stopDashboardAutoRefresh();
    showScreen("masterShiftScreen");
    loadPersonilList();
    loadMasterShift();
}

function goToRakListScreen() {
    closeSidebar();
    stopDashboardAutoRefresh();
    showScreen("rakListScreen");
    loadRakList();
}

function goToSpdListScreen() {
    closeSidebar();
    stopDashboardAutoRefresh();
    showScreen("spdListScreen");
    loadSpdList();
}

function goToTopMinusScreen() {
    closeSidebar();
    stopDashboardAutoRefresh();
    showScreen("topMinusScreen");
    loadTopMinus();
}

function goToStatusScreen() {
    closeSidebar();
    stopDashboardAutoRefresh();
    showScreen("statusScreen");
    loadStatusAnalysis();
}

// =========================================================
// JAM LIVE
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
    const clockTime = document.getElementById("clockTime");
    if (clockTime) clockTime.textContent = `${hh}:${mm}`;

    const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
    const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    const clockDate = document.getElementById("clockDate");
    if (clockDate) {
        clockDate.textContent = `${hari[now.getDay()]}, ${now.getDate()} ${bulan[now.getMonth()]} ${now.getFullYear()}`;
    }

    const hour = now.getHours();
    let greeting = "Selamat Malam";
    let emoji = "🌙";
    if (hour >= 5 && hour < 11) { greeting = "Selamat Pagi"; emoji = "🌅"; }
    else if (hour >= 11 && hour < 15) { greeting = "Selamat Siang"; emoji = "☀️"; }
    else if (hour >= 15 && hour < 18) { greeting = "Selamat Sore"; emoji = "🌆"; }

    const _user = getUser();
    const _name = _user ? (_user.nama_lengkap || _user.username || "Bos") : "Bos";
    const clockGreeting = document.getElementById("clockGreeting");
    if (clockGreeting) clockGreeting.textContent = `${greeting}, ${_name}! ${emoji}`;
}

function updateSettingsUserInfo() {
    const _user = getUser();
    const elUser = document.getElementById("settingsUsername");
    const elName = document.getElementById("settingsNamaLengkap");
    const elRole = document.getElementById("settingsRole");
    
    if (elUser) elUser.textContent = _user ? `@${_user.username}` : "-";
    if (elName) elName.textContent = _user ? (_user.nama_lengkap || "-") : "-";
    if (elRole) elRole.textContent = _user ? (_user.role || "-").toUpperCase() : "-";
} "-").toUpperCase() : "-";
}

// =========================================================
// AUTO TIME THEME
// =========================================================
function updateTimeTheme() {
    if (!autoThemeEnabled) return;
    const hour = new Date().getHours();
    let timeTheme = "malam";
    if (hour >= 5 && hour < 11) timeTheme = "pagi";
    else if (hour >= 11 && hour < 15) timeTheme = "siang";
    else if (hour >= 15 && hour < 18) timeTheme = "sore";
    document.documentElement.setAttribute("data-time-theme", timeTheme);
}

function toggleAutoTheme() {
    autoThemeEnabled = !autoThemeEnabled;
    localStorage.setItem("so_auto_theme", String(autoThemeEnabled));
    updateAutoThemeDisplay();
    if (autoThemeEnabled) {
        updateTimeTheme();
        showToastMini("Auto tema jam aktif ✅", "success");
    } else {
        showToastMini("Auto tema jam dimatikan", "error");
    }
}

function updateAutoThemeDisplay() {
    const el = document.getElementById("autoThemeValue");
    if (el) el.textContent = autoThemeEnabled ? "Aktif" : "Nonaktif";
}

// =========================================================
// MINI DASHBOARD
// =========================================================
async function loadMiniDashboard() {
    const statRak = document.getElementById("statRak");
    const statSpd = document.getElementById("statSpd");
    const statNominal = document.getElementById("statNominal");
    const statusBar = document.getElementById("statusBar");
    const statusIcon = document.getElementById("statusIcon");
    const statusValue = document.getElementById("statusValue");
    const statusPercent = document.getElementById("statusPercent");
    const progressFill = document.getElementById("progressFill");
    const progressLabel = document.getElementById("progressLabel");
    const runningTextContainer = document.getElementById("runningTextContainer");

    const _url = `${CONFIG.BACKEND_URL}/api/yui/rekap`;

    try {
        const resp = await apiFetch(_url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: "bulan_ini" }),
        });
        
        if (!resp.ok) {
            let _errText = "";
            try { _errText = await resp.text(); } catch (e) {}
            console.error("[Dashboard] HTTP Error:", resp.status, _errText.substring(0, 200));
            throw new Error(`HTTP ${resp.status}`);
        }
        
        const data = await resp.json();
        console.log("[Dashboard] Rekap response:", data);
        
        // Handle nested: data.data atau data
        const _d = (data && data.data) ? data.data : data;
        
        const totalRak = _d.total_rak || 0;
        const totalNominal = _d.total_nominal || 0;
        const salesPeriode = _d.sales_periode || 0;
        const totalRakMaster = 145;
        const persenSo = totalRakMaster > 0 ? (totalRak / totalRakMaster) * 100 : 0;

        let statusPersen = 0;
        if (salesPeriode > 0) {
            statusPersen = (Math.abs(totalNominal) / salesPeriode) * 100;
        }

        let statusKey = "aman";
        let statusEmoji = "✅";
        let statusText = "AMAN";
        let statusColor = "hijau";

        if (statusPersen > 0.15) {
            statusKey = "bahaya"; statusEmoji = "🚨"; statusText = "BAHAYA"; statusColor = "merah";
        } else if (statusPersen >= 0.13) {
            statusKey = "waspada"; statusEmoji = "⚠️"; statusText = "WASPADA"; statusColor = "kuning";
        }

        if (statRak) statRak.textContent = `${totalRak}/${totalRakMaster}`;
        if (statSpd) statSpd.textContent = formatRupiahRingkas(salesPeriode);
        if (statNominal) statNominal.textContent = formatRupiahRingkas(totalNominal);

        if (statusIcon) statusIcon.textContent = statusEmoji;
        if (statusValue) statusValue.textContent = `${statusText} (${statusColor})`;
        if (statusPercent) statusPercent.textContent = `${statusPersen.toFixed(2)}%`;

        if (statusBar) {
            statusBar.classList.remove("status-aman", "status-waspada", "status-bahaya");
            statusBar.classList.add(`status-${statusKey}`);
        }

        if (progressFill) progressFill.style.width = `${Math.min(persenSo, 100)}%`;
        if (progressLabel) {
            progressLabel.textContent = `Progress SO: ${persenSo.toFixed(1)}% dari target ${CONFIG.TARGET_SO_PERSEN}%`;
        }

        if (runningTextContainer) {
            const runningParts = [];
            runningParts.push(`📦 Total Rak: <b>${totalRak}/${totalRakMaster}</b>`);
            runningParts.push(`💰 SPD: <b>${formatRupiahRingkas(salesPeriode)}</b>`);
            runningParts.push(`📉 Nominal Adjust: <b>${formatRupiahRingkas(totalNominal)}</b>`);
            runningParts.push(`📊 Status: <b>${statusEmoji} ${statusText}</b> (${statusPersen.toFixed(2)}%)`);

            try {
                const shiftResp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/shift-hari-ini`, {
                    method: "GET",
                });
                if (shiftResp.ok) {
                    const shiftData = await shiftResp.json();
                    if (shiftData.success && shiftData.grouped) {
                        const shiftParts = [];
                        const grouped = shiftData.grouped;
                        if (grouped.P7 && grouped.P7.length) shiftParts.push(`🟢 Pagi: ${grouped.P7.join(", ")}`);
                        if (grouped.S15 && grouped.S15.length) shiftParts.push(`🟡 Siang: ${grouped.S15.join(", ")}`);
                        if (grouped.M22 && grouped.M22.length) shiftParts.push(`🔴 Malam: ${grouped.M22.join(", ")}`);
                        if (grouped.O && grouped.O.length) shiftParts.push(`⚪ Off: ${grouped.O.join(", ")}`);
                        if (grouped.CUTI && grouped.CUTI.length) shiftParts.push(`⚫ Cuti: ${grouped.CUTI.join(", ")}`);
                        if (shiftParts.length) runningParts.push(`🌸 Hana: ${shiftParts.join(" | ")}`);
                    }
                }
            } catch (e) {}

            const now = new Date();
            const hour = now.getHours();
            let greeting = "";
            if (hour < 11) greeting = "🌅 Selamat pagi, semangat SO hari ini!";
            else if (hour < 15) greeting = "☀️ Selamat siang, cek data SO!";
            else if (hour < 18) greeting = "🌆 Selamat sore, cek progress SO!";
            else greeting = "🌙 Selamat malam, jangan lupa SO besok!";
            runningParts.push(greeting);

            const fullText = runningParts.join("  •  ") + "  •  ";
            startRunningText(fullText);
        }

    } catch (err) {
        console.error("[Dashboard] Error:", err);
        if (statRak) statRak.textContent = "—";
        if (statSpd) statSpd.textContent = "—";
        if (statNominal) statNominal.textContent = "—";
        if (progressLabel) progressLabel.textContent = "Gagal load data";
        if (statusValue) statusValue.textContent = "Gagal load";
        if (statusPercent) statusPercent.textContent = "—%";
        if (runningTextContainer) {
            runningTextContainer.innerHTML = `<div class="running-inner" style="color: var(--danger); padding-left: 40px;">⚠️ Gagal: ${err.message}</div>`;
        }
    }
}

function startDashboardAutoRefresh() {
    stopDashboardAutoRefresh();
    dashboardRefreshInterval = setInterval(loadMiniDashboard, 5 * 60 * 1000);
}

function stopDashboardAutoRefresh() {
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
        dashboardRefreshInterval = null;
    }
}

// =========================================================
// HELPERS
// =========================================================
function formatRupiahRingkas(nominal) {
    const abs = Math.abs(nominal);
    let formatted = "";
    if (abs >= 1_000_000_000) formatted = (nominal / 1_000_000_000).toFixed(2) + "M";
    else if (abs >= 1_000_000) formatted = (nominal / 1_000_000).toFixed(1) + "jt";
    else if (abs >= 1_000) formatted = (nominal / 1_000).toFixed(0) + "rb";
    else formatted = nominal.toFixed(0);
    return formatted;
}

function formatRupiahFull(nominal) {
    if (nominal === 0) return "Rp 0";
    const isNegative = nominal < 0;
    const abs = Math.abs(nominal);
    const formatted = abs.toLocaleString("id-ID", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    });
    return `${isNegative ? "-" : ""}Rp ${formatted}`;
}

function startRunningText(text) {
    const container = document.getElementById("runningTextContainer");
    if (!container) return;
    container.innerHTML = `
        <div class="running-icon">📢</div>
        <div class="running-viewport">
            <div class="running-track">
                <span class="running-inner">${text}</span>
                <span class="running-inner">${text}</span>
            </div>
        </div>
    `;
}

function showToastMini(message, type = "success") {
    const oldToast = document.querySelector(".toast-mini");
    if (oldToast) oldToast.remove();

    const toast = document.createElement("div");
    toast.className = `toast-mini ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add("show"), 100);

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

function formatTime(timestamp) {
    if (!timestamp) return "";
    const d = new Date(timestamp);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
}

function getSessionDate() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}${m}${day}`;
}

function formatMessage(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");
    html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.25);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');
    html = html.replace(/^[\-\*]\s+(.+)$/gm, "• $1");
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, "$1. $2");
    return html;
}

function cleanHtmlEntities(str) {
    if (!str) return "";
    return str
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, "&")
        .replace(/&quot;/g, '"')
        .replace(/&nbsp;/g, " ")
        .replace(/&#x27;/g, "'")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">");
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function getWelcomeText(botId) {
    switch (botId) {
        case "yui":
            return "Aku bisa:\n• Rekap SO (harian/mingguan/bulanan)\n• Input SO via chat / upload Excel\n• Input SPD via chat\n• Top item minus/plus";
        case "hana":
            return "Aku bisa:\n• Cek jadwal shift\n• Update/hapus shift (ketik natural)\n• Saran pengganti\n• Cek konflik jadwal";
        case "rei":
            return "Aku bisa:\n• Analisis trend SO\n• LPJ & laporan\n• Prediksi SO\n• Insight & rekomendasi";
        case "kurumi":
            return "Aku bisa:\n• Rangkum laporan\n• Kirim report (text)\n• Chat general\n• Koordinasi antar bot";
        default:
            return "";
    }
}
// =========================================================
// THEME
// =========================================================
function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "halloween-dark" ? "halloween-light" : "halloween-dark";
    setTheme(next);
}

function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("so_theme", theme);

    const isDark = theme === "halloween-dark";
    ["themeIcon", "themeIcon2"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = isDark ? "🌙" : "☀️";
    });

    const sidebarIcon = document.getElementById("sidebarThemeIcon");
    if (sidebarIcon) sidebarIcon.textContent = isDark ? "🌙" : "☀️";

    document.querySelectorAll(".theme-option").forEach(opt => {
        opt.classList.toggle("active", opt.getAttribute("data-theme") === theme);
    });
}

// =========================================================
// SIDEBAR
// =========================================================
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const isOpen = sidebar.classList.contains("open");
    if (isOpen) closeSidebar();
    else {
        sidebar.classList.add("open");
        overlay.classList.add("active");
    }
}

function closeSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("active");
}

// =========================================================
// BOT SWITCHING
// =========================================================
function switchBot(botId) {
    if (!BOTS[botId]) return;
    currentBot = botId;

    const bot = BOTS[botId];
    const emojiEl = document.getElementById("chatBotEmoji");
    const nameEl = document.getElementById("chatBotName");
    if (emojiEl) emojiEl.textContent = bot.emoji;
    if (nameEl) nameEl.textContent = bot.name;

    document.querySelectorAll(".bot-item").forEach(item => {
        item.classList.toggle("active", item.getAttribute("data-bot") === botId);
    });

    renderChatHistory();
    closeSidebar();
}

// =========================================================
// CHAT HISTORIES
// =========================================================
function loadChatHistories() {
    try {
        const raw = localStorage.getItem("so_chat_histories");
        chatHistories = raw ? JSON.parse(raw) : {};
    } catch (e) {
        chatHistories = {};
    }
    Object.keys(BOTS).forEach(botId => {
        if (!chatHistories[botId]) chatHistories[botId] = [];
    });
}

function saveChatHistories() {
    try {
        localStorage.setItem("so_chat_histories", JSON.stringify(chatHistories));
    } catch (e) {
        console.error("Gagal save history:", e);
    }
}

function clearCurrentChat() {
    if (!confirm(`Hapus chat dengan ${BOTS[currentBot].name}?`)) return;
    chatHistories[currentBot] = [];
    saveChatHistories();
    renderChatHistory();
    closeSidebar();
}

function resetAllChat() {
    if (!confirm("Hapus SEMUA chat dengan 4 bot?")) return;
    Object.keys(BOTS).forEach(botId => {
        chatHistories[botId] = [];
    });
    saveChatHistories();
    showToastMini("✅ Semua chat dihapus", "success");
}

// =========================================================
// API KEY
// =========================================================
function updateApiKeyDisplay() {
    const el = document.getElementById("settingsApiKey");
    if (!el) return;
    const key = getApiKey();
    const masked = key.length > 14
        ? key.substring(0, 10) + "..." + key.substring(key.length - 6)
        : "***";
    el.textContent = masked;
}

function changeApiKey() {
    const current = getApiKey();
    const newKey = prompt("Masukkan API Key baru:", current);
    if (!newKey || newKey.trim() === "") return;
    localStorage.setItem("so_api_key", newKey.trim());
    updateApiKeyDisplay();
    showToastMini("✅ API Key diupdate", "success");
}

// =========================================================
// PIN MANAGEMENT
// =========================================================
async function changePin() {
    const oldPin = prompt("Masukkan PIN lama:");
    if (!oldPin) return;
    const newPin = prompt("Masukkan PIN baru (6 digit):");
    if (!newPin || newPin.length !== 6 || !/^\d+$/.test(newPin)) {
        showToastMini("❌ PIN harus 6 digit angka", "error");
        return;
    }
    const confirmPin = prompt("Konfirmasi PIN baru:");
    if (newPin !== confirmPin) {
        showToastMini("❌ PIN tidak sama", "error");
        return;
    }

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/change-pin`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_pin: oldPin, new_pin: newPin }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Gagal");
        showToastMini("✅ PIN berhasil diubah", "success");
    } catch (err) {
        showToastMini(`❌ ${err.message}`, "error");
    }
}

async function changePassword() {
    const oldPass = prompt("Masukkan password lama:");
    if (!oldPass) return;
    const newPass = prompt("Masukkan password baru (min 6 karakter):");
    if (!newPass || newPass.length < 6) {
        showToastMini("❌ Password minimal 6 karakter", "error");
        return;
    }
    const confirmPass = prompt("Konfirmasi password baru:");
    if (newPass !== confirmPass) {
        showToastMini("❌ Password tidak sama", "error");
        return;
    }

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/change-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password: oldPass, new_password: newPass }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || "Gagal");
        showToastMini("✅ Password berhasil diubah", "success");
    } catch (err) {
        showToastMini(`❌ ${err.message}`, "error");
    }
}

// =========================================================
// STREAMLIT
// =========================================================
function loadStreamlit() {
    console.log("[Streamlit] Screen shown");
}

function openStreamlitInBrowser() {
    try {
        window.open(CONFIG.STREAMLIT_URL, "_blank");
    } catch (e) {
        window.location.href = CONFIG.STREAMLIT_URL;
    }
}

// =========================================================
// MASTER SHIFT
// =========================================================
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
    loadMasterShift();
}

function getShiftDateRange() {
    const today = new Date();
    let start = new Date();
    let end = new Date();

    if (shiftPeriod === "hari_ini") {
        start = today; end = today;
    } else if (shiftPeriod === "minggu") {
        const dayOfWeek = today.getDay();
        const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        start = new Date(today);
        start.setDate(today.getDate() + diff);
        end = new Date(start);
        end.setDate(start.getDate() + 6);
    } else if (shiftPeriod === "bulan") {
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    } else if (shiftPeriod === "custom") {
        const customStart = document.getElementById("customStart");
        const customEnd = document.getElementById("customEnd");
        if (customStart && customStart.value) start = new Date(customStart.value);
        if (customEnd && customEnd.value) end = new Date(customEnd.value);
    }

    // Paksa format ke YYYY-MM-DD pakai timezone lokal (biar gak meleset sehari)
    const startStr = start.getFullYear() + "-" + String(start.getMonth() + 1).padStart(2, '0') + "-" + String(start.getDate()).padStart(2, '0');
    const endStr = end.getFullYear() + "-" + String(end.getMonth() + 1).padStart(2, '0') + "-" + String(end.getDate()).padStart(2, '0');
    
    return { start, end, startStr, endStr };
}

function formatTanggalLong(dateStr) {
    const d = new Date(dateStr);
    const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
    const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    return `${d.getDate()} ${bulan[d.getMonth()]} ${d.getFullYear()} — ${hari[d.getDay()]}`;
}

function formatTanggalShort(dateStr) {
    const d = new Date(dateStr);
    const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    return `${d.getDate()} ${bulan[d.getMonth()]}`;
}

async function loadPersonilList() {
    const filterSelect = document.getElementById("personilFilter");
    const personilList = document.getElementById("personilList");

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil`, { method: "GET" });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        personilData = data.data || [];

        if (filterSelect) {
            const currentValue = filterSelect.value;
            filterSelect.innerHTML = '<option value="">👥 Semua Personil</option>';
            personilData.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.nama;
                opt.textContent = `👤 ${p.nama}`;
                filterSelect.appendChild(opt);
            });
            filterSelect.value = currentValue;
        }

        renderPersonilList();

    } catch (err) {
        console.error("[Personil] Error:", err);
        if (personilList) {
            personilList.innerHTML = `
                <div class="loading-state">
                    <p style="color: var(--danger);">⚠️ Gagal load personil: ${err.message}</p>
                </div>
            `;
        }
    }
}

function renderPersonilList() {
    const container = document.getElementById("personilList");
    if (!container) return;

    if (!personilData || personilData.length === 0) {
        container.innerHTML = `<div class="loading-state"><p>Belum ada personil</p></div>`;
        return;
    }

    const html = personilData.map(p => {
        const isActive = p.aktif !== false;
        return `
            <div class="personil-item ${isActive ? '' : 'inactive'}" data-nama="${p.nama}">
                <span class="personil-item-emoji">👤</span>
                <span class="personil-item-name">${p.nama}</span>
                <span class="personil-item-status ${isActive ? 'personil-status-active' : 'personil-status-inactive'}">
                    ${isActive ? 'Aktif' : 'Off'}
                </span>
                <div class="personil-item-actions">
                    ${isActive ? `
                        <button class="personil-item-btn delete" onclick="deletePersonilConfirm('${p.nama}')" title="Hapus">
                            🗑️
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join("");

    container.innerHTML = html;
}

async function loadMasterShift() {
    const container = document.getElementById("shiftList");
    const summary = document.getElementById("shiftSummary");
    if (!container) return;

    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Memuat jadwal shift...</p></div>`;

    try {
        const range = getShiftDateRange();
        // Langsung pakai string yang udah diformat
        const startStr = range.startStr;
        const endStr = range.endStr;

        const filterSelect = document.getElementById("personilFilter");
        const namaFilter = filterSelect ? filterSelect.value : "";

        const body = { tgl_start: startStr, tgl_end: endStr };
        if (namaFilter) body.nama_filter = namaFilter;

        // Debugging: liat apa yang dikirim
        console.log("[MasterShift] Request Body:", body);

        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/master-shift`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        
        // Debugging: liat apa yang diterima
        console.log("[MasterShift] Response Data:", data);

        if (!data.success) throw new Error(data.error || "Gagal load data");

        // PENTING: Ambil data dari field 'data', bukan 'list_shift'
        masterShiftData = data.data || data.list_shift || [];
        
        renderShiftList();
        renderShiftSummary(data);

    } catch (err) {
        console.error("[MasterShift] Error:", err);
        container.innerHTML = `<div class="shift-summary-empty"><span class="empty-icon">⚠️</span><p>Gagal load data: ${err.message}</p></div>`;
        if (summary) summary.innerHTML = "";
    }
}

function renderShiftList() {
    const container = document.getElementById("shiftList");
    if (!container) return;

    if (!masterShiftData || masterShiftData.length === 0) {
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">🌸</span>
                <p>Belum ada data shift di periode ini</p>
            </div>
        `;
        return;
    }

    const grouped = {};
    masterShiftData.forEach(row => {
        const tgl = row.tanggal;
        if (!grouped[tgl]) grouped[tgl] = [];
        grouped[tgl].push(row);
    });

    const sortedDates = Object.keys(grouped).sort();

    const html = sortedDates.map(tgl => {
        const rows = grouped[tgl];
        const rowsHtml = rows.map(r => {
            const kode = r.kode_shift || "O";
            const badgeClass = getBadgeClass(kode);
            return `
                <div class="shift-row">
                    <span class="shift-emoji">${r.shift_emoji || "❓"}</span>
                    <span class="shift-name">${r.nama}</span>
                    <span class="shift-badge ${badgeClass}">${r.shift_nama || kode}</span>
                </div>
            `;
        }).join("");

        return `
            <div class="date-group">
                <div class="date-group-header">
                    <span class="date-group-date">📅 ${formatTanggalLong(tgl)}</span>
                    <span class="date-group-count">${rows.length} orang</span>
                </div>
                ${rowsHtml}
            </div>
        `;
    }).join("");

    container.innerHTML = html;
}

function getBadgeClass(kode) {
    switch (kode) {
        case "P7":   return "shift-badge-p7";
        case "S15":  return "shift-badge-s15";
        case "M22":  return "shift-badge-m22";
        case "O":    return "shift-badge-o";
        case "CUTI": return "shift-badge-cuti";
        default:     return "shift-badge-o";
    }
}

function renderShiftSummary(data) {
    const summary = document.getElementById("shiftSummary");
    if (!summary) return;

    const total = data.data ? data.data.length : 0;
    const periode = data.periode || "—";

    const stats = { P7: 0, S15: 0, M22: 0, O: 0, CUTI: 0 };
    if (data.data) {
        data.data.forEach(r => {
            const kode = r.kode_shift || "O";
            if (stats[kode] !== undefined) stats[kode]++;
        });
    }

    summary.innerHTML = `
        <div style="font-size: 12px; line-height: 1.8;">
            <div style="color: var(--text-muted); margin-bottom: 6px;">📊 <b>${total}</b> data shift — ${periode}</div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;">
                <span>🟢 Pagi: <b>${stats.P7}</b></span>
                <span>🟡 Siang: <b>${stats.S15}</b></span>
                <span>🔴 Malam: <b>${stats.M22}</b></span>
                <span>⚪ Off: <b>${stats.O}</b></span>
                <span>⚫ Cuti: <b>${stats.CUTI}</b></span>
            </div>
        </div>
    `;
}
// =========================================================
// MODAL PERSONIL
// =========================================================
function openPersonilModal() {
    const modal = document.getElementById("personilModal");
    if (!modal) return;
    modal.classList.add("active");
    loadPersonilList();
}

function closePersonilModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById("personilModal");
    if (modal) modal.classList.remove("active");
}

async function addNewPersonil() {
    const input = document.getElementById("newPersonilName");
    if (!input) return;
    const nama = input.value.trim().toUpperCase();
    if (!nama || nama.length < 2) {
        showToastMini("❌ Nama minimal 2 karakter", "error");
        return;
    }
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nama: nama }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || `HTTP ${resp.status}`);
        input.value = "";
        showToastMini(`✅ ${nama} ditambahkan`, "success");
        _personilCache = null;
        await loadPersonilList();
    } catch (err) {
        console.error("[AddPersonil] Error:", err);
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}

function deletePersonilConfirm(nama) {
    const html = `
        <div style="text-align: left;">
            <p style="font-size: 14px; margin-bottom: 12px;">
                Hapus personil <b style="color: var(--accent-orange);">${nama}</b>?
            </p>
            <label style="display: flex; align-items: center; gap: 8px; padding: 10px; background: var(--bg-tertiary); border-radius: 8px; cursor: pointer; margin-bottom: 12px;">
                <input type="checkbox" id="forceDeleteCheck" style="width: 18px; height: 18px; accent-color: var(--danger);">
                <span style="font-size: 12px;">⚠️ <b>Force delete</b> — hapus history juga</span>
            </label>
            <div style="display: flex; gap: 8px;">
                <button class="confirm-btn confirm-btn-cancel" onclick="closeDeleteModal()">❌ Batal</button>
                <button class="confirm-btn confirm-btn-save" style="background: linear-gradient(135deg, #ee5253, #c73133);" onclick="deletePersonilExecute('${nama}')">🗑️ Hapus</button>
            </div>
        </div>
    `;

    let confirmModal = document.getElementById("deleteConfirmModal");
    if (!confirmModal) {
        confirmModal = document.createElement("div");
        confirmModal.id = "deleteConfirmModal";
        confirmModal.className = "modal-overlay active";
        confirmModal.style.zIndex = "300";
        confirmModal.innerHTML = `
            <div class="modal-content" onclick="event.stopPropagation()" style="max-width: 400px;">
                <div class="modal-header">
                    <div class="modal-title">⚠️ Konfirmasi Hapus</div>
                    <button class="modal-close" onclick="closeDeleteModal()">✕</button>
                </div>
                <div class="modal-body" id="deleteConfirmBody"></div>
            </div>
        `;
        document.body.appendChild(confirmModal);
        confirmModal.onclick = (e) => { if (e.target === confirmModal) closeDeleteModal(); };
    }
    document.getElementById("deleteConfirmBody").innerHTML = html;
}

function closeDeleteModal() {
    const modal = document.getElementById("deleteConfirmModal");
    if (modal) modal.remove();
}

async function deletePersonilExecute(nama) {
    const checkbox = document.getElementById("forceDeleteCheck");
    const force = checkbox ? checkbox.checked : false;
    closeDeleteModal();
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil/delete`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nama: nama, force: force }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.detail || `HTTP ${resp.status}`);
        showToastMini(data.message || `✅ ${nama} dihapus`, "success");
        _personilCache = null;
        await loadPersonilList();
    } catch (err) {
        console.error("[DeletePersonil] Error:", err);
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}

// =========================================================
// RAK LIST
// =========================================================
async function loadRakList() {
    const container = document.getElementById("rakList");
    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Memuat data rak...</p>
        </div>
    `;

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/rak-status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: "bulan_ini" }),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load data rak");

        rakListData = data.list_rak || [];

        const elTotal = document.getElementById("rakSummaryTotal");
        const elSudah = document.getElementById("rakSummarySudah");
        const elBelum = document.getElementById("rakSummaryBelum");

        if (elTotal) elTotal.textContent = data.total_rak;
        if (elSudah) elSudah.textContent = data.sudah_so;
        if (elBelum) elBelum.textContent = data.belum_so;

        renderRakList();

    } catch (err) {
        console.error("[RakList] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load data: ${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

function setRakFilter(filter) {
    rakFilterCurrent = filter;
    document.querySelectorAll(".rak-filter-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-filter") === filter);
    });
    renderRakList();
}

function filterRakList() {
    const input = document.getElementById("rakSearchInput");
    const clearBtn = document.getElementById("rakSearchClear");
    if (!input) return;
    rakSearchQuery = input.value.trim().toLowerCase();
    if (clearBtn) {
        if (rakSearchQuery) clearBtn.classList.remove("hidden");
        else clearBtn.classList.add("hidden");
    }
    renderRakList();
}

function clearRakSearch() {
    const input = document.getElementById("rakSearchInput");
    if (input) input.value = "";
    rakSearchQuery = "";
    const clearBtn = document.getElementById("rakSearchClear");
    if (clearBtn) clearBtn.classList.add("hidden");
    renderRakList();
}

function renderRakList() {
    const container = document.getElementById("rakList");
    if (!container) return;

    let filtered = rakListData || [];

    if (rakFilterCurrent === "sudah") {
        filtered = filtered.filter(r => r.status === "SUDAH");
    } else if (rakFilterCurrent === "belum") {
        filtered = filtered.filter(r => r.status === "BELUM");
    }

    if (rakSearchQuery) {
        filtered = filtered.filter(r => {
            const _id = (r.rak_id || "").toLowerCase();
            const _pic = (r.pic || "").toLowerCase();
            return _id.includes(rakSearchQuery) || _pic.includes(rakSearchQuery);
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">🔍</span>
                <p>Tidak ada rak yang cocok</p>
            </div>
        `;
        return;
    }

    const html = filtered.map(rak => {
        const isSudah = rak.status === "SUDAH";
        if (isSudah) {
            const nominalText = formatRupiahFull(rak.nominal);
            const nominalClass = rak.nominal < 0 ? "rak-nominal-minus" : "rak-nominal-plus";
            const tglShort = rak.tgl_so ? formatTanggalShort(rak.tgl_so) : "-";

            return `
                <div class="rak-card rak-card-sudah">
                    <div class="rak-card-header">
                        <span class="rak-card-badge rak-badge-sudah">✅</span>
                        <span class="rak-card-id">${escapeHtml(rak.rak_id)}</span>
                        <span class="rak-card-status">Sudah SO</span>
                    </div>
                    <div class="rak-card-body">
                        <div class="rak-card-row">
                            <span class="rak-card-label">📅 Tanggal</span>
                            <span class="rak-card-value">${tglShort}</span>
                        </div>
                        <div class="rak-card-row">
                            <span class="rak-card-label">💰 Nominal</span>
                            <span class="rak-card-value ${nominalClass}">${nominalText}</span>
                        </div>
                        <div class="rak-card-row">
                            <span class="rak-card-label">👤 PIC</span>
                            <span class="rak-card-value">${escapeHtml(rak.pic || "-")}</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="rak-card rak-card-belum">
                    <div class="rak-card-header">
                        <span class="rak-card-badge rak-badge-belum">❌</span>
                        <span class="rak-card-id">${escapeHtml(rak.rak_id)}</span>
                        <span class="rak-card-status">Belum SO</span>
                    </div>
                </div>
            `;
        }
    }).join("");

    container.innerHTML = html;
}

// =========================================================
// SPD LIST
// =========================================================
function setSpdSort(sortValue) {
    spdSortValue = sortValue;
    document.querySelectorAll(".spd-sort-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue);
    });
    loadSpdList();
}

function setSpdPeriod(period) {
    spdPeriodCurrent = period;
    document.querySelectorAll(".spd-period-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-period") === period);
    });
    const customRow = document.getElementById("spdCustomDateRow");
    if (customRow) {
        if (period === "custom") {
            customRow.classList.remove("hidden");
            const s = document.getElementById("spdCustomStart");
            const e = document.getElementById("spdCustomEnd");
            const today = new Date();
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const todayStr = today.toISOString().slice(0, 10);
            const startStr = startOfMonth.toISOString().slice(0, 10);
            if (s && !s.value) s.value = startStr;
            if (e && !e.value) e.value = todayStr;
        } else {
            customRow.classList.add("hidden");
        }
    }
    loadSpdList();
}

function getSpdDateRange() {
    const today = new Date();
    let start = new Date();
    let end = new Date();
    if (spdPeriodCurrent === "bulan_ini") {
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    } else if (spdPeriodCurrent === "bulan_lalu") {
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        end = new Date(today.getFullYear(), today.getMonth(), 0);
    } else if (spdPeriodCurrent === "custom") {
        const s = document.getElementById("spdCustomStart");
        const e = document.getElementById("spdCustomEnd");
        if (s && s.value) start = new Date(s.value);
        if (e && e.value) end = new Date(e.value);
    }
    return { start, end };
}

async function loadSpdList() {
    const container = document.getElementById("spdList");
    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Memuat data SPD...</p>
        </div>
    `;

    try {
        const range = getSpdDateRange();
        const startStr = range.start.toISOString().slice(0, 10);
        const endStr = range.end.toISOString().slice(0, 10);

        const body = { mode: spdPeriodCurrent };
        if (spdPeriodCurrent === "custom") {
            body.tgl_start = startStr;
            body.tgl_end = endStr;
        }

        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/spd-list`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load SPD");

        spdListData = data.list_spd || [];
        spdListData = sortSpdData(spdListData, spdSortValue);

        renderSpdSummary(data);
        renderSpdList();

    } catch (err) {
        console.error("[SpdList] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load data: ${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

function sortSpdData(data, sortBy) {
    const arr = [...data];
    if (sortBy === "tanggal_asc") {
        arr.sort((a, b) => (b.tanggal || "").localeCompare(a.tanggal || ""));
    } else if (sortBy === "tanggal_desc") {
        arr.sort((a, b) => (a.tanggal || "").localeCompare(b.tanggal || ""));
    } else if (sortBy === "spd_desc") {
        arr.sort((a, b) => (b.spd || 0) - (a.spd || 0));
    } else if (sortBy === "spd_asc") {
        arr.sort((a, b) => (a.spd || 0) - (b.spd || 0));
    }
    return arr;
}

function renderSpdSummary(data) {
    const elTotal = document.getElementById("spdSummaryTotal");
    const elMeta = document.getElementById("spdSummaryMeta");
    const elHari = document.getElementById("spdSummaryHari");
    const elAvg = document.getElementById("spdSummaryAvg");

    const totalSpd = data.total_spd || 0;
    const totalHari = data.total_hari || 0;
    const avgSpd = data.avg_spd || 0;
    const periode = data.periode || "—";

    if (elTotal) elTotal.textContent = formatRupiahFull(totalSpd);
    if (elMeta) elMeta.textContent = `📅 ${periode}`;
    if (elHari) elHari.textContent = totalHari;
    if (elAvg) elAvg.textContent = formatRupiahFull(avgSpd);
}

function renderSpdList() {
    const container = document.getElementById("spdList");
    if (!container) return;

    if (!spdListData || spdListData.length === 0) {
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">💰</span>
                <p>Belum ada data SPD di periode ini</p>
            </div>
        `;
        return;
    }

    const html = spdListData.map(item => {
        const tgl = item.tanggal;
        const spdText = formatRupiahFull(item.spd);
        const deltaNominal = item.delta_nominal || 0;
        const deltaPersen = item.delta_persen || 0;
        const trend = item.trend || "flat";

        let deltaHtml = "";
        if (trend === "flat") {
            deltaHtml = `<span class="spd-delta spd-delta-flat">— Flat</span>`;
        } else {
            const arrow = trend === "up" ? "↑" : "↓";
            const sign = deltaNominal >= 0 ? "+" : "";
            const deltaNominalText = `${sign}${formatRupiahFull(deltaNominal)}`;
            const deltaPersenText = `${sign}${deltaPersen.toFixed(2)}%`;
            const deltaClass = trend === "up" ? "spd-delta-up" : "spd-delta-down";
            deltaHtml = `<span class="spd-delta ${deltaClass}">${arrow} ${deltaNominalText} (${deltaPersenText})</span>`;
        }

        const ket = item.keterangan || "";
        const ketHtml = ket
            ? `<div class="spd-item-ket">📝 ${escapeHtml(ket.substring(0, 80))}${ket.length > 80 ? "..." : ""}</div>`
            : "";

        const pic = item.pic || "-";
        const picHtml = pic && pic !== "-"
            ? `<div class="spd-item-pic">👤 ${escapeHtml(pic)}</div>`
            : "";

        return `
            <div class="spd-item">
                <div class="spd-item-header">
                    <div class="spd-item-tgl">📅 ${formatTanggalLong(tgl)}</div>
                    <div class="spd-item-spd">${spdText}</div>
                </div>
                <div class="spd-item-delta-row">${deltaHtml}</div>
                ${ketHtml}
                ${picHtml}
            </div>
        `;
    }).join("");

    container.innerHTML = html;
}
// =========================================================
// TOP MINUS
// =========================================================
function setTopPeriod(period) {
    topPeriodCurrent = period;
    document.querySelectorAll("#topMinusScreen .spd-period-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-period") === period);
    });
    const customRow = document.getElementById("topCustomDateRow");
    if (customRow) {
        if (period === "custom") {
            customRow.classList.remove("hidden");
            const s = document.getElementById("topCustomStart");
            const e = document.getElementById("topCustomEnd");
            const today = new Date();
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const todayStr = today.toISOString().slice(0, 10);
            const startStr = startOfMonth.toISOString().slice(0, 10);
            if (s && !s.value) s.value = startStr;
            if (e && !e.value) e.value = todayStr;
        } else {
            customRow.classList.add("hidden");
        }
    }
    loadTopMinus();
}

function setTopTab(tab) {
    topTabCurrent = tab;
    document.querySelectorAll(".top-subtab").forEach(t => {
        t.classList.toggle("active", t.getAttribute("data-tab") === tab);
    });
    const searchWrapper = document.getElementById("topSearchWrapper");
    if (searchWrapper) {
        if (tab === "item") searchWrapper.classList.remove("hidden");
        else searchWrapper.classList.add("hidden");
    }
    const filterSign = document.getElementById("topFilterSign");
    if (filterSign) {
        if (tab === "item") filterSign.classList.remove("hidden");
        else filterSign.classList.add("hidden");
    }
    topSearchQuery = "";
    const searchInput = document.getElementById("topSearchInput");
    if (searchInput) searchInput.value = "";
    const clearBtn = document.getElementById("topSearchClear");
    if (clearBtn) clearBtn.classList.add("hidden");
    loadTopMinus();
}

function setTopSign(sign) {
    topSignCurrent = sign;
    document.querySelectorAll(".top-filter-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-sign") === sign);
    });
    loadTopMinus();
}

function setTopSort(sortValue) {
    topSortValue = sortValue;
    document.querySelectorAll("#topMinusScreen .spd-sort-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-sort") === sortValue);
    });
    renderTopList();
}

function getTopDateRange() {
    const today = new Date();
    let start = new Date();
    let end = new Date();
    if (topPeriodCurrent === "bulan_ini") {
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    } else if (topPeriodCurrent === "bulan_lalu") {
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        end = new Date(today.getFullYear(), today.getMonth(), 0);
    } else if (topPeriodCurrent === "custom") {
        const s = document.getElementById("topCustomStart");
        const e = document.getElementById("topCustomEnd");
        if (s && s.value) start = new Date(s.value);
        if (e && e.value) end = new Date(e.value);
    }
    return { start, end };
}

async function loadTopMinus() {
    const container = document.getElementById("topList");
    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Memuat data...</p>
        </div>
    `;

    const summaryTitle = document.getElementById("topSummaryTitle");
    if (summaryTitle) {
        if (topTabCurrent === "rak") {
            summaryTitle.textContent = "💰 TOTAL MINUS RAK";
        } else {
            if (topSignCurrent === "minus") summaryTitle.textContent = "💰 TOTAL MINUS ITEM";
            else if (topSignCurrent === "plus") summaryTitle.textContent = "💰 TOTAL PLUS ITEM";
            else summaryTitle.textContent = "💰 TOTAL ADJUST ITEM";
        }
    }

    try {
        const range = getTopDateRange();
        const startStr = range.start.toISOString().slice(0, 10);
        const endStr = range.end.toISOString().slice(0, 10);

        const body = { mode: topPeriodCurrent };
        if (topPeriodCurrent === "custom") {
            body.tgl_start = startStr;
            body.tgl_end = endStr;
        }

        let url = "";
        if (topTabCurrent === "rak") {
            url = `${CONFIG.BACKEND_URL}/api/yui/top-rak`;
            body.limit = 500;
        } else {
            url = `${CONFIG.BACKEND_URL}/api/yui/top-items-extended`;
            body.limit = null;
            body.search = topSearchQuery || "";
            body.order_by = topSortValue;
            body.sign = topSignCurrent;
        }

        const resp = await apiFetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load data");

        if (topTabCurrent === "rak") {
            topData = data.list_rak || [];
        } else {
            topData = data.items || [];
        }

        renderTopSummary(data);
        renderTopList();

    } catch (err) {
        console.error("[Top] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load data: ${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

function renderTopSummary(data) {
    const elTotal = document.getElementById("topSummaryTotal");
    const elMeta = document.getElementById("topSummaryMeta");

    let totalNominal = 0;
    let totalCount = 0;
    let periode = data.periode || "—";

    if (topTabCurrent === "rak") {
        totalNominal = data.total_nominal || 0;
        totalCount = data.total_rak || 0;
    } else {
        totalNominal = data.total_nominal || 0;
        totalCount = data.total_items || 0;
    }

    if (elTotal) elTotal.textContent = formatRupiahFull(totalNominal);
    if (elMeta) elMeta.textContent = `${totalCount} ${topTabCurrent === "rak" ? "rak" : "item"} • ${periode}`;
}

function renderTopList() {
    const container = document.getElementById("topList");
    if (!container) return;

    if (!topData || topData.length === 0) {
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">💰</span>
                <p>Belum ada data di periode ini</p>
            </div>
        `;
        return;
    }

    const sorted = sortTopData([...topData], topSortValue);
    if (topTabCurrent === "rak") renderTopRakList(container, sorted);
    else renderTopItemList(container, sorted);
}

function renderTopRakList(container, data) {
    const html = data.map((rak, idx) => {
        const rank = idx + 1;
        const nominal = rak.nominal_adjust || 0;
        const nominalText = formatRupiahFull(nominal);
        const nominalClass = nominal < 0 ? "top-nominal-minus" : "top-nominal-plus";
        const tglShort = rak.tgl_so ? formatTanggalShort(rak.tgl_so) : "-";
        const pic = rak.pic || "-";
        const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;

        return `
            <div class="top-item-card" onclick="openRakDetail('${escapeHtml(rak.rak_id)}')">
                <div class="top-item-header">
                    <span class="top-item-rank">${medal}</span>
                    <span class="top-item-title">${escapeHtml(rak.rak_id)}</span>
                    <span class="top-item-nominal ${nominalClass}">${nominalText}</span>
                </div>
                <div class="top-item-meta">
                    <span>📅 ${tglShort}</span>
                    <span>👤 ${escapeHtml(pic)}</span>
                    <span>📦 ${rak.total_item || 0} item</span>
                </div>
                <div class="top-item-hint">Tap untuk detail item →</div>
            </div>
        `;
    }).join("");
    container.innerHTML = html;
}

function renderTopItemList(container, data) {
    if (data.length === 0) {
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">🔍</span>
                <p>Tidak ada item yang cocok</p>
            </div>
        `;
        return;
    }

    const html = data.map((item, idx) => {
        const rank = idx + 1;
        const nominal = item.nominal_adjust || 0;
        const nominalText = formatRupiahFull(nominal);
        const nominalClass = nominal < 0 ? "top-nominal-minus" : "top-nominal-plus";
        const tglShort = item.so_date ? formatTanggalShort(item.so_date) : "-";
        const pic = item.pic || "-";
        const plu = item.plu || "-";
        const nama = cleanHtmlEntities(item.nama_produk) || "(tanpa nama)";
        const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`;

        return `
            <div class="top-item-card top-item-card-item">
                <div class="top-item-header">
                    <span class="top-item-rank">${medal}</span>
                    <span class="top-item-title">${escapeHtml(plu)}</span>
                    <span class="top-item-nominal ${nominalClass}">${nominalText}</span>
                </div>
                <div class="top-item-name">${escapeHtml(nama)}</div>
                <div class="top-item-meta">
                    <span>📅 ${tglShort}</span>
                    <span>🏪 ${escapeHtml(item.rak_id || "-")}</span>
                    <span>👤 ${escapeHtml(pic)}</span>
                </div>
            </div>
        `;
    }).join("");
    container.innerHTML = html;
}

function sortTopData(data, sortBy) {
    if (sortBy === "nominal_desc") {
        data.sort((a, b) => (a.nominal_adjust || 0) - (b.nominal_adjust || 0));
    } else if (sortBy === "nominal_asc") {
        data.sort((a, b) => (b.nominal_adjust || 0) - (a.nominal_adjust || 0));
    } else if (sortBy === "tanggal_desc") {
        data.sort((a, b) => {
            const ta = a.tgl_so || a.so_date || "";
            const tb = b.tgl_so || b.so_date || "";
            return tb.localeCompare(ta);
        });
    } else if (sortBy === "tanggal_asc") {
        data.sort((a, b) => {
            const ta = a.tgl_so || a.so_date || "";
            const tb = b.tgl_so || b.so_date || "";
            return ta.localeCompare(tb);
        });
    }
    return data;
}

function searchTopItems() {
    const input = document.getElementById("topSearchInput");
    const clearBtn = document.getElementById("topSearchClear");
    if (!input) return;
    topSearchQuery = input.value.trim();
    if (clearBtn) {
        if (topSearchQuery) clearBtn.classList.remove("hidden");
        else clearBtn.classList.add("hidden");
    }
    clearTimeout(topSearchTimeout);
    topSearchTimeout = setTimeout(() => { loadTopMinus(); }, 500);
}

function clearTopSearch() {
    const input = document.getElementById("topSearchInput");
    if (input) input.value = "";
    topSearchQuery = "";
    const clearBtn = document.getElementById("topSearchClear");
    if (clearBtn) clearBtn.classList.add("hidden");
    loadTopMinus();
}
// =========================================================
// RAK DETAIL
// =========================================================
async function openRakDetail(rakId) {
    if (!rakId) return;
    rakDetailCurrentRak = rakId;
    rakDetailFilter = "semua";
    rakDetailSearchQuery = "";
    rakDetailData = [];

    const titleEl = document.getElementById("rakDetailTitle");
    if (titleEl) titleEl.textContent = `Detail ${rakId}`;

    document.querySelectorAll(".rak-detail-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-filter") === "semua");
    });

    const searchInput = document.getElementById("rakDetailSearchInput");
    if (searchInput) searchInput.value = "";
    const clearBtn = document.getElementById("rakDetailSearchClear");
    if (clearBtn) clearBtn.classList.add("hidden");

    showScreen("rakDetailScreen");
    await loadRakDetail(rakId);
}

async function loadRakDetail(rakId) {
    const container = document.getElementById("rakDetailList");
    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Memuat item...</p>
        </div>
    `;

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/items-by-rak/${encodeURIComponent(rakId)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: "bulan_ini" }),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load data");

        rakDetailData = data.items || [];
        renderRakDetailInfo(data);
        renderRakDetailList();

    } catch (err) {
        console.error("[RakDetail] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load item: ${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

function renderRakDetailInfo(data) {
    const elRak = document.getElementById("rakDetailInfoRak");
    const elTgl = document.getElementById("rakDetailInfoTgl");
    const elPic = document.getElementById("rakDetailInfoPic");
    const elMinus = document.getElementById("rakDetailStatMinus");
    const elPlus = document.getElementById("rakDetailStatPlus");
    const elNet = document.getElementById("rakDetailStatNet");

    if (elRak) elRak.textContent = data.rak_id || "-";
    if (elTgl) elTgl.textContent = data.tgl_so ? formatTanggalLong(data.tgl_so) : "-";
    if (elPic) elPic.textContent = data.pic || "-";

    if (elMinus) elMinus.textContent = formatRupiahFull(data.total_minus || 0);
    if (elPlus) elPlus.textContent = formatRupiahFull(data.total_plus || 0);
    if (elNet) elNet.textContent = formatRupiahFull(data.total_nominal || 0);
}

function setRakDetailFilter(filter) {
    rakDetailFilter = filter;
    document.querySelectorAll(".rak-detail-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-filter") === filter);
    });
    renderRakDetailList();
}

function filterRakDetail() {
    const input = document.getElementById("rakDetailSearchInput");
    const clearBtn = document.getElementById("rakDetailSearchClear");
    if (!input) return;
    rakDetailSearchQuery = input.value.trim().toLowerCase();
    if (clearBtn) {
        if (rakDetailSearchQuery) clearBtn.classList.remove("hidden");
        else clearBtn.classList.add("hidden");
    }
    renderRakDetailList();
}

function clearRakDetailSearch() {
    const input = document.getElementById("rakDetailSearchInput");
    if (input) input.value = "";
    rakDetailSearchQuery = "";
    const clearBtn = document.getElementById("rakDetailSearchClear");
    if (clearBtn) clearBtn.classList.add("hidden");
    renderRakDetailList();
}

function renderRakDetailList() {
    const container = document.getElementById("rakDetailList");
    if (!container) return;

    let filtered = [...(rakDetailData || [])];

    if (rakDetailFilter === "minus") {
        filtered = filtered.filter(it => (it.nominal_adjust || 0) < 0);
    } else if (rakDetailFilter === "plus") {
        filtered = filtered.filter(it => (it.nominal_adjust || 0) > 0);
    }

    if (rakDetailSearchQuery) {
        filtered = filtered.filter(it => {
            const _plu = (it.plu || "").toLowerCase();
            const _nama = (it.nama_produk || "").toLowerCase();
            return _plu.includes(rakDetailSearchQuery) || _nama.includes(rakDetailSearchQuery);
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">🔍</span>
                <p>Tidak ada item yang cocok</p>
            </div>
        `;
        return;
    }

    filtered.sort((a, b) => (a.nominal_adjust || 0) - (b.nominal_adjust || 0));

    const html = filtered.map((item, idx) => {
        const rank = idx + 1;
        const nominal = item.nominal_adjust || 0;
        const nominalText = formatRupiahFull(nominal);
        const nominalClass = nominal < 0 ? "top-nominal-minus" : "top-nominal-plus";
        const plu = item.plu || "-";
        const nama = cleanHtmlEntities(item.nama_produk) || "(tanpa nama)";
        const icon = nominal < 0 ? "📉" : nominal > 0 ? "📈" : "➖";

        return `
            <div class="rak-detail-item">
                <div class="rak-detail-item-header">
                    <span class="rak-detail-item-rank">${rank}</span>
                    <span class="rak-detail-item-plu">${escapeHtml(plu)}</span>
                    <span class="top-item-nominal ${nominalClass}">${nominalText}</span>
                </div>
                <div class="rak-detail-item-name">${escapeHtml(nama)}</div>
                <div class="rak-detail-item-footer">
                    <span>${icon} Selisih: ${item.qty_var || 0} pcs</span>
                </div>
            </div>
        `;
    }).join("");

    container.innerHTML = html;
}

// =========================================================
// STATUS ANALYSIS
// =========================================================
function setStatusPeriod(period) {
    statusPeriodCurrent = period;
    document.querySelectorAll("#statusScreen .spd-period-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-period") === period);
    });
    const customRow = document.getElementById("statusCustomDateRow");
    if (customRow) {
        if (period === "custom") {
            customRow.classList.remove("hidden");
            const s = document.getElementById("statusCustomStart");
            const e = document.getElementById("statusCustomEnd");
            const today = new Date();
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const todayStr = today.toISOString().slice(0, 10);
            const startStr = startOfMonth.toISOString().slice(0, 10);
            if (s && !s.value) s.value = startStr;
            if (e && !e.value) e.value = todayStr;
        } else {
            customRow.classList.add("hidden");
        }
    }
    loadStatusAnalysis();
}

function getStatusDateRange() {
    const today = new Date();
    let start = new Date();
    let end = new Date();
    if (statusPeriodCurrent === "bulan_ini") {
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    } else if (statusPeriodCurrent === "bulan_lalu") {
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        end = new Date(today.getFullYear(), today.getMonth(), 0);
    } else if (statusPeriodCurrent === "custom") {
        const s = document.getElementById("statusCustomStart");
        const e = document.getElementById("statusCustomEnd");
        if (s && s.value) start = new Date(s.value);
        if (e && e.value) end = new Date(e.value);
    }
    return { start, end };
}

async function loadStatusAnalysis() {
    try {
        const range = getStatusDateRange();
        const startStr = range.start.toISOString().slice(0, 10);
        const endStr = range.end.toISOString().slice(0, 10);

        const body = { mode: statusPeriodCurrent };
        if (statusPeriodCurrent === "custom") {
            body.tgl_start = startStr;
            body.tgl_end = endStr;
        }

        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/status-analysis`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal load status");

        renderStatusCard(data);
        renderStatusMetrics(data);
        renderStatusRekomendasi(data);

    } catch (err) {
        console.error("[Status] Error:", err);
        const elEmoji = document.getElementById("statusBigEmoji");
        const elLabel = document.getElementById("statusBigLabel");
        const elPersen = document.getElementById("statusBigPersen");
        const elMeta = document.getElementById("statusBigMeta");
        const elRekom = document.getElementById("statusRekomendasi");
        if (elEmoji) elEmoji.textContent = "⚠️";
        if (elLabel) elLabel.textContent = "Error";
        if (elPersen) elPersen.textContent = "—";
        if (elMeta) elMeta.textContent = err.message;
        if (elRekom) elRekom.textContent = "Gagal load data.";
    }
}

function renderStatusCard(data) {
    const elEmoji = document.getElementById("statusBigEmoji");
    const elLabel = document.getElementById("statusBigLabel");
    const elPersen = document.getElementById("statusBigPersen");
    const elMeta = document.getElementById("statusBigMeta");
    const elCard = document.getElementById("statusBigCard");

    const statusEmoji = data.status_emoji || "⏳";
    const statusLabel = data.status_label || "—";
    const statusColor = data.status_color || "hijau";
    const persen = data.persen || 0;
    const periode = data.periode || "—";

    if (elEmoji) elEmoji.textContent = statusEmoji;
    if (elLabel) elLabel.textContent = statusLabel;
    if (elPersen) elPersen.textContent = `${persen.toFixed(3)}%`;
    if (elMeta) elMeta.textContent = periode;

    if (elCard) {
        elCard.classList.remove("status-big-card-aman", "status-big-card-waspada", "status-big-card-bahaya");
        const _class = statusColor === "merah" ? "bahaya" : statusColor === "kuning" ? "waspada" : "aman";
        elCard.classList.add(`status-big-card-${_class}`);
    }
}

function renderStatusMetrics(data) {
    const elNSB = document.getElementById("metricNSB");
    const elAdjust = document.getElementById("metricAdjust");
    const elBTSB = document.getElementById("metricBTSB");
    const elNSBPersonil = document.getElementById("metricNSBPersonil");

    if (elNSB) elNSB.textContent = formatRupiahFull(data.net_sales || 0);
    if (elAdjust) elAdjust.textContent = formatRupiahFull(data.total_adjust || 0);
    if (elBTSB) elBTSB.textContent = formatRupiahFull(data.btsb_rupiah || 0);
    if (elNSBPersonil) {
        const nsbPersonil = data.nsb_personil || 0;
        elNSBPersonil.textContent = formatRupiahFull(nsbPersonil);
        elNSBPersonil.classList.remove("status-metric-value-minus", "status-metric-value-plus");
        if (nsbPersonil > 0) elNSBPersonil.classList.add("status-metric-value-minus");
        else elNSBPersonil.classList.add("status-metric-value-plus");
    }
}

function renderStatusRekomendasi(data) {
    const elRekom = document.getElementById("statusRekomendasi");
    const elCard = document.getElementById("statusRekomendasiCard");
    if (elRekom) elRekom.textContent = data.rekomendasi || "Tidak ada rekomendasi.";
    if (elCard) {
        elCard.classList.remove("status-rekomendasi-aman", "status-rekomendasi-waspada", "status-rekomendasi-bahaya");
        elCard.classList.add(`status-rekomendasi-${data.status || "aman"}`);
    }
}
// =========================================================
// CHAT RENDERING
// =========================================================
function renderChatHistory() {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const history = chatHistories[currentBot] || [];
    const bot = BOTS[currentBot];

    if (history.length === 0) {
        container.innerHTML = `
            <div class="chat-message-wrapper ai">
                <div class="chat-avatar">${bot.emoji}</div>
                <div class="bubble-content ai">
                    <div class="bubble bubble-ai bubble-welcome">
Halo Bos! 👋

Aku <b>${bot.emoji} ${bot.name}</b> — ${bot.role}.

${getWelcomeText(currentBot)}
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = "";
    let lastDate = "";

    history.forEach((msg, idx) => {
        const isUser = msg.role === "user";
        
        // --- LOGIC STICKY DATE ---
        const msgDate = new Date(msg.timestamp || Date.now()).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
        if (msgDate !== lastDate) {
            const dateDiv = document.createElement("div");
            dateDiv.className = "chat-date-divider";
            dateDiv.innerHTML = `<span>${msgDate}</span>`;
            container.appendChild(dateDiv);
            lastDate = msgDate;
        }

        const wrapper = document.createElement("div");
        wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;

        const avatar = document.createElement("div");
        if (isUser) {
            avatar.className = "chat-avatar avatar-user";
            avatar.textContent = "👤";
        } else {
            avatar.className = "chat-avatar";
            avatar.textContent = bot.emoji;
        }
        wrapper.appendChild(avatar);

        const bubbleContent = document.createElement("div");
        bubbleContent.className = `bubble-content ${isUser ? "user" : "ai"}`;

        if (msg.isConfirm && msg.confirmData) {
            const confirmBubble = renderConfirmBubble(msg, idx);
            bubbleContent.appendChild(confirmBubble);
        } else {
            const bubble = document.createElement("div");
            bubble.className = `bubble bubble-${isUser ? "user" : "ai"}`;

            if (msg.isSuccess) bubble.classList.add("bubble-success");
            else if (msg.isError) bubble.classList.add("bubble-error");
            else if (msg.isCancel) bubble.classList.add("bubble-error");

            if (msg.isSuccess && msg.content.includes("🌸")) {
                bubble.innerHTML = formatSuccessMessage(msg.content);
            } else {
                bubble.innerHTML = formatMessage(msg.content);
            }

            bubbleContent.appendChild(bubble);
        }

        const time = document.createElement("div");
        time.className = "bubble-time";
        time.textContent = formatTime(msg.timestamp);

        bubbleContent.appendChild(time);
        wrapper.appendChild(bubbleContent);
        container.appendChild(wrapper);
    });
    
    // Reset tombol scroll
    const btn = document.getElementById("scrollBottomBtn");
    if (btn) btn.classList.remove("show");
    
    // Auto scroll ke bawah pas buka chat
    scrollToBottom(true);
}

function formatSuccessMessage(text) {
    if (!text) return "";
    const lines = text.split("\n");
    let html = "";
    let inSummary = false;
    let summaryLines = [];

    lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith("✅")) {
            html += `<div class="success-header">${escapeHtml(trimmed)}</div>`;
        } else if (trimmed.startsWith("🌸")) {
            inSummary = true;
            summaryLines = [];
        } else if (inSummary && trimmed) {
            summaryLines.push(trimmed);
        } else if (trimmed) {
            html += `<div style="margin-top: 4px;">${escapeHtml(trimmed)}</div>`;
        }
    });

    if (summaryLines.length > 0) {
        html += `<div class="shift-summary-chat">`;
        summaryLines.forEach(line => {
            html += `<div class="shift-summary-chat-line">${escapeHtml(line)}</div>`;
        });
        html += `</div>`;
    }
    return html;
}

function renderConfirmBubble(msg, idx) {
    const bubble = document.createElement("div");
    bubble.className = "bubble bubble-ai bubble-confirm";
    if (msg.resolved) bubble.classList.add("resolved");

    const data = msg.confirmData;
    const items = data.items || [];
    const itemsCount = items.length;
    const showAll = itemsCount <= 4;
    const displayItems = showAll ? items : items.slice(0, 4);
    const remaining = itemsCount - 4;

    const itemsHtml = displayItems.map(it => 
        `<span class="confirm-chip">👤 ${it.nama} → ${it.shift_nama || it.kode_shift}</span>`
    ).join("");

    const moreHtml = !showAll 
        ? `<span class="confirm-chip confirm-chip-more">+${remaining}</span>` 
        : "";

    let actionsHtml = "";
    let statusHtml = "";

    if (!msg.resolved) {
        actionsHtml = `
            <div class="confirm-actions">
                <button class="confirm-btn confirm-btn-cancel" onclick="handleConfirmCancel(${idx})">❌ Batal</button>
                <button class="confirm-btn confirm-btn-save" onclick="handleConfirmSave(${idx})" id="confirmBtnSave_${idx}">✅ Simpan</button>
            </div>
        `;
    } else if (msg.resolvedStatus === "saved") {
        statusHtml = `<div class="confirm-status confirm-status-saved">✅ Tersimpan</div>`;
    } else if (msg.resolvedStatus === "cancelled") {
        statusHtml = `<div class="confirm-status confirm-status-cancelled">❌ Dibatalkan</div>`;
    } else if (msg.resolvedStatus === "error") {
        statusHtml = `<div class="confirm-status confirm-status-error">⚠️ Gagal</div>`;
    }

    bubble.innerHTML = `
        <div class="confirm-header">
            <span class="confirm-title-icon">🌸</span>
            <span class="confirm-title">KONFIRMASI UPDATE</span>
            <span class="confirm-date">📅 ${formatTanggalShort(data.tanggal)}</span>
        </div>
        <div class="confirm-chips">${itemsHtml}${moreHtml}</div>
        ${actionsHtml}
        ${statusHtml}
    `;
    return bubble;
}

async function handleConfirmSave(idx) {
    const history = chatHistories[currentBot] || [];
    const msg = history[idx];
    if (!msg || !msg.confirmData) return;

    const btnSave = document.getElementById(`confirmBtnSave_${idx}`);
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';
    }

    const data = msg.confirmData;

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/save-batch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tanggal: data.tanggal,
                items: data.items.map(it => ({
                    nama: it.nama,
                    kode_shift: it.kode_shift,
                })),
            }),
        });

        const result = await resp.json();
        if (!resp.ok || !result.success) throw new Error(result.detail || `HTTP ${resp.status}`);

        msg.resolved = true;
        msg.resolvedStatus = "saved";

        const savedCount = result.saved || data.items.length;
        const successMsg = {
            role: "assistant",
            content: `✅ ${savedCount} shift tersimpan!\n\n${getShiftSummaryText(data.items)}`,
            timestamp: Date.now(),
            isSuccess: true,
        };
        history.push(successMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();

        if (document.getElementById("masterShiftScreen")?.classList.contains("active")) {
            loadMasterShift();
        }

        showToastMini(`✅ ${savedCount} shift tersimpan`, "success");

    } catch (err) {
        console.error("[ConfirmSave] Error:", err);
        msg.resolved = true;
        msg.resolvedStatus = "error";
        const errMsg = {
            role: "assistant",
            content: `⚠️ Gagal simpan: ${err.message}`,
            timestamp: Date.now(),
            isError: true,
        };
        history.push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}

function handleConfirmCancel(idx) {
    const history = chatHistories[currentBot] || [];
    const msg = history[idx];
    if (!msg || !msg.confirmData) return;

    msg.resolved = true;
    msg.resolvedStatus = "cancelled";

    const cancelMsg = {
        role: "assistant",
        content: `❌ Dibatalkan. Gak ada perubahan yang disimpan.`,
        timestamp: Date.now(),
        isCancel: true,
    };
    history.push(cancelMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();
    showToastMini("❌ Dibatalkan", "error");
}

function getShiftSummaryText(items) {
    const grouped = { P7: [], S15: [], M22: [], O: [], CUTI: [] };
    items.forEach(it => {
        const kode = it.kode_shift;
        if (grouped[kode]) grouped[kode].push(it.nama);
    });
    const lines = ["🌸 Shift terbaru:"];
    if (grouped.P7.length) lines.push(`🟢 Pagi: ${grouped.P7.join(", ")}`);
    if (grouped.S15.length) lines.push(`🟡 Siang: ${grouped.S15.join(", ")}`);
    if (grouped.M22.length) lines.push(`🔴 Malam: ${grouped.M22.join(", ")}`);
    if (grouped.O.length) lines.push(`⚪ Off: ${grouped.O.join(", ")}`);
    if (grouped.CUTI.length) lines.push(`⚫ Cuti: ${grouped.CUTI.join(", ")}`);
    return lines.join("\n");
}

// =========================================================
// CHAT INPUT & SEND
// =========================================================
function bindChatInput() {
    const input = document.getElementById("chatInput");
    if (!input) return;

    input.addEventListener("input", () => {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 100) + "px";
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSend");

    if (!input || !sendBtn) return;

    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;

    const _msgLower = text.toLowerCase().trim();

    if (_msgLower === "konfirmasi baru" || _msgLower === "ya konfirmasi") {
        if (window._pendingUploadSo) {
            window._pendingUploadSo.force_new_pic = true;
            const userMsg = { role: "user", content: text, timestamp: Date.now() };
            chatHistories[currentBot].push(userMsg);
            const aiMsg = {
                role: "assistant",
                content: `✅ Oke, PIC baru dikonfirmasi. Ketik **"simpan so"**.`,
                timestamp: Date.now(),
            };
            chatHistories[currentBot].push(aiMsg);
            saveChatHistories();
            renderChatHistory();
            scrollToBottom();
            sendBtn.disabled = false;
            return;
        }
    }

    if (window._pendingUploadSo) {
        if (_msgLower.startsWith("tanggal") || _msgLower.startsWith("pic ") || _msgLower.includes(" pic ")) {
            const _handled = await handleTanggalPicInput(text);
            if (_handled) {
                sendBtn.disabled = false;
                return;
            }
        }
    }

    if (_msgLower === "simpan so" || _msgLower === "save so") {
        await confirmSaveSo();
        sendBtn.disabled = false;
        return;
    }

    if (_msgLower === "simpan spd" || _msgLower === "save spd") {
        await confirmSaveSpd();
        sendBtn.disabled = false;
        return;
    }

    if (_msgLower === "batal" || _msgLower === "cancel") {
        if (window._pendingUploadSo) {
            cancelUploadSo();
            sendBtn.disabled = false;
            return;
        }
        if (window._pendingSpd) {
            window._pendingSpd = null;
            const userMsg = { role: "user", content: text, timestamp: Date.now() };
            chatHistories[currentBot].push(userMsg);
            const aiMsg = {
                role: "assistant",
                content: `Oke, SPD dibatalkan.`,
                timestamp: Date.now(),
            };
            chatHistories[currentBot].push(aiMsg);
            saveChatHistories();
            renderChatHistory();
            scrollToBottom();
            sendBtn.disabled = false;
            return;
        }
    }

    const _isSpdInput = currentBot === "yui" && (
        (_msgLower.includes("spd") || _msgLower.includes("sales")) && (
            _msgLower.includes("input") ||
            _msgLower.includes("catat") ||
            _msgLower.includes("simpan") ||
            _msgLower.includes("tambah") ||
            /\d{3,}/.test(_msgLower.replace(/[.,]/g, ""))
        )
    );

    if (_isSpdInput) {
        const userMsg = { role: "user", content: text, timestamp: Date.now() };
        chatHistories[currentBot].push(userMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        await handleSpdChat(text);
        sendBtn.disabled = false;
        return;
    }

    const userMsg = { role: "user", content: text, timestamp: Date.now() };
    chatHistories[currentBot].push(userMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();

    showLoadingBubble();

    try {
        const bot = BOTS[currentBot];
        const history = chatHistories[currentBot]
            .slice(-7, -1)
            .filter(m => !m.isConfirm && !m.isSuccess && !m.isCancel && !m.isError)
            .map(m => ({ role: m.role, content: m.content }));

        const response = await apiFetch(`${CONFIG.BACKEND_URL}${bot.endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                session_id: `so_${currentBot}_${getSessionDate()}`,
                history: history,
            }),
        });

        hideLoadingBubble();

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Error ${response.status}`);
        }

        const data = await response.json();

        if (data.needs_confirm && data.parsed && data.parsed.items) {
            const shortMsg = {
                role: "assistant",
                content: data.text || `Oke, aku catat ${data.parsed.items.length} perubahan shift.`,
                timestamp: Date.now(),
            };
            chatHistories[currentBot].push(shortMsg);
            saveChatHistories();
            renderChatHistory();
            scrollToBottom();
        
            setTimeout(() => {
                openConfirmShiftModal({
                    tanggal: data.parsed.tanggal,
                    items: data.parsed.items,
                    raw: data.parsed.raw || text,
                });
            }, 400);
        
            sendBtn.disabled = false;
            input.focus();
            return;
        } else {
            const aiMsg = {
                role: "assistant",
                content: data.text || "(kosong)",
                timestamp: Date.now(),
                meta: { model: data.model || null, intent: data.intent || null },
            };
            chatHistories[currentBot].push(aiMsg);
        }

        saveChatHistories();
        renderChatHistory();
        scrollToBottom();

    } catch (err) {
        hideLoadingBubble();
        const errMsg = {
            role: "assistant",
            content: `⚠️ Error: ${err.message}`,
            timestamp: Date.now(),
            isError: true,
        };
        chatHistories[currentBot].push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
    }

    sendBtn.disabled = false;
    input.focus();
}
// =========================================================
// LOADING BUBBLE
// =========================================================
let loadingEl = null;

function showLoadingBubble() {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const old = document.getElementById("loadingBubble");
    if (old) old.remove();

    loadingEl = document.createElement("div");
    loadingEl.className = "bubble bubble-ai bubble-loading";
    loadingEl.id = "loadingBubble";
    loadingEl.innerHTML = "<span></span><span></span><span></span>";
    container.appendChild(loadingEl);
    scrollToBottom();
}

function hideLoadingBubble() {
    const el = document.getElementById("loadingBubble");
    if (el) el.remove();
    loadingEl = null;
}

function scrollToBottom(force = false) {
    const container = document.getElementById("chatMessages");
    if (!container) return;
    
    // Kalau force (habis kirim pesan), langsung ke bawah
    if (force) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
            const btn = document.getElementById("scrollBottomBtn");
            if (btn) btn.classList.remove("show");
        }, 50);
        return;
    }

    // Deteksi kalau user scroll ke atas
    setTimeout(() => {
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        const btn = document.getElementById("scrollBottomBtn");
        if (btn) {
            if (isNearBottom) btn.classList.remove("show");
            else btn.classList.add("show");
        }
    }, 50);
}

// =========================================================
// PERSONIL MASTER + AUTO CORRECT
// =========================================================
async function loadPersonilMaster() {
    const _now = Date.now();
    if (_personilCache && (_now - _personilCacheTime) < 5 * 60 * 1000) {
        return _personilCache;
    }
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/personil`, { method: "GET" });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const _list = (data.data || [])
            .filter(p => p.aktif !== false)
            .map(p => String(p.nama).trim().toUpperCase());
        _personilCache = _list;
        _personilCacheTime = _now;
        console.log("[Personil] Loaded:", _list.length);
        return _list;
    } catch (e) {
        console.error("[Personil] Gagal:", e);
        return _personilCache || [];
    }
}

async function autoCorrectPic(userInput) {
    const _input = String(userInput).trim().toUpperCase();
    if (!_input) return { status: "empty", pic: null, suggestions: [], original: _input };

    const _list = await loadPersonilMaster();
    if (_list.length === 0) return { status: "exact", pic: _input, suggestions: [], original: _input };

    const _exact = _list.find(p => p === _input);
    if (_exact) return { status: "exact", pic: _exact, suggestions: [], original: _input };

    const _matches = _list.filter(p => 
        p.startsWith(_input) || p.includes(_input) || _input.includes(p)
    );

    if (_matches.length === 1) {
        return { status: "corrected", pic: _matches[0], original: _input, suggestions: _matches };
    }
    if (_matches.length > 1) {
        return { status: "multiple", pic: null, original: _input, suggestions: _matches.slice(0, 5) };
    }
    return { status: "not_found", pic: null, original: _input, suggestions: [] };
}

function groupItemsByRak(items) {
    const grouped = {};
    (items || []).forEach(it => {
        const rak = (it.rak_id || "UNKNOWN").toUpperCase();
        if (!grouped[rak]) grouped[rak] = [];
        grouped[rak].push(it);
    });
    return grouped;
}

// =========================================================
// PARSER TANGGAL + PIC
// =========================================================
async function parseTanggalPicInput(text) {
    const _lower = text.toLowerCase().trim();
    const _result = { tanggal: null, pic_per_rak: null, pic_issues: [], is_new_pic: false };
    
    let _match = _lower.match(/tanggal\s+(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (_match) {
        _result.tanggal = `${_match[1]}-${String(_match[2]).padStart(2,'0')}-${String(_match[3]).padStart(2,'0')}`;
    }
    if (!_result.tanggal) {
        _match = _lower.match(/tanggal\s+(\d{1,2})-(\d{1,2})-(\d{4})/);
        if (_match) {
            _result.tanggal = `${_match[3]}-${String(_match[2]).padStart(2,'0')}-${String(_match[1]).padStart(2,'0')}`;
        }
    }
    if (!_result.tanggal) {
        _match = _lower.match(/tanggal\s+(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        if (_match) {
            _result.tanggal = `${_match[3]}-${String(_match[2]).padStart(2,'0')}-${String(_match[1]).padStart(2,'0')}`;
        }
    }
    
    let _picRaw = {};
    const _picMatch = text.match(/pic\s+(.+?)(?:\s+tanggal|$)/i);
    
    if (_picMatch) {
        let _picStr = _picMatch[1].trim();
        const _picStrLower = _picStr.toLowerCase();
        
        if (_picStrLower.startsWith("semua ")) {
            _picRaw["_ALL"] = _picStr.substring(6).trim();
        }
        else if (_picStrLower.startsWith("baru ")) {
            _picRaw["_ALL"] = _picStr.substring(5).trim();
            _result.is_new_pic = true;
        }
        else if (_picStr.includes(",")) {
            const _parts = _picStr.split(",").map(p => p.trim());
            _parts.forEach(part => {
                const _rakMatch = part.match(/^([A-Za-z0-9]+)\s*[:]?\s+(.+)$/);
                if (_rakMatch) {
                    _picRaw[_rakMatch[1].toUpperCase()] = _rakMatch[2].trim();
                }
            });
        }
        else {
            const _rakMatch = _picStr.match(/^([A-Za-z0-9]+)\s+(.+)$/);
            if (_rakMatch && /^[A-Z]{1,3}\d{1,4}$/i.test(_rakMatch[1])) {
                _picRaw[_rakMatch[1].toUpperCase()] = _rakMatch[2].trim();
            } else {
                _picRaw["_ALL"] = _picStr;
            }
        }
    }
    
    if (Object.keys(_picRaw).length > 0) {
        _result.pic_per_rak = {};
        for (const [key, namaRaw] of Object.entries(_picRaw)) {
            const _corrected = await autoCorrectPic(namaRaw);
            if (_corrected.status === "exact") {
                _result.pic_per_rak[key] = _corrected.pic;
            } else if (_corrected.status === "corrected") {
                _result.pic_per_rak[key] = _corrected.pic;
                _result.pic_issues.push({ type: "corrected", key, original: namaRaw, corrected: _corrected.pic });
            } else if (_corrected.status === "multiple") {
                _result.pic_issues.push({ type: "multiple", key, original: namaRaw, suggestions: _corrected.suggestions });
            } else if (_corrected.status === "not_found") {
                _result.pic_issues.push({ type: "not_found", key, original: namaRaw, is_new: _result.is_new_pic });
            }
        }
    }
    return _result;
}

async function handleTanggalPicInput(text) {
    const _pending = window._pendingUploadSo;
    if (!_pending) return false;
    
    const _lower = text.toLowerCase().trim();
    if (!_lower.startsWith("tanggal") && !_lower.includes("pic ") && !_lower.startsWith("pic ")) {
        return false;
    }
    
    const _parsed = await parseTanggalPicInput(text);
    
    const userMsg = { role: "user", content: text, timestamp: Date.now() };
    chatHistories[currentBot].push(userMsg);
    
    if (_parsed.tanggal) _pending.tanggal = _parsed.tanggal;
    
    let _responseText = "";
    
    if (_parsed.pic_issues.some(i => i.type === "corrected")) {
        _responseText += `🔍 **Auto-correct PIC:**\n\n`;
        _parsed.pic_issues.filter(i => i.type === "corrected").forEach(i => {
            _responseText += `- "${i.original}" → **${i.corrected}** ✅\n`;
        });
        _responseText += `\n`;
    }
    
    if (_parsed.pic_issues.some(i => i.type === "multiple")) {
        _responseText += `⚠️ **Nama ambigu, pilih:**\n\n`;
        _parsed.pic_issues.filter(i => i.type === "multiple").forEach(i => {
            _responseText += `Ketik untuk **"${i.original}"**:\n`;
            i.suggestions.forEach(s => {
                _responseText += `   • \`pic ${i.key} ${s}\`\n`;
            });
            _responseText += `\n`;
        });
        const aiMsg = { role: "assistant", content: _responseText, timestamp: Date.now() };
        chatHistories[currentBot].push(aiMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        return true;
    }
    
    if (_parsed.pic_issues.some(i => i.type === "not_found")) {
        const _notFound = _parsed.pic_issues.filter(i => i.type === "not_found");
        _responseText += `⚠️ **Nama gak ada di database:**\n\n`;
        _notFound.forEach(i => {
            _responseText += `- "${i.original}" ❌\n`;
        });
        _responseText += `\n**Kalau typo**, ketik:\n`;
        _notFound.forEach(i => {
            _responseText += `   • \`pic ${i.key} NAMA_BENER\`\n`;
        });
        _responseText += `\n**Kalau personil BARU**, ketik:\n`;
        _responseText += `   • \`pic baru ${_notFound[0].original}\``;
        
        const aiMsg = { role: "assistant", content: _responseText, timestamp: Date.now() };
        chatHistories[currentBot].push(aiMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        return true;
    }
    
    if (_parsed.pic_per_rak && Object.keys(_parsed.pic_per_rak).length > 0) {
        if (_parsed.pic_per_rak["_ALL"]) {
            const _rakList = Object.keys(groupItemsByRak(_pending.items));
            _pending.pic_per_rak = {};
            _rakList.forEach(rak => { _pending.pic_per_rak[rak] = _parsed.pic_per_rak["_ALL"]; });
        } else {
            _pending.pic_per_rak = { ...(_pending.pic_per_rak || {}), ..._parsed.pic_per_rak };
        }
    }
    
    window._pendingUploadSo = _pending;
    
    const _rakList = Object.keys(groupItemsByRak(_pending.items));
    const _picPerRak = _pending.pic_per_rak || {};
    const _rakMissing = _rakList.filter(rak => !_picPerRak[rak]);
    
    _responseText += `📝 **Update konfirmasi:**\n\n`;
    if (_pending.tanggal) {
        _responseText += `📅 Tanggal: ✅ **${_pending.tanggal}**\n\n`;
    } else {
        _responseText += `📅 Tanggal: ❌ Belum\n`;
        _responseText += `   \`tanggal 2026-10-14\`\n\n`;
    }
    
    _responseText += `👤 **PIC per Rak:**\n`;
    _rakList.forEach(rak => {
        if (_picPerRak[rak]) _responseText += `   • ${rak} → **${_picPerRak[rak]}** ✅\n`;
        else _responseText += `   • ${rak} → ❌ belum\n`;
    });
    _responseText += `\n`;
    
    const _isComplete = _pending.tanggal && _rakMissing.length === 0;
    if (_isComplete) {
        const _totalNominal = _pending.items.reduce((sum, it) => sum + (it.nominal_adjust || 0), 0);
        _responseText += `🎉 **Lengkap!**\n\n`;
        _responseText += `📊 Final:\n`;
        _responseText += `- 📅 ${_pending.tanggal}\n`;
        _responseText += `- 🏪 ${_rakList.length} rak\n`;
        _responseText += `- 📦 ${_pending.items.length} item\n`;
        _responseText += `- 💰 ${formatRupiahFull(_totalNominal)}\n\n`;
        _responseText += `Ketik **"simpan so"** buat save! 🚀`;
    } else {
        _responseText += `⚠️ Masih ada yang kosong.\n`;
        if (!_pending.tanggal) _responseText += `\n- \`tanggal 2026-10-14\``;
        if (_rakMissing.length > 0) _responseText += `\n- \`pic ${_rakMissing[0]} NAMA_PIC\``;
    }
    
    const aiMsg = { role: "assistant", content: _responseText, timestamp: Date.now() };
    chatHistories[currentBot].push(aiMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();
    showToastMini("✅ Info diupdate", "success");
    return true;
}

// =========================================================
// CONFIRM SAVE SO
// =========================================================
async function confirmSaveSo() {
    const _pending = window._pendingUploadSo;
    if (!_pending || !_pending.items) {
        showToastMini("❌ Gak ada data", "error");
        return;
    }
    if (!_pending.tanggal) {
        showToastMini("❌ Tanggal belum! Ketik: tanggal 2026-10-14", "error");
        return;
    }
    
    const _rakList = Object.keys(groupItemsByRak(_pending.items));
    const _picPerRak = _pending.pic_per_rak || {};
    const _rakMissing = _rakList.filter(rak => !_picPerRak[rak]);
    
    if (_rakMissing.length > 0) {
        showToastMini(`❌ PIC belum: ${_rakMissing.join(", ")}`, "error");
        return;
    }
    
    const _listMaster = await loadPersonilMaster();
    const _picNotInMaster = [];
    for (const rak of _rakList) {
        const _pic = _picPerRak[rak];
        if (_pic && !_listMaster.includes(_pic) && !_picNotInMaster.includes(_pic)) {
            _picNotInMaster.push(_pic);
        }
    }
    
    if (_picNotInMaster.length > 0 && !_pending.force_new_pic) {
        let _warnText = `⚠️ **Konfirmasi PIC Baru:**\n\n`;
        _warnText += `Nama ini gak ada di master:\n`;
        _picNotInMaster.forEach(p => { _warnText += `   • **${p}**\n`; });
        _warnText += `\n**Kalau personil BARU:**\n`;
        _warnText += `Ketik: \`konfirmasi baru\`\n\n`;
        _warnText += `**Kalau typo**, ketik ulang:\n`;
        _warnText += `Ketik: \`pic ${_rakList[0]} NAMA_BENER\``;
        
        const aiMsg = { role: "assistant", content: _warnText, timestamp: Date.now() };
        chatHistories[currentBot].push(aiMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        return;
    }
    
    const userMsg = { role: "user", content: `💾 simpan so`, timestamp: Date.now() };
    chatHistories[currentBot].push(userMsg);
    
    const aiLoadingMsg = {
        role: "assistant",
        content: `⏳ Menyimpan ${_pending.items.length} item...`,
        timestamp: Date.now(),
        isTemp: true,
    };
    chatHistories[currentBot].push(aiLoadingMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();
    
    const _itemsWithPic = _pending.items.map(it => {
        const _rak = (it.rak_id || "").toUpperCase();
        return { ...it, pic: _picPerRak[_rak] || "" };
    });
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/save-so`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tanggal: _pending.tanggal,
                items: _itemsWithPic,
                keterangan: _pending.keterangan,
            }),
        });
        
        const data = await resp.json();
        chatHistories[currentBot] = chatHistories[currentBot].filter(m => !m.isTemp);
        
        if (!resp.ok || !data.success) throw new Error(data.detail || data.error || "Gagal simpan");
        
        const _saved = data.saved_count || 0;
        const _total = data.total_nominal || 0;
        
        let _picSummary = "";
        Object.entries(_picPerRak).forEach(([rak, pic]) => {
            _picSummary += `   • **${rak}** → ${pic}\n`;
        });
        
        const successMsg = {
            role: "assistant",
            content: 
                `🎉 **Beres Bos!**\n\n` +
                `- 📅 Tanggal: **${_pending.tanggal}**\n` +
                `- ✅ **${_saved} rak** tersimpan\n` +
                `- 💰 Total: **${formatRupiahFull(_total)}**\n\n` +
                `**PIC per rak:**\n${_picSummary}\n` +
                `Data SO udah masuk database! 🚀`,
            timestamp: Date.now(),
            isSuccess: true,
        };
        chatHistories[currentBot].push(successMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        
        window._pendingUploadSo = null;
        
        const homeScreen = document.getElementById("homeScreen");
        if (homeScreen && homeScreen.classList.contains("active")) {
            loadMiniDashboard();
        }
        
        showToastMini(`✅ ${_saved} rak tersimpan`, "success");
        
    } catch (err) {
        console.error("[Save SO] Error:", err);
        chatHistories[currentBot] = chatHistories[currentBot].filter(m => !m.isTemp);
        const errMsg = { role: "assistant", content: `⚠️ Gagal: ${err.message}`, timestamp: Date.now(), isError: true };
        chatHistories[currentBot].push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}

// =========================================================
// UPLOAD FILE VIA CHAT
// =========================================================
async function handleChatFileUpload(file) {
    if (!file) return;
    if (currentBot !== "yui") {
        showToastMini("❌ Upload cuma di chat Yui", "error");
        return;
    }
    
    const userMsg = {
        role: "user",
        content: `📎 **Upload file:** ${file.name}\n_(sedang diproses...)_`,
        timestamp: Date.now(),
        isFile: true,
    };
    chatHistories[currentBot].push(userMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();
    
    showLoadingBubble();
    
    try {
        const formData = new FormData();
        formData.append("file", file);
        
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/upload-so`, {
            method: "POST",
            body: formData,
        });
        
        hideLoadingBubble();
        
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Gagal parse file");
        
        window._pendingUploadSo = {
            tanggal: data.tanggal,
            items: data.items,
            keterangan: `Upload ${file.name}`,
            filename: file.name,
        };
        
        const _totalRak = data.total_rak || 0;
        const _totalItem = data.total_items || 0;
        const _totalNominal = data.total_nominal || 0;
        const _items = data.items || [];
        
        const _grouped = {};
        _items.forEach(it => {
            const rak = (it.rak_id || "UNKNOWN").toUpperCase();
            if (!_grouped[rak]) _grouped[rak] = [];
            _grouped[rak].push(it);
        });
        
        const _rakList = Object.keys(_grouped).sort();
        
        let _previewText = "";
        _rakList.forEach((rak, idx) => {
            const _rakItems = _grouped[rak];
            const _rakTotal = _rakItems.reduce((sum, it) => sum + (it.nominal_adjust || 0), 0);
            const _sign = _rakTotal >= 0 ? "+" : "";
            
            _previewText += `**${idx + 1}. 🏪 ${rak}** (${_rakItems.length} item) — ${_sign}${formatRupiahFull(_rakTotal)}\n`;
            
            _rakItems.slice(0, 3).forEach(it => {
                const _nom = it.nominal_adjust || 0;
                const _itemSign = _nom >= 0 ? "+" : "";
                const _namaShort = (it.nama_produk || "-").substring(0, 25);
                _previewText += `   • \`${it.plu || "-"}\` ${_namaShort} — ${_itemSign}${formatRupiahFull(_nom)}\n`;
            });
            
            if (_rakItems.length > 3) {
                _previewText += `   _... +${_rakItems.length - 3} item lainnya_\n`;
            }
        });
        
        let _aiContent =
            `✅ File **${file.name}** berhasil dibaca!\n\n` +
            `📊 **Ringkasan:**\n` +
            `- 📅 Tanggal: **${data.tanggal || "❌ belum ada"}**\n` +
            `- 🏪 Rak: **${_totalRak}**\n` +
            `- 📦 Item: **${_totalItem}**\n` +
            `- 💰 Total: **${formatRupiahFull(_totalNominal)}**\n\n` +
            `**Detail per Rak:**\n\n${_previewText}\n`;
        
        if (!data.tanggal) {
            _aiContent += `⚠️ **Langkah selanjutnya:**\n\n`;
            _aiContent += `**1. Isi tanggal:**\n`;
            _aiContent += `Ketik: \`tanggal 2026-10-14\`\n\n`;
            _aiContent += `**2. Isi PIC (pilih salah satu):**\n`;
            _aiContent += `**a) Semua rak PIC sama:**\n`;
            _aiContent += `Ketik: \`pic ZAKI\`\n\n`;
            _aiContent += `**b) Per rak beda PIC:**\n`;
            _aiContent += `Ketik: \`pic ${_rakList[0]} ZAKI, ${_rakList[1] || _rakList[0]} PANDU\`\n\n`;
            _aiContent += `**3. Gabung sekaligus (opsional):**\n`;
            _aiContent += `Ketik: \`tanggal 2026-10-14 pic ZAKI\``;
        } else {
            _aiContent += `⚠️ **Isi PIC:**\n\n`;
            _aiContent += `**a) Semua rak PIC sama:**\n`;
            _aiContent += `Ketik: \`pic ZAKI\`\n\n`;
            _aiContent += `**b) Per rak beda PIC:**\n`;
            _aiContent += `Ketik: \`pic ${_rakList[0]} ZAKI, ${_rakList[1] || _rakList[0]} PANDU\`\n\n`;
            _aiContent += `**Rak yang perlu diisi PIC:**\n`;
            _rakList.forEach((rak, i) => {
                _aiContent += `${i + 1}. \`${rak}\`\n`;
            });
        }
        
        const aiMsg = {
            role: "assistant",
            content: _aiContent,
            timestamp: Date.now(),
            isUploadPreview: true,
        };
        chatHistories[currentBot].push(aiMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        
        showToastMini(`✅ ${_totalItem} item siap`, "success");
        
    } catch (err) {
        hideLoadingBubble();
        console.error("[Upload] Error:", err);
        const errMsg = {
            role: "assistant",
            content: `⚠️ Gagal upload: ${err.message}`,
            timestamp: Date.now(),
            isError: true,
        };
        chatHistories[currentBot].push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}

function cancelUploadSo() {
    window._pendingUploadSo = null;
    const userMsg = { role: "user", content: `❌ batal`, timestamp: Date.now() };
    chatHistories[currentBot].push(userMsg);
    const aiMsg = { role: "assistant", content: `Oke, data dibuang. 👍`, timestamp: Date.now() };
    chatHistories[currentBot].push(aiMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();
    showToastMini("❌ Dibatalkan", "error");
}

// =========================================================
// HANDLE SPD VIA CHAT
// =========================================================
async function handleSpdChat(text) {
    showLoadingBubble();
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/parse-spd`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text }),
        });
        
        const parse = await resp.json();
        hideLoadingBubble();
        
        if (!parse.success || !parse.nominal) {
            const errMsg = {
                role: "assistant",
                content: `Hmm, gak nemu nominal SPD Bos.\n\nContoh:\n• \`input spd hari ini 12.750.800\`\n• \`spd 5jt\``,
                timestamp: Date.now(),
            };
            chatHistories[currentBot].push(errMsg);
            saveChatHistories();
            renderChatHistory();
            scrollToBottom();
            return;
        }
        
        const _tanggal = parse.tanggal;
        const _nominal = parse.nominal;
        const _budget = _nominal * 0.0015;
        
        window._pendingSpd = {
            tanggal: _tanggal,
            nominal: _nominal,
        };
        
        const confirmMsg = {
            role: "assistant",
            content: 
                `💰 **Konfirmasi Input SPD**\n\n` +
                `- 📅 Tanggal: **${_tanggal}**\n` +
                `- 💵 SPD: **${formatRupiahFull(_nominal)}**\n` +
                `- 🎯 Budget SO (0,15%): **${formatRupiahFull(_budget)}**\n\n` +
                `Ketik **"simpan spd"** buat simpan.`,
            timestamp: Date.now(),
            isSpdConfirm: true,
        };
        chatHistories[currentBot].push(confirmMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        
    } catch (err) {
        hideLoadingBubble();
        console.error("[SPD Chat] Error:", err);
        const errMsg = {
            role: "assistant",
            content: `⚠️ Error: ${err.message}`,
            timestamp: Date.now(),
            isError: true,
        };
        chatHistories[currentBot].push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
    }
}

async function confirmSaveSpd() {
    const _pending = window._pendingSpd;
    if (!_pending) {
        showToastMini("❌ Gak ada SPD pending", "error");
        return;
    }
    
    const userMsg = { role: "user", content: `💾 simpan spd`, timestamp: Date.now() };
    chatHistories[currentBot].push(userMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();
    
    showLoadingBubble();
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/yui/save-spd`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tanggal: _pending.tanggal,
                nominal: _pending.nominal,
                keterangan: "Input via APK chat",
            }),
        });
        
        const data = await resp.json();
        hideLoadingBubble();
        
        if (!resp.ok || !data.success) {
            throw new Error(data.detail || data.message || "Gagal simpan");
        }
        
        const successMsg = {
            role: "assistant",
            content: 
                `✅ **SPD tersimpan!**\n\n` +
                `- 📅 Tanggal: **${_pending.tanggal}**\n` +
                `- 💰 SPD: **${formatRupiahFull(_pending.nominal)}**\n` +
                `- 🎯 Budget SO: **${formatRupiahFull(data.budget_so)}**\n\n` +
                `Gas input SO-nya Bos 🚀`,
            timestamp: Date.now(),
            isSuccess: true,
        };
        chatHistories[currentBot].push(successMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        
        window._pendingSpd = null;
        showToastMini(`✅ SPD tersimpan`, "success");
        
    } catch (err) {
        hideLoadingBubble();
        console.error("[SPD Save] Error:", err);
        const errMsg = {
            role: "assistant",
            content: `⚠️ Gagal: ${err.message}`,
            timestamp: Date.now(),
            isError: true,
        };
        chatHistories[currentBot].push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}

// =========================================================
// MODAL KONFIRMASI UPDATE SHIFT
// =========================================================
function openConfirmShiftModal(data) {
    const modal = document.getElementById("confirmShiftModal");
    if (!modal) return;
    currentConfirmData = data;

    const tglEl = document.getElementById("confirmModalDate");
    if (tglEl) tglEl.textContent = formatTanggalLong(data.tanggal);

    const countEl = document.getElementById("confirmModalCount");
    if (countEl) countEl.textContent = `${data.items.length} orang`;

    renderConfirmModalItems(data.items);

    const saveBtn = document.getElementById("confirmModalSaveBtn");
    if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = "✅ Konfirmasi";
    }

    modal.classList.add("active");
}

function closeConfirmShiftModal() {
    const modal = document.getElementById("confirmShiftModal");
    if (modal) modal.classList.remove("active");
    currentConfirmData = null;
}

function renderConfirmModalItems(items) {
    const container = document.getElementById("confirmModalList");
    if (!container) return;
    const html = items.map(it => {
        const kode = it.kode_shift || "O";
        const shiftClass = getShiftModalClass(kode);
        return `
            <div class="confirm-modal-item ${shiftClass}">
                <span class="confirm-modal-item-icon">👤</span>
                <span class="confirm-modal-item-name">${it.nama}</span>
                <span class="confirm-modal-item-arrow">→</span>
                <span class="confirm-modal-item-shift">${it.shift_nama || kode}</span>
            </div>
        `;
    }).join("");
    container.innerHTML = html;
}

function getShiftModalClass(kode) {
    switch (kode) {
        case "P7":   return "shift-p7";
        case "S15":  return "shift-s15";
        case "M22":  return "shift-m22";
        case "O":    return "shift-o";
        case "CUTI": return "shift-cuti";
        default:     return "shift-o";
    }
}

async function executeConfirmShift() {
    if (!currentConfirmData) {
        showToastMini("❌ Tidak ada data", "error");
        return;
    }
    const saveBtn = document.getElementById("confirmModalSaveBtn");
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';
    }
    const data = currentConfirmData;

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/hana/save-batch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tanggal: data.tanggal,
                items: data.items.map(it => ({
                    nama: it.nama,
                    kode_shift: it.kode_shift,
                })),
            }),
        });
        const result = await resp.json();
        if (!resp.ok || !result.success) throw new Error(result.detail || `HTTP ${resp.status}`);

        const savedCount = result.saved || data.items.length;
        const modal = document.getElementById("confirmShiftModal");
        if (modal) modal.classList.remove("active");

        const successMsg = {
            role: "assistant",
            content: `✅ ${savedCount} shift tersimpan!\n\n${getShiftSummaryText(data.items)}`,
            timestamp: Date.now(),
            isSuccess: true,
        };
        chatHistories[currentBot].push(successMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();

        if (document.getElementById("masterShiftScreen")?.classList.contains("active")) {
            loadMasterShift();
        }

        showToastMini(`✅ ${savedCount} shift tersimpan`, "success");
        currentConfirmData = null;

    } catch (err) {
        console.error("[ConfirmShift] Error:", err);
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = "✅ Konfirmasi";
        }
        const errMsg = {
            role: "assistant",
            content: `⚠️ Gagal: ${err.message}`,
            timestamp: Date.now(),
            isError: true,
        };
        chatHistories[currentBot].push(errMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}
// =========================================================
// BACK BUTTON + LOGOUT MODAL
// =========================================================
window.addEventListener("popstate", function(event) {
    const activeScreen = document.querySelector(".screen.active");
    if (!activeScreen) return;
    const screenId = activeScreen.id;

    const sidebar = document.getElementById("sidebar");
    if (sidebar && sidebar.classList.contains("open")) {
        event.preventDefault();
        closeSidebar();
        pushBackGuard();
        return;
    }

    const modalOpen = document.querySelector(".modal-overlay.active:not(#exitModal)");
    if (modalOpen) {
        event.preventDefault();
        modalOpen.classList.remove("active");
        pushBackGuard();
        return;
    }

    if (exitModalShown) {
        event.preventDefault();
        confirmLogout();
        return;
    }

    if (screenId === "homeScreen" || screenId === "loginScreen") {
        event.preventDefault();
        showExitModal();
        pushBackGuard();
        return;
    }

    event.preventDefault();

    if (screenId === "rakDetailScreen") {
        goToTopMinusScreen();
        pushBackGuard();
        return;
    }

    goToHomeScreen();
    pushBackGuard();
});

function showExitModal() {
    exitModalShown = true;
    const modal = document.getElementById("exitModal");
    if (modal) modal.classList.add("active");
}

function pushBackGuard() {
    try {
        history.pushState({ guard: true, ts: Date.now() }, "", "");
    } catch (e) {}
}

setTimeout(pushBackGuard, 800);

// =========================================================
// IDLE TIMER
// =========================================================
function resetIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    if (!isLoggedIn()) return;
    const activeScreen = document.querySelector(".screen.active");
    if (activeScreen && activeScreen.id === "loginScreen") return;

    idleTimer = setTimeout(() => {
        console.log("[Idle] Auto logout");
        autoLogout();
    }, IDLE_TIMEOUT);
}

function autoLogout() {
    clearAuth();
    pinInput = "";
    updatePinDisplay();
    if (clockInterval) clearInterval(clockInterval);
    stopDashboardAutoRefresh();
    showToastMini("⏰ Idle 5 menit — auto logout", "error");
    setTimeout(() => {
        showLoginView(true);
        showScreen("loginScreen");
        pushBackGuard();
    }, 300);
}

["click", "touchstart", "keydown", "scroll"].forEach(evt => {
    document.addEventListener(evt, resetIdleTimer, { passive: true });
});

// =========================================================
// CHECK UPDATE
// =========================================================
async function checkForUpdate(manual = false) {
    if (manual) showToastMini("🔍 Cek update...", "success");
    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/config/`, { method: "GET" });
        if (!resp.ok) {
            if (manual) showToastMini("❌ Gagal cek update", "error");
            return;
        }
        const data = await resp.json();
        if (!data.app) {
            if (manual) showToastMini("❌ Response invalid", "error");
            return;
        }
        const latestVersion = data.app.latest_version;
        const currentVersion = CONFIG.APP_VERSION;
        const forceUpdate = data.app.force_update || false;

        const elCurrent = document.getElementById("settingsCurrentVersion");
        const elLatest = document.getElementById("settingsLatestVersion");
        if (elCurrent) elCurrent.textContent = currentVersion;
        if (elLatest) elLatest.textContent = latestVersion;

        if (isNewerVersion(latestVersion, currentVersion)) {
            updateInfo = data.app;
            showUpdateModal(data.app, forceUpdate);
        } else {
            if (manual) showToastMini("✅ App sudah versi terbaru!", "success");
        }
    } catch (e) {
        console.warn("[Update] Error:", e);
        if (manual) showToastMini("❌ Gagal cek update", "error");
    }
}

function isNewerVersion(latest, current) {
    const l = String(latest).split(".").map(Number);
    const c = String(current).split(".").map(Number);
    for (let i = 0; i < 3; i++) {
        if ((l[i] || 0) > (c[i] || 0)) return true;
        if ((l[i] || 0) < (c[i] || 0)) return false;
    }
    return false;
}

function showUpdateModal(appInfo, force) {
    const modal = document.getElementById("updateModal");
    if (!modal) return;
    const elVersion = document.getElementById("updateLatestVersion");
    const elChangelog = document.getElementById("updateChangelog");
    const elHint = document.getElementById("updateHint");
    const btnCancel = modal.querySelector(".update-btn-cancel");
    if (elVersion) elVersion.textContent = appInfo.latest_version;
    if (elChangelog) elChangelog.textContent = appInfo.changelog || "Ada update terbaru!";
    if (force) {
        if (btnCancel) { btnCancel.disabled = true; btnCancel.style.opacity = "0.4"; }
        if (elHint) elHint.innerHTML = "⚠️ <b>Update wajib</b> — versi kamu terlalu lama.";
    }
    modal.classList.add("active");
}

function closeUpdateModal() {
    const modal = document.getElementById("updateModal");
    if (modal) modal.classList.remove("active");
}

function openUpdateDownload() {
    if (!updateInfo || !updateInfo.download_url) {
        showToastMini("❌ URL download nggak ada", "error");
        return;
    }
    try {
        window.open(updateInfo.download_url, "_blank");
    } catch (e) {
        window.location.href = updateInfo.download_url;
    }
    showToastMini("⬇️ Download dimulai...", "success");
    setTimeout(() => closeUpdateModal(), 1000);
}

// =========================================================
// AUTO REFRESH MINI DASHBOARD
// =========================================================
setInterval(() => {
    const homeScreen = document.getElementById("homeScreen");
    if (homeScreen && homeScreen.classList.contains("active") && isLoggedIn()) {
        loadMiniDashboard();
    }
}, 5 * 60 * 1000);
// =========================================================
// USER MANAGEMENT (ADMIN)
// =========================================================
function goToUserManagementScreen() {
    // Cek role dulu
    const _user = getUser();
    if (!_user || _user.role !== "admin") {
        showToastMini("❌ Akses ditolak. Khusus Admin.", "error");
        return;
    }
    
    showScreen("userManagementScreen");
    loadUsers();
}

async function loadUsers() {
    const container = document.getElementById("userListContainer");
    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Memuat data user...</p>
        </div>
    `;

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users`, {
            method: "GET",
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        if (!data.success) throw new Error(data.detail || "Gagal load user");

        renderUserList(data.users);
    } catch (err) {
        console.error("[UserMgmt] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load data: ${err.message}</p>
            </div>
        `;
    }
}

function renderUserList(users) {
    const container = document.getElementById("userListContainer");
    if (!container) return;

    if (!users || users.length === 0) {
        container.innerHTML = `<p style="text-align:center; padding: 20px;">Belum ada user.</p>`;
        return;
    }

    const html = users.map(u => {
        const isMe = u.id === getUser().id;
        const statusClass = u.aktif ? "shift-badge-p7" : "shift-badge-m22";
        const statusText = u.aktif ? "Aktif" : "Nonaktif";
        
        return `
            <div class="rak-card" style="margin-bottom: 10px;">
                <div class="rak-card-header">
                    <span class="rak-card-id">${u.username}</span>
                    <span class="shift-badge ${statusClass}">${statusText}</span>
                </div>
                <div class="rak-card-body">
                    <div class="rak-card-row">
                        <span class="rak-card-label">Nama</span>
                        <span class="rak-card-value">${u.nama_lengkap}</span>
                    </div>
                    <div class="rak-card-row">
                        <span class="rak-card-label">Role</span>
                        <span class="rak-card-value" style="text-transform: uppercase;">${u.role}</span>
                    </div>
                    <div class="rak-card-row">
                        <span class="rak-card-label">Last Login</span>
                        <span class="rak-card-value">${u.last_login ? formatTanggalLong(u.last_login.split('T')[0]) : "-"}</span>
                    </div>
                    
                    ${!isMe ? `
                    <div style="display: flex; gap: 8px; margin-top: 12px;">
                        <button class="settings-btn" style="padding: 8px; font-size: 12px;" onclick="resetUserPin(${u.id}, '${u.username}')">🔑 Reset PIN</button>
                        <button class="settings-btn" style="padding: 8px; font-size: 12px;" onclick="resetUserPassword(${u.id}, '${u.username}')">🔒 Reset Pass</button>
                        <button class="settings-btn settings-btn-danger" style="padding: 8px; font-size: 12px;" onclick="forceLogoutUser(${u.id}, '${u.username}')">🚪 Force Out</button>
                    </div>
                    ` : `<p style="font-size: 12px; color: var(--accent-orange); margin-top: 12px; text-align: center;">(Ini akun Anda)</p>`}
                </div>
            </div>
        `;
    }).join("");

    container.innerHTML = html;
}

// Action Buttons
async function resetUserPin(userId, username) {
    const newPin = prompt(`Masukkan PIN baru untuk ${username} (6 digit):`);
    if (!newPin || newPin.length !== 6 || !/^\d+$/.test(newPin)) {
        showToastMini("❌ PIN harus 6 digit angka", "error");
        return;
    }

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users/${userId}/reset-pin`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_pin: newPin })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "Gagal");
        showToastMini(`✅ PIN ${username} direset`, "success");
    } catch (err) {
        showToastMini(`❌ ${err.message}`, "error");
    }
}

async function resetUserPassword(userId, username) {
    const newPass = prompt(`Masukkan Password baru untuk ${username} (min 6 char):`);
    if (!newPass || newPass.length < 6) {
        showToastMini("❌ Password minimal 6 karakter", "error");
        return;
    }

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users/${userId}/reset-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_password: newPass })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "Gagal");
        showToastMini(`✅ Password ${username} direset`, "success");
    } catch (err) {
        showToastMini(`❌ ${err.message}`, "error");
    }
}

async function forceLogoutUser(userId, username) {
    if (!confirm(`Tendang ${username} dari semua device?`)) return;
    
    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/users/${userId}/force-logout`, {
            method: "POST"
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "Gagal");
        showToastMini(`✅ ${username} ditendang`, "success");
    } catch (err) {
        showToastMini(`❌ ${err.message}`, "error");
    }
}
// =========================================================
// TAMBAH USER BARU (ADMIN)
// =========================================================
function openAddUserModal() {
    // Reset form
    document.getElementById("newUserUsername").value = "";
    document.getElementById("newUserNama").value = "";
    document.getElementById("newUserPassword").value = "";
    document.getElementById("newUserPin").value = "123456";
    document.getElementById("newUserRole").value = "operator";
    document.getElementById("addUserError").textContent = "";
    
    document.getElementById("addUserModal").classList.add("active");
}

function closeAddUserModal() {
    document.getElementById("addUserModal").classList.remove("active");
}

async function submitAddUser() {
    const btn = document.getElementById("btnSaveUser");
    const errEl = document.getElementById("addUserError");
    
    const username = document.getElementById("newUserUsername").value.trim().toUpperCase();
    const nama = document.getElementById("newUserNama").value.trim();
    const password = document.getElementById("newUserPassword").value;
    const pin = document.getElementById("newUserPin").value;
    const role = document.getElementById("newUserRole").value;

    if (!username || !nama || !password) {
        errEl.textContent = "❌ Semua field wajib diisi!";
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';
    errEl.textContent = "";

    try {
        const resp = await apiFetch(`${CONFIG.BACKEND_URL}/api/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: username,
                password: password,
                nama_lengkap: nama,
                role: role,
                pin: pin
            })
        });

        const data = await resp.json();
        
        if (!resp.ok || !data.success) {
            throw new Error(data.detail || data.error || "Gagal menambah user");
        }

        showToastMini(`✅ User ${username} berhasil dibuat`, "success");
        closeAddUserModal();
        loadUsers(); // Refresh list

    } catch (err) {
        console.error("[AddUser] Error:", err);
        errEl.textContent = `❌ ${err.message}`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '✅ Simpan';
    }
}

// =========================================================
// BOOT
// =========================================================
document.addEventListener("DOMContentLoaded", initApp);