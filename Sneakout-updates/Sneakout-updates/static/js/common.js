const ICONS = {
  clock: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
  calendar: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
  settings: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
  bell: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 01-3.4 0"/></svg>',
  door: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 4l-7 1.4V21h7M13 4v17M13 4l7 1v16h-7"/><circle cx="9" cy="12" r="1"/></svg>',
  chevronRight: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"/></svg>',
  board: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  shield: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l7 4v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-4z"/></svg>',
};

// Build nav dynamically based on current user role
function buildNavItems() {
  const role = window.USER_ROLE || "user";
  const items = [
    { label: "Today",   icon: "clock",    path: "/today" },
    { label: "Week",    icon: "calendar", path: "/week" },
    { label: "Board",   icon: "board",    path: "/freeboard" },
    { label: "Settings",icon: "settings", path: "/settings" },
  ];
  if (role === "admin") {
    // Insert admin item before settings
    items.splice(3, 0, { label: "Admin", icon: "shield", path: "/admin" });
  }
  return items;
}

function renderBottomNav(activePath) {
  const mount = document.getElementById("bottom-nav-mount");
  if (!mount) return;
  const navItems = buildNavItems();
  const items = navItems.map(({ label, icon, path }) => {
    const active = path === activePath;
    return `<a class="nav-item ${active ? "active" : ""}" href="${path}">
      <span class="nav-icon-wrap">${ICONS[icon]}</span>
      <span>${label}</span>
    </a>`;
  }).join("");
  mount.innerHTML = `<nav class="bottom-nav"><div class="bottom-nav-inner">${items}</div></nav>`;
}

const TYPE_COLORS = { lecture: "#9d7bff", lab: "#4fc3a1", tutorial: "#f7b731", free: "#3a2a5c" };
const TYPE_LABELS = { lecture: "LEC", lab: "LAB", tutorial: "TUT", free: "FREE" };

function timelineItemHTML(entry, isLast) {
  const accent = TYPE_COLORS[entry.type];
  if (entry.type === "free") {
    return `
    <div class="timeline-row">
      <div class="timeline-rail">
        <span class="timeline-time">${entry.startTime}</span>
        <div class="timeline-dot-wrap">
          <div class="timeline-dot" style="background:${accent}"></div>
          ${!isLast ? `<div class="timeline-line"></div>` : ""}
        </div>
      </div>
      <div class="timeline-card-wrap">
        <div class="timeline-card free">
          <div style="width:36px;height:36px;border-radius:8px;background:rgba(58,42,92,0.4);display:flex;align-items:center;justify-content:center;color:var(--so-muted)">${ICONS.door}</div>
          <div>
            <p style="font-weight:500;font-size:14px;color:var(--so-muted);margin:0">Free Period</p>
            <p style="font-size:11px;color:rgba(123,111,160,0.6);margin:2px 0 0">${entry.startTime} – ${entry.endTime}</p>
          </div>
        </div>
      </div>
    </div>`;
  }
  return `
  <div class="timeline-row">
    <div class="timeline-rail">
      <span class="timeline-time ${entry.isCurrent ? "current" : ""}">${entry.startTime}</span>
      <div class="timeline-dot-wrap">
        <div class="timeline-dot ${entry.isCurrent ? "pulse" : ""}" style="background:${accent}"></div>
        ${!isLast ? `<div class="timeline-line"></div>` : ""}
      </div>
    </div>
    <div class="timeline-card-wrap">
      <div class="timeline-card ${entry.isCurrent ? "current" : ""}">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <span class="type-tag" style="background:${accent}22;color:${accent};border:1px solid ${accent}44">${TYPE_LABELS[entry.type]||entry.type}</span>
              <span style="font-size:10px;color:var(--so-muted)">${entry.code||""}</span>
              ${entry.isCurrent ? `<span class="now-tag">NOW</span>` : ""}
            </div>
            <p style="font-weight:600;font-size:14px;margin:0">${entry.subject||""}</p>
            <p style="font-size:11px;color:var(--so-muted);margin:2px 0 0">${entry.faculty||""}</p>
          </div>
          <div style="text-align:right;flex-shrink:0">
            <div style="font-weight:600;font-size:12px;color:${accent}">${entry.startTime}</div>
            <div style="font-size:10px;color:rgba(123,111,160,0.7)">${entry.endTime}</div>
            <div style="font-size:10px;margin-top:4px;padding:2px 6px;border-radius:6px;background:rgba(58,42,92,0.5);color:var(--so-muted)">${entry.room||""}</div>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}
