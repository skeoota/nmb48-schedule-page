/**
 * NMB48 Theater Schedule & Member Portal Application Logic
 */

// Global State
let memberDatabase = [];
let memberMap = {}; // { id: memberObj }
let currentYear = 2026;
let currentMonth = 8;
let currentMonthlySchedules = [];
let currentLang = "ko";
let activeSelectedMemberId = null;
let activeSelectedPerformanceId = null;
let activeSearchQuery = "";
let currentViewMode = "schedule"; // "schedule" | "profiles"

// Multilingual i18n Translations Dictionary
const i18n = {
    ko: {
        tabSchedule: "극장 스케줄",
        tabProfiles: "멤버 프로필",
        searchPlaceholder: "공연명, 출연 멤버, 생탄제 검색...",
        today: "오늘",
        regularMembers: "정규생",
        researchStudents: "연구생",
        graduatedMembers: "졸업생",
        castTitle: "출연 멤버",
        castUndecided: "출연 멤버 미정 (추후 공지)",
        ticketSectionTitle: "FANY 공식 티켓 예매 / 응모 정보",
        noTicketInfo: "현재 등록된 FANY 티켓 판매 정보가 없습니다.",
        statusLotteryOpen: "추첨 접수 중",
        statusLotteryEnded: "추첨 접수 종료",
        statusUpcoming: "발매 예정",
        statusOnSale: "선착 발매 중",
        statusSoldOut: "매진",
        bookNow: "예매 바로가기",
        accordionDetail: "프로필 상세 정보",
        personalSchedule: "{month}월 출연 공연 ({count}회)",
        noPersonalSchedule: "이번 달 예정된 출연 공연이 없습니다.",
        nickname: "닉네임",
        birthday: "생년월일",
        bloodType: "혈액형",
        birthplace: "출신지",
        height: "신장",
        favoriteFood: "좋아하는 음식",
        hobby: "취미",
        specialty: "특기",
        dream: "장래희망",
        detailTitle: "공연 상세 정보",
        backToList: "목록으로",
        selectShowPrompt: "공연을 선택하면 상세 정보 및 티켓팅 링크를 확인할 수 있습니다.",
        selectMemberPrompt: "멤버를 선택하면 상세 프로필을 확인할 수 있습니다.",
        castSummaryLabel: "출연: ",
        favoriteAdd: "즐겨찾기 추가",
        favoriteRemove: "즐겨찾기 해제"
    },
    ja: {
        tabSchedule: "劇場スケジュール",
        tabProfiles: "メンバープロフィール",
        searchPlaceholder: "公演名、出演メンバー、生誕祭を検索...",
        today: "今日",
        regularMembers: "正規生",
        researchStudents: "研究生",
        graduatedMembers: "卒業生",
        castTitle: "出演メンバー",
        castUndecided: "出演メンバー未定 (決まり次第お知らせ)",
        ticketSectionTitle: "FANY公式チケット予約・受付情報",
        noTicketInfo: "現在登録されているFANYチケット販売情報はありません。",
        statusLotteryOpen: "抽選受付中",
        statusLotteryEnded: "抽選受付終了",
        statusUpcoming: "発売前",
        statusOnSale: "先着発売中",
        statusSoldOut: "完売",
        bookNow: "チケット申込み",
        accordionDetail: "プロフィール詳細情報",
        personalSchedule: "{month}月 出演公演 ({count}回)",
        noPersonalSchedule: "今月の出演予定公演はありません。",
        nickname: "ニックネーム",
        birthday: "生年月日",
        bloodType: "血液型",
        birthplace: "出身地",
        height: "身長",
        favoriteFood: "好きな食べ物",
        hobby: "趣味",
        specialty: "特技",
        dream: "将来の夢",
        detailTitle: "公演詳細情報",
        backToList: "一覧へ戻る",
        selectShowPrompt: "公演を選択すると詳細情報とチケット申込みリンクが表示されます。",
        selectMemberPrompt: "メンバーを選択するとプロフィール詳細が表示されます。",
        castSummaryLabel: "出演: ",
        favoriteAdd: "お気に入り追加",
        favoriteRemove: "お気に入り解除"
    },
    en: {
        tabSchedule: "Theater Schedule",
        tabProfiles: "Member Profiles",
        searchPlaceholder: "Search shows, members, birthday events...",
        today: "Today",
        regularMembers: "Regular Members",
        researchStudents: "Research Students",
        graduatedMembers: "Graduated Members",
        castTitle: "Performing Members",
        castUndecided: "Lineup to be announced",
        ticketSectionTitle: "FANY Official Ticket / Lottery Info",
        noTicketInfo: "No active FANY ticketing info at this moment.",
        statusLotteryOpen: "Lottery Open",
        statusLotteryEnded: "Lottery Ended",
        statusUpcoming: "Upcoming",
        statusOnSale: "On Sale (First-come)",
        statusSoldOut: "Sold Out",
        bookNow: "Apply / Purchase",
        accordionDetail: "Member Profile Details",
        personalSchedule: "Shows in Month {month} ({count} shows)",
        noPersonalSchedule: "No scheduled shows this month.",
        nickname: "Nickname",
        birthday: "Birthday",
        bloodType: "Blood Type",
        birthplace: "Birthplace",
        height: "Height",
        favoriteFood: "Favorite Food",
        hobby: "Hobby",
        specialty: "Special Skill",
        dream: "Future Dream",
        detailTitle: "Show Details",
        backToList: "Back to List",
        selectShowPrompt: "Select a show to view lineup and official ticketing links.",
        selectMemberPrompt: "Select a member to view details and SNS links.",
        castSummaryLabel: "Cast: ",
        favoriteAdd: "Add to Favorites",
        favoriteRemove: "Remove from Favorites"
    }
};

