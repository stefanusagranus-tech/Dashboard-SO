/* =========================================================
   DASHBOARD SO C383 — APP LOGIC v1.1
   Tambah: Jam Live, Auto Time Theme, Mini Dashboard, Running Text
   ========================================================= */

// =========================================================
// CONFIG
// =========================================================
const CONFIG = {
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev",
    STREAMLIT_URL: "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/",
    API_KEY: "so_c383_GOfNKuPRfhhdXnGTYGBYnr5zV5kzFRkV",  // ⚠️ GANTI KALAU KEY LO BEDA
    DEFAULT_PIN: "123456",
    APP_VERSION: "1.1.0",
    TARGET_SO_PERSEN: 70,  // Target SO 70%
};

const BOTS = {
    yui:    { emoji: "📦", name: "Yui",    role: "Data Entry",   endpoint: "/api/yui/chat" },
    hana:   { emoji: "🌸", name: "Hana",   role: "Master Shift", endpoint: "/api/hana/chat" },
    rei:    { emoji: "📊", name: "Rei",    role: "Analisis",     endpoint: "/api/rei/chat" },
    kurumi: { emoji: "🎀", name: "Kurumi", role: "Chief",        endpoint: "/api/kurumi/chat" },
};


// =========================================================
// STATE
// =========================================================
let pinInput = "";
let currentBot = "yui";
let chatHistories = {};
let clockInterval = null;
let dashboardRefreshInterval = null;
let autoThemeEnabled = true;


// =========================================================
// INIT
// =========================================================
function initApp() {
    const isLoggedIn = localStorage.getItem("so_logged_in") === "true";

    loadChatHistories();

    // Auto theme setting
    autoThemeEnabled = localStorage.getItem("so_auto_theme") !== "false";

    // Theme
    const savedTheme = localStorage.getItem("so_theme") || "halloween-dark";
    setTheme(savedTheme);

    // Time theme
    updateTimeTheme();

    // API Key display
    updateApiKeyDisplay();
    updateAutoThemeDisplay();

    // PIN hint
    const savedPin = localStorage.getItem("so_pin");
    if (savedPin) {
        const hint = document.querySelector(".pin-hint");
        if (hint) hint.textContent = "";
    }

    // Show screen
    if (isLoggedIn) {
        showScreen("homeScreen");
        startLiveClock();
        loadMiniDashboard();
        startDashboardAutoRefresh();
    } else {
        showScreen("loginScreen");
    }

    // Bind
    bindPinKeypad();
    bindChatInput();

    // Auto update time theme tiap 1 menit
    setInterval(updateTimeTheme, 60 * 1000);
}


// =========================================================
// SCREEN NAVIGATION
// =========================================================
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(screenId);
    if (target) target.classList.add("active");
}

function goToHomeScreen() {
    closeSidebar();
    showScreen("homeScreen");
    // Refresh dashboard + start clock
    startLiveClock();
    loadMiniDashboard();
    startDashboardAutoRefresh();
}

function goToChatScreen() {
    try {
        document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
        const chat = document.getElementById("chatScreen");
        if (!chat) {
            alert("ERROR: chatScreen element gak ada!");
            return;
        }
        chat.classList.add("active");
        
        // Set default bot
        if (!currentBot || !BOTS[currentBot]) currentBot = "yui";
        const bot = BOTS[currentBot];
        document.getElementById("chatBotEmoji").textContent = bot.emoji;
        document.getElementById("chatBotName").textContent = bot.name;
        
        renderChatHistory();
    } catch (err) {
        alert("ERROR: " + err.name + " — " + err.message);
        console.error(err);
    }
}

function goToSettingsScreen() {
    closeSidebar();
    updateApiKeyDisplay();
    updateAutoThemeDisplay();
    showScreen("settingsScreen");
}

function goToStreamlitScreen() {
    closeSidebar();
    loadStreamlit();
    showScreen("streamlitScreen");
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

    // Jam
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const clockTime = document.getElementById("clockTime");
    if (clockTime) clockTime.textContent = `${hh}:${mm}`;

    // Tanggal
    const hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
    const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    const clockDate = document.getElementById("clockDate");
    if (clockDate) {
        clockDate.textContent = `${hari[now.getDay()]}, ${now.getDate()} ${bulan[now.getMonth()]} ${now.getFullYear()}`;
    }

    // Greeting
    const hour = now.getHours();
    let greeting = "Selamat Malam";
    let emoji = "🌙";
    if (hour >= 5 && hour < 11) { greeting = "Selamat Pagi"; emoji = "🌅"; }
    else if (hour >= 11 && hour < 15) { greeting = "Selamat Siang"; emoji = "☀️"; }
    else if (hour >= 15 && hour < 18) { greeting = "Selamat Sore"; emoji = "🌆"; }
    else { greeting = "Selamat Malam"; emoji = "🌙"; }

    const clockGreeting = document.getElementById("clockGreeting");
    if (clockGreeting) clockGreeting.textContent = `${greeting}, Bos! ${emoji}`;
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
    else timeTheme = "malam";

    document.documentElement.setAttribute("data-time-theme", timeTheme);
    console.log(`[TimeTheme] ${timeTheme} (jam: ${hour})`);
}

