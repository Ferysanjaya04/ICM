
"use strict";

const matchForm = document.getElementById("match-form");
const resumeSelect = document.getElementById("resume-select");
const jobTextInput = document.getElementById("job-text");
const analyzeButton = document.getElementById("analyze-button");

const SCORE_COMPONENTS = [
  {
    label: "Semantic Similarity",
    weight: 25,
    keys: ["semantic", "semantic_score", "semantic_similarity"]
  },
  {
    label: "Skill Matching",
    weight: 40,
    keys: ["skill", "skills", "skill_score"]
  },
  {
    label: "Experience Matching",
    weight: 20,
    keys: ["experience", "experience_score"]
  },
  {
    label: "Education Matching",
    weight: 15,
    keys: ["education", "education_score"]
  }
];

function showMatchError(message) {
  const element = document.getElementById("match-message");
  element.textContent = message;
  element.hidden = false;
}

function clearMatchError() {
  const element = document.getElementById("match-message");
  element.textContent = "";
  element.hidden = true;
}

function redirectToLogin() {
  AuthStorage.clear();
  window.location.replace("./login.html");
}

async function getAuthenticatedUser() {
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

async function loadResumeOptions() {
  const response = await ICMApi.listResumes();
  const resumes = Array.isArray(response.resumes)
    ? response.resumes
    : [];

  resumeSelect.replaceChildren();

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = resumes.length
    ? "Pilih CV untuk dianalisis"
    : "Belum ada CV. Upload terlebih dahulu.";

  resumeSelect.append(placeholder);

  resumes.forEach((resume) => {
    const option = document.createElement("option");
    option.value = resume.id;
    option.textContent = resume.original_filename || "Untitled CV";

    if (resume.has_extracted_text === false) {
      option.disabled = true;
      option.textContent += " (teks tidak tersedia)";
    }

    resumeSelect.append(option);
  });

  resumeSelect.disabled = resumes.length === 0;

  return resumes.length;
}

async function initializeMatchPage() {
  try {
    const user = await getAuthenticatedUser();

    document.getElementById("current-user").textContent =
      user.username || "ICM User";

    // Daftar CV hanya diambil setelah autentikasi valid.
    await loadResumeOptions();

  } catch (error) {
    if (
      !AuthStorage.getAccessToken() ||
      error.message.includes("Sesi")
    ) {
      redirectToLogin();
      return;
    }

    showMatchError(
      `Gagal memuat daftar CV: ${error.message}`
    );

  } finally {
    document.getElementById("page-loading").hidden = true;
    document.getElementById("job-match-app").hidden = false;
  }
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (typeof value === "object") {
    return null;
  }

  const number = Number(
    typeof value === "string"
      ? value.trim().replace("%", "")
      : value
  );

  return Number.isFinite(number) ? number : null;
}

function getFirstAvailable(object, keys) {
  if (!object || typeof object !== "object") {
    return null;
  }

  for (const key of keys) {
    const value = object[key];

    if (value !== undefined && value !== null) {
      return value;
    }
  }

  return null;
}

function readScore(value) {
  if (value && typeof value === "object") {
    value = getFirstAvailable(
      value,
      ["score", "percentage", "value", "match_percentage"]
    );
  }

  const number = toNumber(value);

  // Persentase ICM diharapkan berada pada 0-100.
  // Jangan mengarang skor bila formatnya berbeda.
  return number !== null && number >= 0 && number <= 100
    ? number
    : null;
}

function formatPercentage(score) {
  return score === null
    ? "—"
    : `${score.toFixed(2)}%`;
}

function createScoreRow(label, value, weight) {
  const row = document.createElement("div");
  row.className = "score-row";

  const heading = document.createElement("div");
  heading.className = "score-row-header";

  const name = document.createElement("span");
  name.textContent = label;

  const number = document.createElement("strong");
  number.textContent = formatPercentage(value);

  heading.append(name, number);

  const track = document.createElement("div");
  track.className = "score-track";

  const fill = document.createElement("div");
  fill.className = "score-track-fill";

  fill.style.width = value === null
    ? "0%"
    : `${value}%`;

  track.append(fill);

  const weightText = document.createElement("p");
  weightText.className = "score-weight";
  weightText.textContent = `Bobot: ${weight}%`;

  row.append(heading, track, weightText);

  return row;
}

function renderScores(data) {
  const compatibility = data.compatibility;
  const scores = data.scores || {};

  const compatibilityValue = readScore(
    typeof compatibility === "object"
      ? getFirstAvailable(
          compatibility,
          [
            "score",
            "percentage",
            "value",
            "compatibility_score"
          ]
        )
      : compatibility
  );

  const level = getFirstAvailable(
    compatibility,
    ["level", "label", "compatibility_level"]
  ) || data.compatibility_level || "Tidak tersedia";

  document.getElementById("compatibility-value").textContent =
    formatPercentage(compatibilityValue);

  document.getElementById("compatibility-level").textContent =
    String(level);

  const circle = document.getElementById("score-circle");

  circle.style.setProperty(
    "--score",
    compatibilityValue === null
      ? "0%"
      : `${compatibilityValue}%`
  );

  const breakdown = document.getElementById("score-breakdown");
  breakdown.replaceChildren();

  SCORE_COMPONENTS.forEach((component) => {
    let rawValue = getFirstAvailable(
      scores,
      component.keys
    );

    if (rawValue === null) {
      rawValue = getFirstAvailable(
        data,
        component.keys
      );
    }

    const score = readScore(rawValue);

    breakdown.append(
      createScoreRow(
        component.label,
        score,
        component.weight
      )
    );
  });
}

function normalizeSkillList(raw) {
  if (Array.isArray(raw)) {
    return raw
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          return item.name || item.skill || item.label || "";
        }

        return "";
      })
      .filter(Boolean);
  }

  if (typeof raw === "string" && raw.trim()) {
    return raw
      .split(/[,;\n|]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [];
}

function renderSkillList(elementId, rawSkills, kind) {
  const container = document.getElementById(elementId);
  container.replaceChildren();

  const skills = normalizeSkillList(rawSkills);

  if (skills.length === 0) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent =
      "Tidak ada keterampilan yang tercatat pada bagian ini.";
    container.append(empty);
    return;
  }

  skills.forEach((skill) => {
    const chip = document.createElement("span");

    chip.className =
      `skill-chip skill-${kind}`;

    chip.textContent = skill;
    container.append(chip);
  });
}

