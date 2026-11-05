
"use strict";

const historyState = {
  activeTab: "matches",
  matches: [],
  careers: [],
  errors: {
    matches: null,
    careers: null
  }
};

const historyList = document.getElementById("history-list");
const historyRefresh = document.getElementById("history-refresh");
const historyMessage = document.getElementById("history-message");

function historyElement(tag, className, text) {
  const element = document.createElement(tag);

  if (className) element.className = className;

  if (text !== undefined && text !== null) {
    element.textContent = String(text);
  }

  return element;
}

function historyEmpty(message) {
  historyList.append(
    historyElement("p", "history-empty", message)
  );
}

function historyShowMessage(message) {
  historyMessage.textContent = message;
  historyMessage.hidden = false;
}

function historyClearMessage() {
  historyMessage.textContent = "";
  historyMessage.hidden = true;
}

function historyLoginRedirect() {
  AuthStorage.clear();
  window.location.replace("./login.html");
}

async function historyGetUser() {
  if (!AuthStorage.getAccessToken()) {
    throw new Error("Belum login.");
  }

  try {
    return await ICMApi.getMe();
  } catch {
    await ICMApi.refreshAccessToken();
    return ICMApi.getMe();
  }
}

function historyFormatDate(value) {
  if (!value) return "Tanggal tidak tersedia";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Tanggal tidak tersedia";
  }

  return date.toLocaleString("id-ID", {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function historyPercent(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number) ||
      number < 0 || number > 100) {
    return "—";
  }

  return `${number.toFixed(2)}%`;
}

function historyMatchScore(item) {
  const compatibility = item.compatibility;

  if (
    compatibility &&
    typeof compatibility === "object"
  ) {
    return (
      compatibility.score ??
      compatibility.percentage ??
      compatibility.value ??
      compatibility.compatibility_score ??
      null
    );
  }

  return compatibility ??
    item.compatibility_score ??
    null;
}

function historyAddChip(container, text) {
  container.append(
    historyElement("span", "history-chip", text)
  );
}

function historyMatchCard(item) {
  const card = historyElement("article", "history-item");
  const top = historyElement("div", "history-item-top");
  const info = historyElement("div");

  const name =
    item.job_title_target ||
    item.job_title ||
    item.resume_filename ||
    item.cv_filename ||
    "CV & Job Matching";

  info.append(
    historyElement("h3", "", name)
  );

  info.append(
    historyElement(
      "p",
      "",
      historyFormatDate(
        item.created_at || item.date
      )
    )
  );

  const score = historyElement(
    "strong",
    "history-score",
    historyPercent(historyMatchScore(item))
  );

  top.append(info, score);
  card.append(top);

  if (item.job_description_text ||
      item.job_description) {
    const description =
      item.job_description_text ||
      item.job_description;

    card.append(
      historyElement(
        "p",
        "",
        String(description).slice(0, 180) +
        (String(description).length > 180 ? "..." : "")
      )
    );
  }

  const meta = historyElement("div", "history-meta");

  const compatibility = item.compatibility;
  const level =
    (compatibility &&
      typeof compatibility === "object" &&
      (compatibility.level || compatibility.label)) ||
    item.compatibility_level;

  if (level) {
    historyAddChip(meta, `Level: ${level}`);
  }

  historyAddChip(meta, "Feature 1");
  card.append(meta);

  return card;
}

function historyCareerCard(item) {
  const card = historyElement("article", "history-item");
  const top = historyElement("div", "history-item-top");
  const info = historyElement("div");

  info.append(
    historyElement(
      "h3",
      "",
      item.dominant_category || "Career Recommendation"
    )
  );

  info.append(
    historyElement(
      "p",
      "",
      historyFormatDate(item.created_at)
    )
  );

  top.append(info);
  card.append(top);

  const roles = Array.isArray(item.top_roles)
    ? [...item.top_roles].sort(
        (a, b) => Number(a.rank) - Number(b.rank)
      )
    : [];

  if (roles.length > 0) {
    const meta = historyElement("div", "history-meta");

    roles.slice(0, 3).forEach((role) => {
      historyAddChip(
        meta,
        `#${role.rank || "?"} ${role.role_title || "Role"}`
      );
    });

    card.append(meta);
  } else {
    card.append(
      historyElement(
        "p",
        "",
        "Detail Top-3 tidak tersedia pada data riwayat."
      )
    );
  }

  return card;
}