function toggleAutoTheme() {
    autoThemeEnabled = !autoThemeEnabled;
    localStorage.setItem("so_auto_theme", String(autoThemeEnabled));
    updateAutoThemeDisplay();

    if (autoThemeEnabled) {
        updateTimeTheme();
        alert("✅ Auto tema jam aktif");
    } else {
        alert("❌ Auto tema jam dimatikan");
    }
}

function updateAutoThemeDisplay() {
    const el = document.getElementById("autoThemeValue");
    if (el) el.textContent = autoThemeEnabled ? "Aktif" : "Nonaktif";
}


// =========================================================
// MINI DASHBOARD — Fetch dari /api/yui/rekap
// =========================================================
async function loadMiniDashboard() {
    const statRak = document.getElementById("statRak");
    const statItem = document.getElementById("statItem");
    const statNominal = document.getElementById("statNominal");
    const progressFill = document.getElementById("progressFill");
    const progressLabel = document.getElementById("progressLabel");
    const runningText = document.getElementById("runningText");

    // 🔥 DEBUG — liat URL & key sebelum fetch
    const _url = `${CONFIG.BACKEND_URL}/api/yui/rekap`;
    const _key = getApiKey();

    alert(
        `DEBUG INFO:\n\n` +
        `URL: ${_url}\n\n` +
        `Key prefix: ${_key.substring(0, 15)}...\n` +
        `Key length: ${_key.length}\n` +
        `Backend: ${CONFIG.BACKEND_URL}`
    );

    try {
        const resp = await fetch(_url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify({ mode: "bulan_ini" }),
        });

        // 🔥 DEBUG — liat response status
        alert(
            `RESPONSE:\n\n` +
            `Status: ${resp.status}\n` +
            `Status text: ${resp.statusText}\n` +
            `Final URL: ${resp.url}`
        );

        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }

        const data = await resp.json();

        const totalRak = data.total_rak || 0;
        const totalItem = data.total_item || 0;
        const totalNominal = data.total_nominal || 0;

        const totalRakMaster = 145;
        const persen = totalRakMaster > 0 ? (totalRak / totalRakMaster) * 100 : 0;

        if (statRak) statRak.textContent = `${totalRak}/${totalRakMaster}`;
        if (statItem) statItem.textContent = totalItem;
        if (statNominal) {
            const abs = Math.abs(totalNominal);
            let formatted = "";
            if (abs >= 1_000_000) formatted = `${(totalNominal / 1_000_000).toFixed(1)}M`;
            else if (abs >= 1_000) formatted = `${(totalNominal / 1_000).toFixed(0)}K`;
            else formatted = totalNominal.toFixed(0);
            statNominal.textContent = `Rp ${formatted}`;
        }

        if (progressFill) progressFill.style.width = `${Math.min(persen, 100)}%`;
        if (progressLabel) {
            progressLabel.textContent = `${persen.toFixed(1)}% dari target ${CONFIG.TARGET_SO_PERSEN}%`;
        }

        if (runningText) {
            const runningParts = [];
            runningParts.push(`📦 Yui: ${totalRak} rak SO bulan ini`);
            runningParts.push(`💰 Total selisih: Rp ${totalNominal.toLocaleString("id-ID")}`);
            runningParts.push(`📊 Total item: ${totalItem}`);
            runningParts.push(`⚙️ Target SO: ${CONFIG.TARGET_SO_PERSEN}%`);

            const now = new Date();
            const hour = now.getHours();
            if (hour < 11) runningParts.push(`🌅 Selamat pagi, semangat SO hari ini!`);
            else if (hour < 15) runningParts.push(`☀️ Selamat siang, cek data SO!`);
            else if (hour < 18) runningParts.push(`🌆 Selamat sore, cek progress SO!`);
            else runningParts.push(`🌙 Selamat malam, jangan lupa SO besok!`);

            runningText.textContent = runningParts.join("  •  ");
        }

    } catch (err) {
        console.error("[Dashboard] Error:", err);

        // 🔥 DEBUG — error detail
        alert(`ERROR CATCH:\n\nName: ${err.name}\nMessage: ${err.message}`);

        if (statRak) statRak.textContent = "—";
        if (statItem) statItem.textContent = "—";
        if (statNominal) statNominal.textContent = "—";
        if (progressLabel) progressLabel.textContent = "Gagal load data";
        if (runningText) runningText.textContent = `⚠️ Gagal: ${err.name} — ${err.message}`;
    }
}

