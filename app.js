/* =========================================================
   DASHBOARD SO C383 — APP LOGIC v1.3
   Tambah: Master Shift Screen, Chat Konfirmasi, CRUD Personil
   ========================================================= */

// =========================================================
// CONFIG
// =========================================================
const CONFIG = {
    BACKEND_URL: "https://dashboard-so.fastapicloud.dev",
    STREAMLIT_URL: "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/",
    API_KEY: "so_c383_GOfNKuPRfhhdXnGTYGBYnr5zV5kzFRkV",
    DEFAULT_PIN: "123456",
    APP_VERSION: "1.3.0",
    TARGET_SO_PERSEN: 70,
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

// Master Shift state
let shiftPeriod = "hari_ini";
let shiftPersonilFilter = "";
let masterShiftData = [];
let personilData = [];

// Konfirmasi chat state
let pendingConfirmations = {};  // { msgId: { items, tanggal, resolved } }
// Modal konfirmasi state
let currentConfirmData = null;   // { tanggal, items, raw }

// =========================================================
// INIT
// =========================================================
function initApp() {
    const isLoggedIn = localStorage.getItem("so_logged_in") === "true";

    loadChatHistories();

    autoThemeEnabled = localStorage.getItem("so_auto_theme") !== "false";

    const savedTheme = localStorage.getItem("so_theme") || "halloween-dark";
    setTheme(savedTheme);

    updateTimeTheme();
    updateApiKeyDisplay();
    updateAutoThemeDisplay();

    const savedPin = localStorage.getItem("so_pin");
    if (savedPin) {
        const hint = document.querySelector(".pin-hint");
        if (hint) hint.textContent = "";
    }

    if (isLoggedIn) {
        showScreen("homeScreen");
        startLiveClock();
        loadMiniDashboard();
        startDashboardAutoRefresh();
    } else {
        showScreen("loginScreen");
    }

    bindPinKeypad();
    bindChatInput();

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
    updateApiKeyDisplay();
    updateAutoThemeDisplay();
    showScreen("settingsScreen");
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
// MINI DASHBOARD — Fetch dari /api/yui/rekap
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
    const _key = getApiKey();

    try {
        const resp = await fetch(_url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify({ mode: "bulan_ini" }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();

        const totalRak = data.total_rak || 0;
        const totalNominal = data.total_nominal || 0;
        const salesPeriode = data.sales_periode || 0;

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
            statusKey = "bahaya";
            statusEmoji = "🚨";
            statusText = "BAHAYA";
            statusColor = "merah";
        } else if (statusPersen >= 0.13) {
            statusKey = "waspada";
            statusEmoji = "⚠️";
            statusText = "WASPADA";
            statusColor = "kuning";
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

            // Load shift hari ini
            try {
                const shiftResp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/shift-hari-ini`, {
                    method: "GET",
                    headers: { "X-API-Key": _key },
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
                        if (shiftParts.length) {
                            runningParts.push(`🌸 Hana: ${shiftParts.join(" | ")}`);
                        }
                    }
                }
            } catch (e) {
                // Skip kalau gagal
            }

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
            runningTextContainer.innerHTML = `<div class="running-inner" style="color: var(--danger); padding-left: 40px;">⚠️ Gagal: ${err.name} — ${err.message}</div>`;
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
// HELPER — Format Rupiah Ringkas
// =========================================================
function formatRupiahRingkas(nominal) {
    const abs = Math.abs(nominal);
    let formatted = "";

    if (abs >= 1_000_000_000) {
        formatted = (nominal / 1_000_000_000).toFixed(2) + "M";
    } else if (abs >= 1_000_000) {
        formatted = (nominal / 1_000_000).toFixed(1) + "jt";
    } else if (abs >= 1_000) {
        formatted = (nominal / 1_000).toFixed(0) + "rb";
    } else {
        formatted = nominal.toFixed(0);
    }

    return formatted;
}


// =========================================================
// RUNNING TEXT HELPER — Seamless Loop
// =========================================================
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


// =========================================================
// TOAST MINI — notifikasi kecil
// =========================================================
let toastTimer = null;

function showToastMini(message, type = "success") {
    // Hapus toast lama
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

function getApiKey() {
    return localStorage.getItem("so_api_key") || CONFIG.API_KEY;
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
function changePin() {
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
    localStorage.setItem("so_pin", newPin);
    showToastMini("✅ PIN berhasil diubah", "success");
}


// =========================================================
// STREAMLIT
// =========================================================
function loadStreamlit() {
    const iframe = document.getElementById("streamlitFrame");
    const loading = document.getElementById("streamlitLoading");
    if (!iframe) return;

    iframe.src = "about:blank";
    if (loading) loading.classList.remove("hidden");

    setTimeout(() => {
        iframe.src = CONFIG.STREAMLIT_URL;

        setTimeout(() => {
            if (loading) loading.classList.add("hidden");
        }, 4000);
    }, 100);
}

function openStreamlitInBrowser() {
    window.open(CONFIG.STREAMLIT_URL, "_blank");
}
// =========================================================
// MASTER SHIFT v1.3 — LOAD & RENDER
// =========================================================

// =========================================================
// SET PERIOD
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


// =========================================================
// HELPER — Hitung tanggal berdasarkan period
// =========================================================
function getShiftDateRange() {
    const today = new Date();
    let start = new Date();
    let end = new Date();

    if (shiftPeriod === "hari_ini") {
        start = today;
        end = today;
    } else if (shiftPeriod === "minggu") {
        // Senin s/d Minggu minggu ini
        const dayOfWeek = today.getDay();  // 0=Sunday
        const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;  // mundur ke Senin
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

    return { start, end };
}


// =========================================================
// HELPER — Format tanggal
// =========================================================
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


// =========================================================
// LOAD PERSONIL LIST
// =========================================================
async function loadPersonilList() {
    const filterSelect = document.getElementById("personilFilter");
    const personilList = document.getElementById("personilList");
    const _key = getApiKey();

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/personil`, {
            method: "GET",
            headers: { "X-API-Key": _key },
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        personilData = data.data || [];

        // Update filter dropdown
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

        // Render di modal
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


// =========================================================
// RENDER PERSONIL LIST (di modal)
// =========================================================
function renderPersonilList() {
    const container = document.getElementById("personilList");
    if (!container) return;

    if (!personilData || personilData.length === 0) {
        container.innerHTML = `
            <div class="loading-state">
                <p>Belum ada personil</p>
            </div>
        `;
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


// =========================================================
// LOAD MASTER SHIFT
// =========================================================
async function loadMasterShift() {
    const container = document.getElementById("shiftList");
    const summary = document.getElementById("shiftSummary");
    const _key = getApiKey();

    if (!container) return;

    // Loading state
    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Memuat jadwal shift...</p>
        </div>
    `;

    try {
        const range = getShiftDateRange();
        const startStr = range.start.toISOString().slice(0, 10);
        const endStr = range.end.toISOString().slice(0, 10);

        const filterSelect = document.getElementById("personilFilter");
        const namaFilter = filterSelect ? filterSelect.value : "";

        const body = {
            tgl_start: startStr,
            tgl_end: endStr,
        };
        if (namaFilter) body.nama_filter = namaFilter;

        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/master-shift`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify(body),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();

        if (!data.success) {
            throw new Error(data.error || "Gagal load data");
        }

        masterShiftData = data.data || [];

        renderShiftList();
        renderShiftSummary(data);

    } catch (err) {
        console.error("[MasterShift] Error:", err);
        container.innerHTML = `
            <div class="shift-summary-empty">
                <span class="empty-icon">⚠️</span>
                <p>Gagal load data: ${err.message}</p>
            </div>
        `;
        if (summary) summary.innerHTML = "";
    }
}


// =========================================================
// RENDER SHIFT LIST
// =========================================================
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

    // Group by date
    const grouped = {};
    masterShiftData.forEach(row => {
        const tgl = row.tanggal;
        if (!grouped[tgl]) grouped[tgl] = [];
        grouped[tgl].push(row);
    });

    // Sort dates
    const sortedDates = Object.keys(grouped).sort();

    // Render
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


// =========================================================
// HELPER — Badge class
// =========================================================
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


// =========================================================
// RENDER SHIFT SUMMARY
// =========================================================
function renderShiftSummary(data) {
    const summary = document.getElementById("shiftSummary");
    if (!summary) return;

    const total = data.data ? data.data.length : 0;
    const periode = data.periode || "—";

    // Hitung statistik per kode
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
// MODAL KONFIRMASI UPDATE SHIFT v1.4
// =========================================================
function openConfirmShiftModal(data) {
    const modal = document.getElementById("confirmShiftModal");
    if (!modal) {
        console.error("[Modal] confirmShiftModal tidak ditemukan");
        return;
    }

    // Simpan data di state
    currentConfirmData = data;

    // Format tanggal
    const tglEl = document.getElementById("confirmModalDate");
    if (tglEl) tglEl.textContent = formatTanggalLong(data.tanggal);

    // Total
    const countEl = document.getElementById("confirmModalCount");
    if (countEl) countEl.textContent = `${data.items.length} orang`;

    // Render list items
    renderConfirmModalItems(data.items);

    // Reset tombol save
    const saveBtn = document.getElementById("confirmModalSaveBtn");
    if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = "✅ Konfirmasi";
    }

    // Tampilkan modal
    modal.classList.add("active");
}


function closeConfirmShiftModal() {
    const modal = document.getElementById("confirmShiftModal");
    if (modal) modal.classList.remove("active");

    // Reset state kalau user batal (bukan setelah save)
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


// =========================================================
// EKSEKUSI KONFIRMASI — klik tombol ✅
// =========================================================
async function executeConfirmShift() {
    if (!currentConfirmData) {
        showToastMini("❌ Tidak ada data untuk dikonfirmasi", "error");
        return;
    }

    const saveBtn = document.getElementById("confirmModalSaveBtn");
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';
    }

    const _key = getApiKey();
    const data = currentConfirmData;

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/save-batch`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify({
                tanggal: data.tanggal,
                items: data.items.map(it => ({
                    nama: it.nama,
                    kode_shift: it.kode_shift,
                })),
            }),
        });

        const result = await resp.json();

        if (!resp.ok || !result.success) {
            throw new Error(result.detail || result.message || `HTTP ${resp.status}`);
        }

        const savedCount = result.saved || data.items.length;

        // Tutup modal
        const modal = document.getElementById("confirmShiftModal");
        if (modal) modal.classList.remove("active");

        // Push success bubble ke chat
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

        // Refresh Master Shift kalau lagi di screen itu
        const masterScreen = document.getElementById("masterShiftScreen");
        if (masterScreen && masterScreen.classList.contains("active")) {
            loadMasterShift();
        }

        // Refresh running text di home (kalau lagi di home)
        const homeScreen = document.getElementById("homeScreen");
        if (homeScreen && homeScreen.classList.contains("active")) {
            loadMiniDashboard();
        }

        showToastMini(`✅ ${savedCount} shift tersimpan`, "success");

        // Clear state
        currentConfirmData = null;

    } catch (err) {
        console.error("[ConfirmShift] Error:", err);

        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = "✅ Konfirmasi";
        }

        // Push error bubble
        const errMsg = {
            role: "assistant",
            content: `⚠️ Gagal simpan: ${err.message}`,
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
// MODAL — KELOLA PERSONIL v1.3
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


// =========================================================
// TAMBAH PERSONIL
// =========================================================
async function addNewPersonil() {
    const input = document.getElementById("newPersonilName");
    if (!input) return;

    const nama = input.value.trim().toUpperCase();
    if (!nama || nama.length < 2) {
        showToastMini("❌ Nama minimal 2 karakter", "error");
        return;
    }

    const _key = getApiKey();

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/personil/add`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify({ nama: nama }),
        });

        const data = await resp.json();

        if (!resp.ok || !data.success) {
            throw new Error(data.detail || data.message || `HTTP ${resp.status}`);
        }

        input.value = "";
        showToastMini(`✅ ${nama} ditambahkan`, "success");

        // Reload personil list
        await loadPersonilList();

    } catch (err) {
        console.error("[AddPersonil] Error:", err);
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}


// =========================================================
// HAPUS PERSONIL — dengan konfirmasi soft/force
// =========================================================
function deletePersonilConfirm(nama) {
    // Modal konfirmasi custom
    const html = `
        <div style="text-align: left;">
            <p style="font-size: 14px; margin-bottom: 12px;">
                Hapus personil <b style="color: var(--accent-orange);">${nama}</b>?
            </p>
            <label style="display: flex; align-items: center; gap: 8px; padding: 10px; background: var(--bg-tertiary); border-radius: 8px; cursor: pointer; margin-bottom: 12px;">
                <input type="checkbox" id="forceDeleteCheck" style="width: 18px; height: 18px; accent-color: var(--danger);">
                <span style="font-size: 12px;">⚠️ <b>Force delete</b> — hapus history juga (permanent)</span>
            </label>
            <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 16px;">
                Kalau gak dicentang, personil cuma dinonaktifkan (history tetap tersimpan).
            </p>
            <div style="display: flex; gap: 8px;">
                <button class="confirm-btn confirm-btn-cancel" onclick="closeDeleteModal()">
                    ❌ Batal
                </button>
                <button class="confirm-btn confirm-btn-save" style="background: linear-gradient(135deg, #ee5253, #c73133);" onclick="deletePersonilExecute('${nama}')">
                    🗑️ Hapus
                </button>
            </div>
        </div>
    `;

    // Pakai modal personil yang udah ada — inject konfirmasi
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
    const _key = getApiKey();

    closeDeleteModal();

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/personil/delete`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify({ nama: nama, force: force }),
        });

        const data = await resp.json();

        if (!resp.ok || !data.success) {
            throw new Error(data.detail || data.message || `HTTP ${resp.status}`);
        }

        showToastMini(data.message || `✅ ${nama} dihapus`, "success");
        await loadPersonilList();

    } catch (err) {
        console.error("[DeletePersonil] Error:", err);
        showToastMini(`❌ Gagal: ${err.message}`, "error");
    }
}


// =========================================================
// CHAT — RENDER HISTORY (dengan konfirmasi)
// =========================================================
function renderChatHistory() {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const history = chatHistories[currentBot] || [];
    const bot = BOTS[currentBot];

    // Empty state — welcome bubble
    if (history.length === 0) {
        container.innerHTML = `
            <div class="chat-message-wrapper ai">
                <div class="chat-avatar">${bot.emoji}</div>
                <div class="bubble bubble-ai bubble-welcome">
Halo Bos! 👋

Aku <b>${bot.emoji} ${bot.name}</b> — ${bot.role}.

${getWelcomeText(currentBot)}
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = "";

    history.forEach((msg, idx) => {
        const isUser = msg.role === "user";

        // Wrapper untuk bubble + avatar
        const wrapper = document.createElement("div");
        wrapper.className = `chat-message-wrapper ${isUser ? "user" : "ai"}`;
        
        // ============================================================
        // AVATAR
        // ============================================================
        const avatar = document.createElement("div");
        if (isUser) {
            avatar.className = "chat-avatar avatar-user";
            avatar.textContent = "👤";
        } else {
            avatar.className = "chat-avatar";
            avatar.textContent = bot.emoji;
        }
        wrapper.appendChild(avatar);
        
        // ============================================================
        // BUBBLE CONTENT WRAPPER (ini yang isi bubble + timestamp)
        // ============================================================
        const bubbleWrapper = document.createElement("div");
        bubbleWrapper.className = `bubble-content ${isUser ? "user" : "ai"}`;

        // === KALAU PESAN KONFIRMASI ===
        if (msg.isConfirm && msg.confirmData) {
            const confirmBubble = renderConfirmBubble(msg, idx);
            bubbleWrapper.appendChild(confirmBubble);
        } else {
            // === BUBBLE BIASA ===
            const bubble = document.createElement("div");
            bubble.className = `bubble bubble-${isUser ? "user" : "ai"}`;

            // Custom class berdasarkan tipe pesan
            if (msg.isSuccess) {
                bubble.classList.add("bubble-success");
            } else if (msg.isError) {
                bubble.classList.add("bubble-error");
            } else if (msg.isCancel) {
                bubble.classList.add("bubble-error");
            } else if (msg.isConfirmTrigger) {
                bubble.classList.add("bubble-confirm-trigger");
            }

            // Render content
            if (msg.isSuccess && msg.content.includes("🌸")) {
                // Custom render untuk success + shift summary
                bubble.innerHTML = formatSuccessMessage(msg.content);
            } else {
                bubble.innerHTML = formatMessage(msg.content);
            }

            bubbleWrapper.appendChild(bubble);
        }

        // === TIMESTAMP ===
        const time = document.createElement("div");
        time.className = `bubble-time ${!isUser ? "bubble-time-ai" : ""}`;
        time.textContent = formatTime(msg.timestamp);

        bubbleWrapper.appendChild(time);
        wrapper.appendChild(bubbleWrapper);
        container.appendChild(wrapper);
    });
}


// =========================================================
// HELPER — Format Success Message
// =========================================================
function formatSuccessMessage(text) {
    if (!text) return "";

    // Split by line
    const lines = text.split("\n");
    let html = "";
    let inSummary = false;
    let summaryLines = [];

    lines.forEach(line => {
        const trimmed = line.trim();

        if (trimmed.startsWith("✅")) {
            // Header success
            html += `<div class="success-header">${escapeHtml(trimmed)}</div>`;
        } else if (trimmed.startsWith("🌸")) {
            // Start shift summary
            inSummary = true;
            summaryLines = [];
        } else if (inSummary && trimmed) {
            // Item dalam summary
            summaryLines.push(trimmed);
        } else if (trimmed) {
            html += `<div style="margin-top: 4px;">${escapeHtml(trimmed)}</div>`;
        }
    });

    // Render summary
    if (summaryLines.length > 0) {
        html += `<div class="shift-summary-chat">`;
        summaryLines.forEach(line => {
            html += `<div class="shift-summary-chat-line">${escapeHtml(line)}</div>`;
        });
        html += `</div>`;
    }

    return html;
}

// =========================================================
// RENDER BUBBLE KONFIRMASI
// =========================================================
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

    // Item sejajar horizontal — inline
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
        <div class="confirm-chips">
            ${itemsHtml}
            ${moreHtml}
        </div>
        ${actionsHtml}
        ${statusHtml}
    `;

    return bubble;
}
// =========================================================
// HANDLE KONFIRMASI — SIMPAN
// =========================================================
async function handleConfirmSave(idx) {
    const history = chatHistories[currentBot] || [];
    const msg = history[idx];
    if (!msg || !msg.confirmData) return;

    const btnSave = document.getElementById(`confirmBtnSave_${idx}`);
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<span class="btn-spinner"></span> Menyimpan...';
    }

    const _key = getApiKey();
    const data = msg.confirmData;

    try {
        const resp = await fetch(`${CONFIG.BACKEND_URL}/api/hana/save-batch`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": _key,
            },
            body: JSON.stringify({
                tanggal: data.tanggal,
                items: data.items.map(it => ({
                    nama: it.nama,
                    kode_shift: it.kode_shift,
                })),
            }),
        });

        const result = await resp.json();

        if (!resp.ok || !result.success) {
            throw new Error(result.detail || result.message || `HTTP ${resp.status}`);
        }

        // Mark as resolved
        msg.resolved = true;
        msg.resolvedStatus = "saved";

        // Add success message
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

        // Refresh shift list kalau di master shift screen
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


// =========================================================
// HANDLE KONFIRMASI — BATAL
// =========================================================
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


// =========================================================
// HELPER — Shift summary text untuk chat
// =========================================================
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
// CHAT — BIND INPUT & SEND MESSAGE
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


// =========================================================
// SEND MESSAGE
// =========================================================
async function sendMessage() {
    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSend");

    if (!input || !sendBtn) return;

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

    showLoadingBubble();

    try {
        const bot = BOTS[currentBot];

        const history = chatHistories[currentBot]
            .slice(-7, -1)
            .filter(m => !m.isConfirm && !m.isSuccess && !m.isCancel && !m.isError)
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

        // === KALAU HANA MINTA KONFIRMASI ===
        if (data.needs_confirm && data.parsed && data.parsed.items) {
            // Push bubble pendek
            const shortMsg = {
                role: "assistant",
                content: data.text || `Oke Bos, aku catat ${data.parsed.items.length} perubahan shift. Cek detailnya ya! 🌸`,
                timestamp: Date.now(),
            };
            chatHistories[currentBot].push(shortMsg);
            saveChatHistories();
            renderChatHistory();
            scrollToBottom();
        
            // Trigger modal
            setTimeout(() => {
                openConfirmShiftModal({
                    tanggal: data.parsed.tanggal,
                    items: data.parsed.items,
                    raw: data.parsed.raw || text,
                });
            }, 400);
        
            hideLoadingBubble();
            sendBtn.disabled = false;
            input.focus();
            return;  // Stop di sini, jangan render bubble konfirmasi lama
        } else {
            // === CHAT BIASA ===
            const aiMsg = {
                role: "assistant",
                content: data.text || "(kosong)",
                timestamp: Date.now(),
                meta: {
                    model: data.model || null,
                    intent: data.intent || null,
                },
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

    html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");
    html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.25);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');
    html = html.replace(/^[\-\*]\s+(.+)$/gm, "• $1");
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
            return "Aku bisa:\n• Cek jadwal shift\n• Update/hapus shift (ketik natural)\n• Saran pengganti\n• Cek konflik jadwal\n\nContoh: <i>\"Pagi: Pandu, Tika. Siang: Reza\"</i>";
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
// AUTO REFRESH MINI DASHBOARD tiap 5 menit (kalau di home)
// =========================================================
setInterval(() => {
    const homeScreen = document.getElementById("homeScreen");
    if (homeScreen && homeScreen.classList.contains("active")) {
        loadMiniDashboard();
    }
}, 5 * 60 * 1000);


// =========================================================
// BOOT
// =========================================================
document.addEventListener("DOMContentLoaded", initApp);