function t(key, params = {}) {
    let text = (i18n[currentLang] && i18n[currentLang][key]) || i18n["ko"][key] || key;
    for (const [k, v] of Object.entries(params)) {
        text = text.replace(new RegExp(`\\{${k}\\}`, "g"), v);
    }
    return text;
}

// --------------------------------------------------------------------------
// Initialization
// --------------------------------------------------------------------------

async function initApplication() {
    // 1. Initialize Date Controls
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1; // 1-12

    setupDateDropdowns();

    // 2. Load Members Database
    await loadMemberDatabase();

    // 3. Load Initial Monthly Schedules
    await loadMonthlySchedule(currentYear, currentMonth);

    // 4. Check URL Params or Saved Favorites
    const savedFav = localStorage.getItem("nmb_favorite_member");
    if (savedFav && memberMap[savedFav]) {
        selectMember(savedFav, false);
    }
}

function setupDateDropdowns() {
    const yearSelect = document.getElementById("year-select");
    const monthSelect = document.getElementById("month-select");

    yearSelect.innerHTML = "";
    for (let y = 2025; y <= 2028; y++) {
        const opt = document.createElement("option");
        opt.value = y;
        opt.textContent = `${y}년`;
        if (y === currentYear) opt.selected = true;
        yearSelect.appendChild(opt);
    }

    monthSelect.innerHTML = "";
    for (let m = 1; m <= 12; m++) {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = `${m}월`;
        if (m === currentMonth) opt.selected = true;
        monthSelect.appendChild(opt);
    }
}

// --------------------------------------------------------------------------
// Data Loading
// --------------------------------------------------------------------------

async function loadMemberDatabase() {
    try {
        const res = await fetch("member.json");
        if (!res.ok) throw new Error("member.json fetch failed");
        memberDatabase = await res.json();

        memberMap = {};
        for (const m of memberDatabase) {
            if (m.id) {
                memberMap[m.id] = m;
            }
        }
    } catch (e) {
        console.error("Error loading member.json:", e);
    }
}

async function loadMonthlySchedule(year, month) {
    const container = document.getElementById("timeline-container");
    container.innerHTML = `<div class="loading-text">${t("searchPlaceholder")}</div>`;

    const formattedMonth = String(month).padStart(2, "0");
    const filePath = `schedules/schedule_${year}-${formattedMonth}.json`;

    try {
        const res = await fetch(filePath);
        if (!res.ok) {
            currentMonthlySchedules = [];
        } else {
            currentMonthlySchedules = await res.json();
        }
    } catch (e) {
        currentMonthlySchedules = [];
    }

    renderTimeline();

    // Select first show by default if available on desktop
    if (currentMonthlySchedules.length > 0 && window.innerWidth > 1024) {
        showPerformanceDetail(currentMonthlySchedules[0].id, false);
    } else {
        renderDetailPlaceholder();
    }

    // Refresh active profile personal schedule if any
    if (activeSelectedMemberId) {
        selectMember(activeSelectedMemberId, false);
    }
}