// =========================================================
// PIN LOGIN
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
        setTimeout(() => {
            const validPin = localStorage.getItem("so_pin") || CONFIG.DEFAULT_PIN;

            if (pinInput === validPin) {
                pinInput = "";
                updatePinDisplay();
                localStorage.setItem("so_logged_in", "true");
                showScreen("homeScreen");
                startLiveClock();
                loadMiniDashboard();
                startDashboardAutoRefresh();
            } else {
                if (pinError) pinError.textContent = "❌ PIN salah, coba lagi";
                pinInput = "";
                updatePinDisplay();
                if (navigator.vibrate) navigator.vibrate(200);
            }
        }, 200);
    }
}


// =========================================================
// LOGOUT
// =========================================================
function logout() {
    if (!confirm("Yakin mau logout?")) return;
    localStorage.removeItem("so_logged_in");
    pinInput = "";
    updatePinDisplay();
    closeSidebar();
    stopDashboardAutoRefresh();
    if (clockInterval) clearInterval(clockInterval);
    showScreen("loginScreen");
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
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("sidebarOverlay").classList.remove("active");
}


// =========================================================
// BOT SWITCHING
// =========================================================
function switchBot(botId) {
    if (!BOTS[botId]) return;
    currentBot = botId;

    const bot = BOTS[botId];
    document.getElementById("chatBotEmoji").textContent = bot.emoji;
    document.getElementById("chatBotName").textContent = bot.name;

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
    alert("✅ Semua chat dihapus");
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

function getApiKey() {
    return localStorage.getItem("so_api_key") || CONFIG.API_KEY;
}

function changeApiKey() {
    const current = getApiKey();
    const newKey = prompt("Masukkan API Key baru:", current);
    if (!newKey || newKey.trim() === "") return;
    localStorage.setItem("so_api_key", newKey.trim());
    updateApiKeyDisplay();
    alert("✅ API Key diupdate");
}


// =========================================================
// PIN MANAGEMENT
// =========================================================
function changePin() {
    const newPin = prompt("Masukkan PIN baru (6 digit):");
    if (!newPin || newPin.length !== 6 || !/^\d+$/.test(newPin)) {
        alert("❌ PIN harus 6 digit angka");
        return;
    }
    const confirmPin = prompt("Konfirmasi PIN baru:");
    if (newPin !== confirmPin) {
        alert("❌ PIN tidak sama");
        return;
    }
    localStorage.setItem("so_pin", newPin);
    alert("✅ PIN berhasil diubah");
}


// =========================================================
// STREAMLIT
// =========================================================
function loadStreamlit() {
    const iframe = document.getElementById("streamlitFrame");
    const loading = document.getElementById("streamlitLoading");
    if (!iframe) return;

    // Reset ke blank dulu
    iframe.src = "about:blank";
    if (loading) loading.classList.remove("hidden");

    setTimeout(() => {
        iframe.src = CONFIG.STREAMLIT_URL;

        // Hide loading setelah 4 detik
        setTimeout(() => {
            if (loading) loading.classList.add("hidden");
        }, 4000);
    }, 100);
}

function openStreamlitInBrowser() {
    window.open(CONFIG.STREAMLIT_URL, "_blank");
}


// =========================================================
// BOOT
// =========================================================
document.addEventListener("DOMContentLoaded", initApp);
/* =========================================================
   CHAT — MESSAGE HANDLING
   ========================================================= */

// =========================================================
// BIND INPUT
// =========================================================
function bindChatInput() {
    const input = document.getElementById("chatInput");
    if (!input) return;

    // Auto-resize
    input.addEventListener("input", () => {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 100) + "px";
    });

    // Enter = kirim
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}


