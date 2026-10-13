/* =========================================================
   DASHBOARD SO C383 — APP LOGIC
   ========================================================= */

// =========================================================
// CONFIG
// =========================================================
const CONFIG = {
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev",
    STREAMLIT_URL: "https://dashboard-so.streamlit.app",
    API_KEY: "so_c383_GOfNKuPRfhhdXnGTYGBYnr5zV5kzFRkV",  // ⚠️ GANTI DENGAN KEY LO
    DEFAULT_PIN: "123456",
    APP_VERSION: "1.0.0",
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
let chatHistories = {};  // { yui: [...], hana: [...], ... }


// =========================================================
// INIT — saat app pertama dibuka
// =========================================================
function initApp() {
    // Cek apakah udah login
    const isLoggedIn = localStorage.getItem("so_logged_in") === "true";

    // Load histories
    loadChatHistories();

    // Load theme
    const savedTheme = localStorage.getItem("so_theme") || "halloween-dark";
    setTheme(savedTheme);

    // Update API key display
    updateApiKeyDisplay();

    // Update PIN hint
    const savedPin = localStorage.getItem("so_pin");
    if (savedPin) {
        document.querySelector(".pin-hint").textContent = "";
    }

    // Redirect ke home kalau udah login
    if (isLoggedIn) {
        showScreen("homeScreen");
    } else {
        showScreen("loginScreen");
    }

    // Bind event listeners
    bindPinKeypad();
    bindChatInput();
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
}

function goToChatScreen() {
    showScreen("chatScreen");
    renderChatHistory();
}

function goToSettingsScreen() {
    closeSidebar();
    updateApiKeyDisplay();
    showScreen("settingsScreen");
}

function goToStreamlitScreen() {
    closeSidebar();
    loadStreamlit();
    showScreen("streamlitScreen");
}


// =========================================================
// PIN — LOGIN
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
        if (idx < pinInput.length) {
            dot.classList.add("filled");
        } else {
            dot.classList.remove("filled");
        }
    });
}

function checkPinComplete() {
    const pinError = document.getElementById("pinError");
    pinError.textContent = "";

    if (pinInput.length === 6) {
        setTimeout(() => {
            const validPin = localStorage.getItem("so_pin") || CONFIG.DEFAULT_PIN;

            if (pinInput === validPin) {
                // PIN benar — login
                pinInput = "";
                updatePinDisplay();
                localStorage.setItem("so_logged_in", "true");
                showScreen("homeScreen");
            } else {
                // PIN salah
                pinError.textContent = "❌ PIN salah, coba lagi";
                pinInput = "";
                updatePinDisplay();
                // Vibrate kalau didukung
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

    // Update icon
    const icons = ["themeIcon", "themeIcon2"];
    const isDark = theme === "halloween-dark";
    icons.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = isDark ? "🌙" : "☀️";
    });

    const sidebarIcon = document.getElementById("sidebarThemeIcon");
    if (sidebarIcon) sidebarIcon.textContent = isDark ? "🌙" : "☀️";

    // Update theme options active state
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

    if (isOpen) {
        closeSidebar();
    } else {
        sidebar.classList.add("open");
        overlay.classList.add("active");
    }
}

function closeSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
}


// =========================================================
// BOT SWITCHING
// =========================================================
function switchBot(botId) {
    if (!BOTS[botId]) return;
    currentBot = botId;

    // Update header
    const bot = BOTS[botId];
    document.getElementById("chatBotEmoji").textContent = bot.emoji;
    document.getElementById("chatBotName").textContent = bot.name;

    // Update sidebar active
    document.querySelectorAll(".bot-item").forEach(item => {
        item.classList.toggle("active", item.getAttribute("data-bot") === botId);
    });

    // Render history
    renderChatHistory();

    // Close sidebar
    closeSidebar();
}


// =========================================================
// CHAT HISTORIES (localStorage)
// =========================================================
function loadChatHistories() {
    try {
        const raw = localStorage.getItem("so_chat_histories");
        chatHistories = raw ? JSON.parse(raw) : {};
    } catch (e) {
        chatHistories = {};
    }

    // Init kalau kosong
    Object.keys(BOTS).forEach(botId => {
        if (!chatHistories[botId]) chatHistories[botId] = [];
    });
}

function saveChatHistories() {
    try {
        localStorage.setItem("so_chat_histories", JSON.stringify(chatHistories));
    } catch (e) {
        console.error("Gagal save chat history:", e);
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
    const key = localStorage.getItem("so_api_key") || CONFIG.API_KEY;
    // Sensor key
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
    const loading = document.querySelector(".streamlit-loading");

    if (!iframe || iframe.src !== "about:blank") return;

    loading.classList.remove("hidden");
    iframe.src = CONFIG.STREAMLIT_URL;

    // Hide loading setelah 3 detik (asumsi streamlit loaded)
    setTimeout(() => {
        loading.classList.add("hidden");
    }, 3000);
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

    // Auto-resize textarea
    input.addEventListener("input", () => {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 100) + "px";
    });

    // Enter = kirim, Shift+Enter = newline
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

    // Clear input
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;

    // Add user message
    const userMsg = {
        role: "user",
        content: text,
        timestamp: Date.now(),
    };
    chatHistories[currentBot].push(userMsg);
    saveChatHistories();
    renderChatHistory();
    scrollToBottom();

    // Show loading
    showLoadingBubble();

    // Send to backend
    try {
        const bot = BOTS[currentBot];

        // Build history (max 6 messages terakhir)
        const history = chatHistories[currentBot]
            .slice(-7, -1)  // exclude yang barusan dikirim
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

        // Remove loading
        hideLoadingBubble();

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errMsg = errorData.detail || errorData.message || `Error ${response.status}`;
            throw new Error(errMsg);
        }

        const data = await response.json();
        const aiText = data.text || "(kosong)";

        // Add AI response
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
        // Welcome message
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

        // Render markdown-like: bold, code block
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

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.2);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');

    // Bullet points
    html = html.replace(/^[\-\*]\s+(.+)$/gm, "• $1");

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
// OVERRIDE goToChatScreen (biar render history)
// =========================================================
const _origGoToChatScreen = goToChatScreen;
goToChatScreen = function() {
    _origGoToChatScreen();
    // Set bot default kalau belum
    if (!currentBot || !BOTS[currentBot]) currentBot = "yui";
    switchBot(currentBot);
};


// =========================================================
// AUTO LOGOUT KALAU IDLE 30 MENIT (opsional)
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