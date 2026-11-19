
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

async function historyGetUser() {
  return ICMApi.getMe();
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
  if(item.id) card.dataset.analysisId = String(item.id);
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
  const quality = historyElement('div');
  ICMTransparency.renderQuality(quality, item, '', true);
  card.append(quality);
  const assessment = historyElement('div');
  ICMTransparency.renderAssessment(assessment, item, '');
  card.append(assessment);

  const detail = historyElement('details');
  detail.append(historyElement('summary', '', 'Lihat detail analisis'));
  const fields = [['Semantic', item.semantic_score ?? item.scores?.semantic], ['Skill', item.skill_score ?? item.scores?.skill], ['Experience', item.experience_score ?? item.scores?.experience], ['Education', item.education_score ?? item.scores?.education]];
  for (const [name, value] of fields) detail.append(historyElement('p', 'history-detail-row', `${name}: ${value === null || value === undefined ? 'Belum dapat dinilai' : historyPercent(typeof value === 'object' ? value.score : value)}`));
  card.append(detail);
  return card;
}

function historyCareerCard(item) {
  const card = historyElement("article", "history-item");
  if(item.id) card.dataset.analysisId = String(item.id);
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

  const quality = historyElement('div');
  ICMTransparency.renderQuality(quality, item, '', true);
  card.append(quality);
  card.append(historyElement('p', '', 'Top 3 ditampilkan sesuai urutan tersimpan; probabilitas kategori berbeda dari skill match.'));
  for (const role of roles.slice(0, 3)) {
    const probability = Number(role.category_probability);
    const validProbability = role.category_probability !== null && role.category_probability !== undefined && Number.isFinite(probability) && probability >= 0 && probability <= 1;
    const coverage = ICMTransparency.requirementsKnown(role) && role.match_percentage !== null && role.match_percentage !== undefined
      ? historyPercent(role.match_percentage) : 'Persyaratan belum tersedia';
    card.append(historyElement('p', '', `${role.role_title || 'Role'}: probabilitas kategori ${validProbability ? (probability * 100).toFixed(2) + '%' : 'tidak tersedia'}; skill match ${coverage}.`));
  }
  const detail = historyElement('details');detail.append(historyElement('summary', '', 'Lihat detail rekomendasi'));
  for (const role of roles.slice(0,3)) {
    const missing = Array.isArray(role.missing_skills) ? role.missing_skills : [];
    detail.append(historyElement('p', 'history-detail-row', `${role.role_title || 'Role'} — ${ICMTransparency.requirementsKnown(role) ? (missing.length ? 'Kebutuhan belum terbukti: '+missing.join(', ') : 'Tidak ada gap tersimpan yang ditampilkan.') : 'Persyaratan belum tersedia.'}`));
  }
  card.append(detail);
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
  if (historyRefresh.disabled) return;
  historyRefresh.disabled = true;
  historyClearMessage();

  historyList.replaceChildren();
  historyEmpty("Memuat riwayat dari Django...");

  const [matchesResult, careersResult] =
    await Promise.allSettled([
      ICMApi.listJobMatches(),
      ICMApi.listCareerRecommendations()
    ]);

  for (const result of [matchesResult, careersResult]) {
    if (result.status === "rejected" && ICMApi.handleSessionError(result.reason)) return;
  }
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
    const query = new URLSearchParams(location.search);
    if (query.get('type') === 'career') setHistoryTab('careers');
    const selected = [...historyList.children].find(el => el.dataset.analysisId === query.get('id'));
    if (selected) { const detail = selected.querySelector('details');if(detail)detail.open=true;selected.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'}); }


  } catch (error) {
    // Gagal autentikasi: jangan menampilkan data pengguna.
    if (ICMApi.handleSessionError(error)) return;
    document.getElementById("history-loading").hidden = true;
    document.getElementById("history-app").hidden = false;
    historyShowMessage(error.message + " Muat ulang halaman untuk mencoba lagi.");
  }
}

initializeHistory();