// --------------------------------------------------------------------------
// Navigation & Mode Switching
// --------------------------------------------------------------------------

function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth < 1) {
        currentMonth = 12;
        currentYear -= 1;
    } else if (currentMonth > 12) {
        currentMonth = 1;
        currentYear += 1;
    }

    updateDropdownValues();
    loadMonthlySchedule(currentYear, currentMonth);
}

function handleSelectDateChange() {
    currentYear = parseInt(document.getElementById("year-select").value, 10);
    currentMonth = parseInt(document.getElementById("month-select").value, 10);
    loadMonthlySchedule(currentYear, currentMonth);
}

function goToToday() {
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1;
    updateDropdownValues();
    loadMonthlySchedule(currentYear, currentMonth);
}

function updateDropdownValues() {
    document.getElementById("year-select").value = currentYear;
    document.getElementById("month-select").value = currentMonth;
}

function switchLanguage(lang) {
    currentLang = lang;
    document.getElementById("tab-btn-schedule").textContent = t("tabSchedule");
    document.getElementById("tab-btn-profiles").textContent = t("tabProfiles");
    document.getElementById("timeline-search-input").placeholder = t("searchPlaceholder");
    document.getElementById("btn-today").textContent = t("today");

    renderTimeline();
    if (activeSelectedPerformanceId) {
        showPerformanceDetail(activeSelectedPerformanceId, false);
    }
    if (activeSelectedMemberId) {
        selectMember(activeSelectedMemberId, false);
    }
    if (currentViewMode === "profiles") {
        renderProfilesView();
    }
}

function switchViewMode(mode) {
    currentViewMode = mode;
    const scheduleBtn = document.getElementById("tab-btn-schedule");
    const profilesBtn = document.getElementById("tab-btn-profiles");
    const scheduleArea = document.getElementById("schedule-view-area");
    const profilesArea = document.getElementById("profiles-view-area");

    if (mode === "schedule") {
        scheduleBtn.classList.add("active");
        profilesBtn.classList.remove("active");
        scheduleArea.style.display = "flex";
        profilesArea.style.display = "none";
    } else {
        scheduleBtn.classList.remove("active");
        profilesBtn.classList.add("active");
        scheduleArea.style.display = "none";
        profilesArea.style.display = "block";
        renderProfilesView();
    }
}

// --------------------------------------------------------------------------
// View 1: Timeline Rendering
// --------------------------------------------------------------------------