// =========================================================
// SEND MESSAGE
// =========================================================
async function sendMessage() {
    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSend");

    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;

    // Push user message
    const userMsg = {
        role: "user",
        content: text,
        timestamp: Date.now(),
    };
    chatHistories[currentBot].push(userMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();

    // Loading
    showLoadingBubble();

    try {
        const bot = BOTS[currentBot];

        // History max 6 pesan terakhir (exclude yang barusan)
        const history = chatHistories[currentBot]
            .slice(-7, -1)
            .map(m => ({ role: m.role, content: m.content }));

        const response = await fetch(`${CONFIG.BACKEND_URL}${bot.endpoint}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": getApiKey(),
            },
            body: JSON.stringify({
                message: text,
                session_id: `so_${currentBot}_${getSessionDate()}`,
                history: history,
            }),
        });

        hideLoadingBubble();

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errMsg = errorData.detail || errorData.message || `Error ${response.status}`;
            throw new Error(errMsg);
        }

        const data = await response.json();
        const aiText = data.text || "(kosong)";

        const aiMsg = {
            role: "assistant",
            content: aiText,
            timestamp: Date.now(),
            meta: {
                model: data.model || null,
                intent: data.intent || null,
            },
        };
        chatHistories[currentBot].push(aiMsg);
        saveChatHistories();
        renderChatHistory();
        scrollToBottom();

    } catch (err) {
        hideLoadingBubble();

        const errMsg = {
            role: "assistant",
            content: `⚠️ Error: ${err.message}\n\nCek koneksi atau API key di Pengaturan.`,
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
// RENDER CHAT HISTORY
// =========================================================
function renderChatHistory() {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const history = chatHistories[currentBot] || [];

    if (history.length === 0) {
        const bot = BOTS[currentBot];
        container.innerHTML = `
            <div class="bubble bubble-ai">
Halo Bos! 👋

Aku <b>${bot.emoji} ${bot.name}</b> — ${bot.role}.

${getWelcomeText(currentBot)}
            </div>
        `;
        return;
    }

    container.innerHTML = "";

    history.forEach(msg => {
        const wrapper = document.createElement("div");
        wrapper.style.display = "flex";
        wrapper.style.flexDirection = "column";
        wrapper.style.gap = "4px";

        const bubble = document.createElement("div");
        bubble.className = `bubble bubble-${msg.role === "user" ? "user" : "ai"}`;

        if (msg.isError) {
            bubble.style.borderLeft = "3px solid var(--danger)";
        }

        bubble.innerHTML = formatMessage(msg.content);

        const time = document.createElement("div");
        time.className = `bubble-time ${msg.role === "assistant" ? "bubble-time-ai" : ""}`;
        time.textContent = formatTime(msg.timestamp);

        wrapper.appendChild(bubble);
        wrapper.appendChild(time);
        container.appendChild(wrapper);
    });
}


// =========================================================
// LOADING BUBBLE
// =========================================================
let loadingEl = null;

function showLoadingBubble() {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    // Hapus dulu kalau ada
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


// =========================================================
// SCROLL
// =========================================================
function scrollToBottom() {
    const container = document.getElementById("chatMessages");
    if (!container) return;
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 50);
}


// =========================================================
// HELPERS
// =========================================================
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

    // Bold **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");

    // Italic *text*
    html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.25);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');

    // Bullet points
    html = html.replace(/^[\-\*]\s+(.+)$/gm, "• $1");

    // Numbered list
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, "$1. $2");

    return html;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function getWelcomeText(botId) {
    switch (botId) {
        case "yui":
            return "Aku bisa:\n• Rekap SO (harian/mingguan/bulanan)\n• Input SO via chat\n• Top item minus/plus\n• List item per rak";
        case "hana":
            return "Aku bisa:\n• Cek jadwal shift\n• Update/hapus shift\n• Saran pengganti\n• Cek konflik jadwal";
        case "rei":
            return "Aku bisa:\n• Analisis trend SO\n• LPJ & laporan\n• Prediksi SO\n• Insight & rekomendasi";
        case "kurumi":
            return "Aku bisa:\n• Rangkum laporan\n• Kirim report (text)\n• Chat general\n• Koordinasi antar bot";
        default:
            return "";
    }
}


// =========================================================
// IDLE AUTO LOGOUT 30 MENIT
// =========================================================
let idleTimer;
function resetIdleTimer() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
        if (localStorage.getItem("so_logged_in") === "true") {
            console.log("[Auth] Idle 30 menit — auto logout");
            localStorage.removeItem("so_logged_in");
            location.reload();
        }
    }, 30 * 60 * 1000);
}

["click", "touchstart", "keydown"].forEach(evt => {
    document.addEventListener(evt, resetIdleTimer, { passive: true });
});
resetIdleTimer();


// =========================================================
// AUTO REFRESH MINI DASHBOARD — tiap 5 menit (kalau di home)
// =========================================================
setInterval(() => {
    const homeScreen = document.getElementById("homeScreen");
    if (homeScreen && homeScreen.classList.contains("active")) {
        console.log("[Dashboard] Auto refresh");
        loadMiniDashboard();
    }
}, 5 * 60 * 1000);


// =========================================================
// END OF APP v1.1
// =========================================================