function renderSkills(data) {
  const skillData = data.skills || {};

  const matched = getFirstAvailable(
    skillData,
    ["matched", "matched_skills"]
  ) ?? data.matched_skills;

  const missing = getFirstAvailable(
    skillData,
    ["missing", "missing_skills"]
  ) ?? data.missing_skills;

  renderSkillList(
    "matched-skills",
    matched,
    "matched"
  );

  renderSkillList(
    "missing-skills",
    missing,
    "missing"
  );
}

function recommendationToText(item) {
  if (typeof item === "string") {
    return item;
  }

  if (item && typeof item === "object") {
    return (
      item.message ||
      item.recommendation ||
      item.description ||
      item.text ||
      item.action ||
      JSON.stringify(item)
    );
  }

  return String(item);
}

function renderRecommendations(data) {
  const container = document.getElementById(
    "match-recommendations"
  );

  container.replaceChildren();

  const recommendations = data.recommendations;

  let items = [];

  if (Array.isArray(recommendations)) {
    items = recommendations;
  } else if (
    typeof recommendations === "string" &&
    recommendations.trim()
  ) {
    items = [recommendations];
  } else if (
    recommendations &&
    typeof recommendations === "object"
  ) {
    items = Object.values(recommendations).flat();
  }

  if (items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent =
      "Belum ada saran pengembangan yang tersedia.";

    container.append(empty);
    return;
  }

  const list = document.createElement("ul");
  list.className = "recommendations-list";

  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = recommendationToText(item);
    list.append(li);
  });

  container.append(list);
}

function renderMatchResult(data) {
  if (!data || typeof data !== "object") {
    throw new Error(
      "Respons analisis tidak memiliki format yang valid."
    );
  }

  renderScores(data);
  renderSkills(data);
  renderRecommendations(data);

  const selectedCV =
    resumeSelect.options[resumeSelect.selectedIndex]?.textContent
    || "CV terpilih";

  document.getElementById("result-subtitle").textContent =
    `Hasil analisis untuk ${selectedCV}.`;

  const resultSection = document.getElementById("result-section");

  resultSection.hidden = false;
  resultSection.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

jobTextInput.addEventListener("input", () => {
  document.getElementById("char-counter").textContent =
    `${jobTextInput.value.length} / 30000`;
});

matchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMatchError();

  const resumeId = resumeSelect.value;
  const jobText = jobTextInput.value.trim();

  if (!resumeId) {
    showMatchError("Silakan pilih CV terlebih dahulu.");
    return;
  }

  if (jobText.length < 10 || jobText.length > 30000) {
    showMatchError(
      "Deskripsi pekerjaan harus 10-30.000 karakter."
    );
    return;
  }

  analyzeButton.disabled = true;
  analyzeButton.textContent = "AI sedang menganalisis...";

  // Hasil analisis lama disembunyikan agar tidak
  // dikira sebagai hasil dari request baru.
  document.getElementById("result-section").hidden = true;

  try {
    const result = await ICMApi.createJobMatch(
      resumeId,
      jobText
    );

    renderMatchResult(result);

  } catch (error) {
    showMatchError(error.message);

  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = "Analyze Compatibility";
  }
});

document.getElementById("new-analysis-button")
  .addEventListener("click", () => {
    document.getElementById("result-section").hidden = true;
    clearMatchError();
    jobTextInput.focus();

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  });

initializeMatchPage();