function renderTimeline() {
    const container = document.getElementById("timeline-container");
    if (!container) return;

    if (!currentMonthlySchedules || currentMonthlySchedules.length === 0) {
        container.innerHTML = `<div class="profile-placeholder">${t("noPersonalSchedule")}</div>`;
        return;
    }

    // Filter by search query
    let filteredShows = currentMonthlySchedules;
    if (activeSearchQuery) {
        const q = activeSearchQuery.toLowerCase().trim();
        filteredShows = currentMonthlySchedules.filter(show => {
            const title = (show.title || "").toLowerCase();
            const fullTitle = (show.full_title || "").toLowerCase();
            const eventType = (show.event_type || "").toLowerCase();
            const rawMembers = (show.members_raw || "").toLowerCase();
            
            // Also search by cast member names from memberDatabase
            const memberNames = (show.members || []).map(mid => {
                const m = memberMap[mid];
                return m ? (m.name + " " + m.yomi).toLowerCase() : "";
            }).join(" ");

            return title.includes(q) || fullTitle.includes(q) || eventType.includes(q) || rawMembers.includes(q) || memberNames.includes(q);
        });
    }

    if (filteredShows.length === 0) {
        container.innerHTML = `<div class="profile-placeholder">${t("searchPlaceholder")}</div>`;
        return;
    }

    // Group shows by Date
    const groupedByDate = {};
    for (const show of filteredShows) {
        const d = show.date;
        if (!groupedByDate[d]) groupedByDate[d] = [];
        groupedByDate[d].push(show);
    }

    let html = "";
    for (const [dateStr, shows] of Object.entries(groupedByDate)) {
        const dateObj = new Date(dateStr);
        const dayNum = dateObj.getDate();
        const dayOfWeekIdx = dateObj.getDay(); // 0 = Sun, 6 = Sat
        const dayOfWeekStr = shows[0].day_of_week || ["日", "月", "火", "水", "木", "金", "土"][dayOfWeekIdx];

        let weekdayClass = "";
        if (dayOfWeekIdx === 0) weekdayClass = "sun sunday";
        else if (dayOfWeekIdx === 6) weekdayClass = "sat saturday";

        html += `
            <div class="timeline-day">
                <div class="day-num ${weekdayClass}">
                    <span>${dayNum}</span>
                    <span class="weekday ${weekdayClass}">(${dayOfWeekStr})</span>
                </div>
                <div class="day-content">
        `;

        for (const show of shows) {
            const isSelected = activeSelectedPerformanceId === show.id;
            const eventBadgeHTML = show.event_type ? `<span class="perf-event-badge">${show.event_type}</span>` : "";

            // Format Cast summary
            let castSummaryHTML = "";
            if (show.is_members_undecided) {
                castSummaryHTML = `<div class="day-cast-summary" style="color:#e63946; font-weight:600;">${t("castUndecided")}</div>`;
            } else if (show.members && show.members.length > 0) {
                const castNames = show.members.map(mid => {
                    const m = memberMap[mid];
                    const name = m ? m.name : mid;
                    if (activeSelectedMemberId && mid === activeSelectedMemberId) {
                        return `<span class="highlight-cast">${name}</span>`;
                    }
                    return name;
                }).join(", ");
                castSummaryHTML = `<div class="day-cast-summary"><strong>${t("castSummaryLabel")}</strong>${castNames}</div>`;
            }

            // Ticket Status Tag
            let ticketTagHTML = "";
            if (show.ticket_sales && show.ticket_sales.length > 0) {
                const activeSale = show.ticket_sales.find(s => s.status && s.status.includes("受付中") || s.status.includes("発売中"));
                if (activeSale) {
                    ticketTagHTML = `<div class="fany-ticket-badge-tag">🎟️ ${activeSale.sales_name} (${activeSale.status})</div>`;
                }
            }

            html += `
                <div class="perf-item-link ${isSelected ? 'selected' : ''}" onclick="showPerformanceDetail('${show.id}', true)">
                    <div class="perf-header-line">
                        <span class="perf-time-badge">${show.time}</span>
                        ${eventBadgeHTML}
                    </div>
                    <div class="day-title">${show.title}</div>
                    ${castSummaryHTML}
                    ${ticketTagHTML}
                </div>
            `;
        }

        html += `
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

// --------------------------------------------------------------------------
// Performance Detail Panel (Right Sub-Panel)
// --------------------------------------------------------------------------

function showPerformanceDetail(perfId, forceOpenMobile = true) {
    activeSelectedPerformanceId = perfId;
    const show = currentMonthlySchedules.find(s => s.id === perfId);
    if (!show) return;

    // Highlight in timeline list
    document.querySelectorAll(".perf-item-link").forEach(el => el.classList.remove("selected"));
    const selectedEl = document.querySelector(`.perf-item-link[onclick*="${perfId}"]`);
    if (selectedEl) selectedEl.classList.add("selected");

    const detailWrapper = document.getElementById("detail-wrapper");
    if (!detailWrapper) return;

    // Event tag
    const eventBadgeHTML = show.event_type ? `<span class="perf-event-badge" style="font-size:13px; padding:4px 10px;">${show.event_type}</span>` : "";

    // FANY Ticket Sales Cards
    let ticketCardsHTML = "";
    if (show.ticket_sales && show.ticket_sales.length > 0) {
        ticketCardsHTML = `
            <div class="ticket-section-box">
                <div class="ticket-section-title">
                    <span>🎟️</span>
                    <span>${t("ticketSectionTitle")}</span>
                </div>
                <div class="ticket-sales-list">
        `;

        for (const sale of show.ticket_sales) {
            const isEnded = sale.status && (sale.status.includes("終了") || sale.status.includes("完売"));
            const btnClass = isEnded ? "ticket-sale-btn ended" : "ticket-sale-btn active";
            const btnText = isEnded ? sale.status : `${sale.status || t("bookNow")} →`;

            ticketCardsHTML += `
                <div class="ticket-sale-card">
                    <div class="ticket-sale-info">
                        <div class="ticket-sale-name">${sale.sales_name}</div>
                        <div class="ticket-sale-period">📅 ${sale.period_start} ~ ${sale.period_end}</div>
                    </div>
                    ${sale.url ? `<a href="${sale.url}" target="_blank" rel="noopener noreferrer" class="${btnClass}">${btnText}</a>` : `<span class="${btnClass}">${btnText}</span>`}
                </div>
            `;
        }

        ticketCardsHTML += `
                </div>
            </div>
        `;
    } else {
        ticketCardsHTML = `
            <div class="ticket-section-box" style="background:#f8f9fa; border-color:#e9ecef;">
                <div class="ticket-section-title" style="color:#6c757d;">
                    <span>🎟️</span>
                    <span>${t("ticketSectionTitle")}</span>
                </div>
                <div style="font-size:12.5px; color:#6c757d;">${t("noTicketInfo")}</div>
            </div>
        `;
    }

    // Cast Members Grid
    let castGridHTML = "";
    if (show.is_members_undecided) {
        castGridHTML = `
            <div class="cast-grid-title">${t("castTitle")}</div>
            <div style="padding:16px; background:#fff5f5; border:1px solid #ffe3e3; border-radius:8px; color:#e63946; font-weight:700;">
                ⚠️ ${t("castUndecided")}
            </div>
        `;
    } else if (show.members && show.members.length > 0) {
        castGridHTML = `
            <div class="cast-grid-title">${t("castTitle")} (${show.members.length}명)</div>
            <div class="cast-grid">
        `;

        for (const mid of show.members) {
            const m = memberMap[mid];
            if (m) {
                const savedFav = localStorage.getItem("nmb_favorite_member");
                const isFav = savedFav === m.id;
                const favBadgeHTML = isFav ? `<span class="mini-card-fav-badge">★</span>` : "";

                castGridHTML += `
                    <div class="member-mini-card" onclick="selectMember('${m.id}', true)">
                        ${favBadgeHTML}
                        <img src="${m.thumbnail_url || m.image_url}" alt="${m.name}" class="mini-card-img" onerror="this.src='https://placehold.co/100x125/fae8c8/333333?text=${m.name}'">
                        <span class="card-name">${m.name}</span>
                    </div>
                `;
            } else {
                castGridHTML += `
                    <div class="member-mini-card">
                        <div class="mini-card-img" style="background:#eee; display:flex; align-items:center; justify-content:center; font-size:10px;">Guest</div>
                        <span class="card-name">${mid}</span>
                    </div>
                `;
            }
        }

        castGridHTML += `</div>`;
    }

    // Special Notes
    let notesHTML = "";
    if (show.special_notes && show.special_notes.length > 0) {
        notesHTML = `
            <div style="margin-top:20px; padding:14px; background:#f8f9fa; border:1px solid #e9ecef; border-radius:8px; font-size:12px; color:#6c757d;">
                ${show.special_notes.map(n => `<div>${n}</div>`).join("")}
            </div>
        `;
    }

    detailWrapper.innerHTML = `
        <div class="detail-meta-box">
            <span class="detail-meta-item">📅 ${show.date_display}</span>
            <span class="detail-meta-item">⏰ ${show.time} 개연</span>
            ${eventBadgeHTML}
        </div>
        <h2 class="detail-show-title">${show.title}</h2>
        ${ticketCardsHTML}
        ${castGridHTML}
        ${notesHTML}
    `;

    // Mobile Slider Activation
    if (forceOpenMobile && window.innerWidth <= 1024) {
        const panel = document.getElementById("detail-panel");
        panel.classList.add("active");
    }
}

function renderDetailPlaceholder() {
    const detailWrapper = document.getElementById("detail-wrapper");
    if (detailWrapper) {
        detailWrapper.innerHTML = `<div class="profile-placeholder">${t("selectShowPrompt")}</div>`;
    }
}

function closeDetailPanel() {
    const panel = document.getElementById("detail-panel");
    if (panel) panel.classList.remove("active");
}

// --------------------------------------------------------------------------
// Left Panel: Member Profile & Personal Schedule
// --------------------------------------------------------------------------

function selectMember(memberId, forceOpenDrawer = true) {
    activeSelectedMemberId = memberId;
    const member = memberMap[memberId];
    const leftPanelContent = document.getElementById("left-panel-content");
    if (!member || !leftPanelContent) return;

    const savedFav = localStorage.getItem("nmb_favorite_member");
    const isFav = savedFav === member.id;
    const favButtonHTML = `
        <button class="favorite-button ${isFav ? 'active' : ''}" onclick="toggleFavorite('${member.id}')" title="${isFav ? t('favoriteRemove') : t('favoriteAdd')}">
            ★
        </button>
    `;

    // Profile badge class
    let badgeClass = "regular";
    if (member.is_graduated || member.member_type === "졸업생") badgeClass = "graduated";
    else if (member.member_type === "연구생") badgeClass = "kenkyusei";

    // SNS Buttons
    let snsHTML = "";
    if (member.sns && member.sns.length > 0) {
        snsHTML = `
            <div class="profile-sns-list">
                ${member.sns.map(s => `<a href="${s.url}" target="_blank" rel="noopener noreferrer" class="sns-btn">🔗 ${s.name}</a>`).join("")}
            </div>
        `;
    }

    // Detail Profile Table
    const p = member.profile || {};
    const detailsTableHTML = `
        <table class="details-table">
            <tbody>
                ${p["生年月日"] ? `<tr><th>${t("birthday")}</th><td>${p["生年月日"]}</td></tr>` : ""}
                ${p["血液型"] ? `<tr><th>${t("bloodType")}</th><td>${p["血液型"]}</td></tr>` : ""}
                ${p["出身地"] ? `<tr><th>${t("birthplace")}</th><td>${p["出身地"]}</td></tr>` : ""}
                ${p["身長"] ? `<tr><th>${t("height")}</th><td>${p["身長"]}</td></tr>` : ""}
                ${p["好きな食べ物"] ? `<tr><th>${t("favoriteFood")}</th><td>${p["好きな食べ物"]}</td></tr>` : ""}
                ${p["趣味"] ? `<tr><th>${t("hobby")}</th><td>${p["趣味"]}</td></tr>` : ""}
                ${p["特技"] ? `<tr><th>${t("specialty")}</th><td>${p["特技"]}</td></tr>` : ""}
                ${p["将来の夢"] ? `<tr><th>${t("dream")}</th><td>${p["将来の夢"]}</td></tr>` : ""}
            </tbody>
        </table>
    `;

    // Calculate Personal Schedules for current month
    const personalShows = currentMonthlySchedules.filter(show => {
        return show.members && show.members.includes(member.id);
    });

    let personalScheduleHTML = "";
    if (personalShows.length > 0) {
        personalScheduleHTML = personalShows.map(show => `
            <div class="member-schedule-item ${show.id === activeSelectedPerformanceId ? 'active-schedule-item' : ''}" onclick="handlePersonalScheduleClick('${show.id}')">
                <div style="font-weight:700; color:var(--nmb-black); margin-bottom:2px;">📅 ${show.date_display} (${show.time})</div>
                <div style="color:#495057;">${show.title}</div>
            </div>
        `).join("");
    } else {
        personalScheduleHTML = `<div style="font-size:12.5px; color:#868e96; padding:8px 4px;">${t("noPersonalSchedule")}</div>`;
    }

    leftPanelContent.innerHTML = `
        <div class="profile-sticky-header">
            <div class="profile-name">
                ${member.name}
                ${favButtonHTML}
            </div>
            <div class="profile-yomi">${member.yomi || ""}</div>
            ${p["ニックネーム"] ? `<div class="profile-nickname-badge">🏷️ ${p["ニックネーム"]}</div>` : ""}
        </div>

        <div class="profile-card">
            <div class="profile-img-wrapper">
                <img src="${member.image_url || member.thumbnail_url}" alt="${member.name}" onerror="this.src='https://placehold.co/170x215/fae8c8/333333?text=${member.name}'">
            </div>
            <div class="profile-badge ${badgeClass}">${member.member_type || member.status}</div>
            ${snsHTML}
        </div>

        <!-- Accordion 1: Details -->
        <div class="accordion-header" onclick="toggleAccordion('profile-details-body', 'details-arrow')">
            <span>📋 ${t("accordionDetail")}</span>
            <span class="arrow-indicator" id="details-arrow">▼</span>
        </div>
        <div id="profile-details-body" class="accordion-content">
            ${detailsTableHTML}
        </div>

        <!-- Accordion 2: Monthly Shows -->
        <div class="accordion-header" onclick="toggleAccordion('profile-schedule-body', 'schedule-arrow')">
            <span>🎭 ${t("personalSchedule", { month: currentMonth, count: personalShows.length })}</span>
            <span class="arrow-indicator" id="schedule-arrow">▼</span>
        </div>
        <div id="profile-schedule-body" class="accordion-content">
            <div class="member-schedule-list">
                ${personalScheduleHTML}
            </div>
        </div>
    `;

    if (forceOpenDrawer && window.innerWidth <= 1024) {
        document.getElementById("left-panel").classList.add("drawer-active");
        document.getElementById("drawer-overlay").classList.add("active");
    }

    // Refresh timeline highlights
    renderTimeline();
}

function handlePersonalScheduleClick(perfId) {
    closeMobileDrawer();
    switchViewMode("schedule");
    showPerformanceDetail(perfId, true);

    setTimeout(() => {
        const target = document.querySelector(`.perf-item-link[onclick*="${perfId}"]`);
        if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, 150);
}

function toggleFavorite(memberId) {
    const currentFav = localStorage.getItem("nmb_favorite_member");
    if (currentFav === memberId) {
        localStorage.removeItem("nmb_favorite_member");
    } else {
        localStorage.setItem("nmb_favorite_member", memberId);
    }

    selectMember(memberId, false);
    if (activeSelectedPerformanceId) {
        showPerformanceDetail(activeSelectedPerformanceId, false);
    }
    if (currentViewMode === "profiles") {
        renderProfilesView();
    }
}

function toggleAccordion(bodyId, arrowId) {
    const body = document.getElementById(bodyId);
    const arrow = document.getElementById(arrowId);
    if (!body || !arrow) return;

    if (body.classList.contains("collapsed")) {
        body.classList.remove("collapsed");
        arrow.textContent = "▼";
    } else {
        body.classList.add("collapsed");
        arrow.textContent = "▶";
    }
}

function closeMobileDrawer() {
    const leftPanel = document.getElementById("left-panel");
    const overlay = document.getElementById("drawer-overlay");
    if (leftPanel) leftPanel.classList.remove("drawer-active");
    if (overlay) overlay.classList.remove("active");
}

// --------------------------------------------------------------------------
// View 2: Member Profiles Grid View
// --------------------------------------------------------------------------

function renderProfilesView() {
    const container = document.getElementById("profiles-view-area");
    if (!container || !memberDatabase) return;

    const regularMembers = memberDatabase.filter(m => !m.is_graduated && m.member_type !== "연구생");
    const kenkyuseiMembers = memberDatabase.filter(m => !m.is_graduated && m.member_type === "연구생");
    const graduatedMembers = memberDatabase.filter(m => m.is_graduated || m.member_type === "졸업생");

    function renderGroup(title, members) {
        if (!members || members.length === 0) return "";
        const cardsHTML = members.map(m => {
            const savedFav = localStorage.getItem("nmb_favorite_member");
            const isFav = savedFav === m.id;
            const favBadgeHTML = isFav ? `<span class="mini-card-fav-badge" style="font-size:16px;">★</span>` : "";

            return `
                <div class="profile-grid-card" onclick="selectMember('${m.id}', true)">
                    ${favBadgeHTML}
                    <img src="${m.thumbnail_url || m.image_url}" alt="${m.name}" class="grid-img" onerror="this.src='https://placehold.co/100x126/fae8c8/333333?text=${m.name}'">
                    <span class="grid-name">${m.name}</span>
                    <span class="grid-yomi">${m.yomi || ""}</span>
                </div>
            `;
        }).join("");

        return `
            <div class="member-group-section">
                <div class="member-group-title">
                    <span>${title}</span>
                    <span class="member-group-count">(${members.length}명)</span>
                </div>
                <div class="profiles-grid">${cardsHTML}</div>
            </div>
        `;
    }

    container.innerHTML = `
        ${renderGroup(t("regularMembers"), regularMembers)}
        ${renderGroup(t("researchStudents"), kenkyuseiMembers)}
        ${renderGroup(t("graduatedMembers"), graduatedMembers)}
    `;
}

// --------------------------------------------------------------------------
// Search Handlers
// --------------------------------------------------------------------------

function handleSearchInput(value) {
    activeSearchQuery = value;
    const clearBtn = document.getElementById("search-clear-btn");
    if (clearBtn) clearBtn.style.display = value ? "block" : "none";
    renderTimeline();
}

function clearSearchInput() {
    const input = document.getElementById("timeline-search-input");
    if (input) {
        input.value = "";
        input.focus();
    }
    handleSearchInput("");
}

// On Page Load
window.onload = function () {
    initApplication();
};