function normalizeHistoryCollection(data, fieldName) {
  if (Array.isArray(data)) {
    return data;
  }

  if (!data || typeof data !== "object") {
    return [];
  }

  if (Array.isArray(data[fieldName])) {
    return data[fieldName];
  }

  if (Array.isArray(data.results)) {
    return data.results;
  }

  return [];
}

function renderHistory() {
  historyList.replaceChildren();
  historyClearMessage();

  const isMatches = historyState.activeTab === "matches";

  document.getElementById("history-section-title").textContent =
    isMatches
      ? "Job Matching History"
      : "Career Recommendation History";

  const items = isMatches
    ? historyState.matches
    : historyState.careers;

  const error = isMatches
    ? historyState.errors.matches
    : historyState.errors.careers;

  if (error) {
    historyShowMessage(error);
  }

  if (items.length === 0) {
    historyEmpty(
      error
        ? "Riwayat belum berhasil dimuat."
        : "Belum ada riwayat untuk fitur ini."
    );
    return;
  }

  items.forEach((item) => {
    historyList.append(
      isMatches
        ? historyMatchCard(item)
        : historyCareerCard(item)
    );
  });
}

async function loadHistory() {
  historyRefresh.disabled = true;
  historyClearMessage();

  historyList.replaceChildren();
  historyEmpty("Memuat riwayat dari Django...");

  const [matchesResult, careersResult] =
    await Promise.allSettled([
      ICMApi.listJobMatches(),
      ICMApi.listCareerRecommendations()
    ]);

  if (matchesResult.status === "fulfilled") {
    historyState.matches = normalizeHistoryCollection(
      matchesResult.value,
      "results"
    );

    historyState.errors.matches = null;
  } else {
    historyState.errors.matches =
      matchesResult.reason?.message ||
      "Riwayat Job Matching gagal dimuat.";
  }

  if (careersResult.status === "fulfilled") {
    historyState.careers = normalizeHistoryCollection(
      careersResult.value,
      "recommendations"
    );

    historyState.errors.careers = null;
  } else {
    historyState.errors.careers =
      careersResult.reason?.message ||
      "Riwayat Career AI gagal dimuat.";
  }

  document.getElementById("match-total").textContent =
    historyState.errors.matches
      ? "—"
      : historyState.matches.length;

  document.getElementById("career-total").textContent =
    historyState.errors.careers
      ? "—"
      : historyState.careers.length;

  renderHistory();
  historyRefresh.disabled = false;
}

function setHistoryTab(tab) {
  historyState.activeTab = tab;

  const matchesButton =
    document.getElementById("tab-matches");

  const careerButton =
    document.getElementById("tab-career");

  matchesButton.classList.toggle(
    "active",
    tab === "matches"
  );

  careerButton.classList.toggle(
    "active",
    tab === "careers"
  );

  matchesButton.setAttribute(
    "aria-pressed",
    String(tab === "matches")
  );

  careerButton.setAttribute(
    "aria-pressed",
    String(tab === "careers")
  );

  renderHistory();
}

document.getElementById("tab-matches")
  .addEventListener("click", () => {
    setHistoryTab("matches");
  });

document.getElementById("tab-career")
  .addEventListener("click", () => {
    setHistoryTab("careers");
  });

historyRefresh.addEventListener("click", loadHistory);

async function initializeHistory() {
  try {
    const user = await historyGetUser();

    document.getElementById("history-user").textContent =
      user.username || "ICM Member";

    document.getElementById("history-loading").hidden = true;
    document.getElementById("history-app").hidden = false;

    await loadHistory();

  } catch (error) {
    // Gagal autentikasi: jangan menampilkan data pengguna.
    historyLoginRedirect();
  }
}

initializeHistory();
