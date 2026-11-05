
"use strict";

const careerForm = document.getElementById("career-form");
const careerSelect = document.getElementById("career-resume-select");
const careerButton = document.getElementById("career-generate-button");

function careerText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function careerMessage(message) {
  const element = document.getElementById("career-message");
  element.textContent = message;
  element.hidden = false;
}

function clearCareerMessage() {
  const element = document.getElementById("career-message");
  element.textContent = "";
  element.hidden = true;
}

function careerLoginRedirect() {
  AuthStorage.clear();
  window.location.replace("./login.html");
}

async function careerAuthenticatedUser() {
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

async function initializeCareer() {
  try {
    const user = await careerAuthenticatedUser();

    careerText("career-user", user.username || "ICM Member");

    const result = await ICMApi.listResumes();
    const resumes = Array.isArray(result.resumes)
      ? result.resumes
      : [];

    careerSelect.replaceChildren();

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = resumes.length
      ? "Pilih CV yang ingin dianalisis"
      : "Belum ada CV. Upload terlebih dahulu.";

    careerSelect.append(placeholder);

    for (const resume of resumes) {
      const option = document.createElement("option");

      option.value = resume.id;
      option.textContent = resume.original_filename || "Untitled CV";

      if (resume.has_extracted_text === false) {
        option.disabled = true;
        option.textContent += " (teks tidak tersedia)";
      }

      careerSelect.append(option);
    }

    careerSelect.disabled = resumes.length === 0;

  } catch (error) {
    if (!AuthStorage.getAccessToken()) {
      careerLoginRedirect();
      return;
    }

    careerMessage(`Gagal memuat CV: ${error.message}`);

  } finally {
    document.getElementById("career-loading").hidden = true;
    document.getElementById("career-app").hidden = false;
  }
}

function safeNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (typeof value === "boolean" || typeof value === "object") {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function formatPercent(value) {
  const number = safeNumber(value);

  if (number === null || number < 0 || number > 100) {
    return "—";
  }

  return `${number.toFixed(2)}%`;
}

function categoryProbabilityPercent(value) {
  const number = safeNumber(value);

  if (number === null || number < 0 || number > 1) {
    return null;
  }

  return number * 100;
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);

  if (className) {
    element.className = className;
  }

  if (text !== undefined && text !== null) {
    element.textContent = String(text);
  }

  return element;
}

function appendEmpty(container, message) {
  container.append(
    createElement("p", "career-empty", message)
  );
}

function addProgress(container, percent) {
  const track = createElement("div", "career-progress");
  const fill = createElement("div", "career-progress-fill");

  fill.style.width =
    percent === null ? "0%" : `${Math.max(0, Math.min(100, percent))}%`;

  track.append(fill);
  container.append(track);
}

function renderCareerRoles(data) {
  const container = document.getElementById("career-role-grid");

  container.replaceChildren();

  const roles = Array.isArray(data.top_recommendations)
    ? data.top_recommendations
    : Array.isArray(data.top_roles)
      ? data.top_roles
      : [];

  if (roles.length === 0) {
    appendEmpty(container, "Data Top-3 belum tersedia.");
    return;
  }

  const sortedRoles = [...roles].sort(
    (a, b) => Number(a.rank || 0) - Number(b.rank || 0)
  );

  sortedRoles.slice(0, 3).forEach((role, index) => {
    const card = createElement("article", "career-role-card");

    card.append(
      createElement(
        "span",
        "career-role-rank",
        `RANK #${role.rank || index + 1}`
      )
    );

    card.append(
      createElement(
        "h3",
        "career-role-title",
        role.role_title || "Nama pekerjaan tidak tersedia"
      )
    );

    card.append(
      createElement(
        "p",
        "career-role-category",
        role.category || role.predicted_category || "Kategori tidak tersedia"
      )
    );

    card.append(
      createElement(
        "span",
        "career-role-score-label",
        "Skill Match"
      )
    );

    const hasSkillRequirements =
      role.skill_match_available !== false &&
      role.source !== "classifier_label";

    const match = hasSkillRequirements
      ? safeNumber(role.match_percentage)
      : null;

    const validMatch =
      match !== null && match >= 0 && match <= 100
        ? match
        : null;

    card.append(
      createElement(
        "strong",
        "career-role-score",
        hasSkillRequirements
          ? formatPercent(validMatch)
          : "Tidak tersedia"
      )
    );

    addProgress(card, validMatch);
    
    if (validMatch === 0) {
        card.append(
            createElement(
                "p",
                "career-role-note",
                "Belum ada kecocokan yang terdeteksi oleh " +
                "metode skill matching saat ini. " +
                "Ini tidak berarti pengguna tidak memiliki skill."
            )
        );
    }


    if (role.salary_range) {
      card.append(
        createElement(
          "p",
          "career-role-meta",
          `Salary range: ${role.salary_range}`
        )
      );
    }

    const probability = categoryProbabilityPercent(
      role.category_probability
    );

    if (probability !== null) {
      card.append(
        createElement(
          "p",
          "career-role-note",
          `Probabilitas kategori AI: ${formatPercent(probability)}`
        )
      );
    }

    if (!hasSkillRequirements) {
      card.append(
        createElement(
          "p",
          "career-role-note",
          "Persyaratan skill pekerjaan tidak tersedia. " +
          "Nilai ini tidak boleh ditafsirkan sebagai 0% kecocokan."
        )
      );
    }

    if (Array.isArray(role.missing_skills) &&
        role.missing_skills.length > 0) {
      const gap = role.missing_skills.join(", ");

      card.append(
        createElement(
          "p",
          "career-role-note",
          `Skill gap: ${gap}`
        )
      );
    }

    container.append(card);
  });
}

function flattenDetectedSkills(raw) {
  if (Array.isArray(raw)) {
    return raw
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          return item.skill || item.name || item.label || "";
        }
        return "";
      })
      .filter(Boolean);
  }

  if (raw && typeof raw === "object") {
    return Object.values(raw)
      .flat()
      .filter((item) => typeof item === "string");
  }

  return [];
}

function renderCareerSkills(data) {
  const container = document.getElementById("career-skills");
  container.replaceChildren();

  const skills = flattenDetectedSkills(data.detected_skills);

  if (skills.length === 0) {
    appendEmpty(container, "Belum ada skill yang dapat ditampilkan.");
    return;
  }

  for (const skill of skills) {
    container.append(
      createElement("span", "career-chip", skill)
    );
  }
}

function getProbabilities(data) {
  const raw = data.profile_summary?.category_probabilities;

  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return Object.entries(raw)
      .map(([category, probability]) => ({
        category,
        percentage: categoryProbabilityPercent(probability)
      }))
      .filter((entry) => entry.percentage !== null)
      .sort((a, b) => b.percentage - a.percentage);
  }

  if (Array.isArray(data.all_predicted_categories)) {
    return data.all_predicted_categories
      .map((item) => ({
        category: item.category || item.label,
        percentage: categoryProbabilityPercent(
          item.probability ?? item.category_probability
        )
      }))
      .filter((entry) =>
        entry.category && entry.percentage !== null
      )
      .sort((a, b) => b.percentage - a.percentage);
  }

  return [];
}

function renderCareerProbabilities(data) {
  const container = document.getElementById(
    "career-probabilities"
  );

  container.replaceChildren();

  const probabilities = getProbabilities(data);

  if (probabilities.length === 0) {
    appendEmpty(
      container,
      "Probabilitas per kategori tidak tersedia pada respons ini."
    );
    return;
  }

  for (const item of probabilities.slice(0, 3)) {
    const wrapper = createElement(
      "div",
      "career-probability-item"
    );

    const header = createElement(
      "div",
      "career-probability-header"
    );

    header.append(
      createElement("span", "", item.category),
      createElement(
        "strong",
        "",
        formatPercent(item.percentage)
      )
    );

    wrapper.append(header);
    addProgress(wrapper, item.percentage);
    container.append(wrapper);
  }
}

function learningItemTitle(item, index) {
  if (typeof item === "string") {
    return `Learning Step ${index + 1}`;
  }

  return (
    item.role_title ||
    item.role ||
    item.title ||
    item.skill ||
    item.category ||
    `Learning Step ${index + 1}`
  );
}


function renderLearningItem(item, index) {
  const wrapper = createElement(
    "div",
    "career-learning-item"
  );

  wrapper.append(
    createElement(
      "strong",
      "",
      learningItemTitle(item, index)
    )
  );

  if (typeof item === "string") {
    wrapper.append(createElement("p", "", item));
    return wrapper;
  }

  if (!item || typeof item !== "object") {
    wrapper.append(
      createElement("p", "", "Learning path belum tersedia.")
    );
    return wrapper;
  }

  const description =
    item.description ||
    item.message ||
    item.recommendation ||
    item.summary;

  if (description) {
    wrapper.append(createElement("p", "", description));
  }

  const possibleSteps =
    item.steps ||
    item.resources ||
    item.missing_skills ||
    item.skills_to_learn ||
    item.recommended_skills;

  let hasSteps = false;

  if (Array.isArray(possibleSteps)) {
    const list = createElement("ul");

    possibleSteps.forEach((step) => {
      const text = typeof step === "string"
        ? step
        : step?.title ||
          step?.name ||
          step?.skill ||
          step?.description ||
          "";

      if (text) {
        list.append(createElement("li", "", text));
        hasSteps = true;
      }
    });

    if (hasSteps) {
      wrapper.append(list);
    }
  }

  if (!description && !hasSteps) {
    wrapper.append(
      createElement(
        "p",
        "",
        "Belum tersedia langkah pembelajaran spesifik " +
        "untuk rekomendasi ini."
      )
    );
  }

  return wrapper;
}

function renderCareerLearning(data) {
  const container = document.getElementById(
    "career-learning-path"
  );

  container.replaceChildren();

  const learning = data.learning_path;

  let items = [];

  if (Array.isArray(learning)) {
    items = learning;
  } else if (
    learning &&
    typeof learning === "object"
  ) {
    items = Object.entries(learning).map(([title, value]) => {
      if (Array.isArray(value)) {
        return { title, steps: value };
      }

      if (typeof value === "object" && value !== null) {
        return { title, ...value };
      }

      return { title, description: String(value) };
    });
  }

  if (items.length === 0) {
    appendEmpty(
      container,
      "Learning path belum tersedia untuk hasil ini."
    );
    return;
  }

  items.forEach((item, index) => {
    container.append(renderLearningItem(item, index));
  });
}

function renderCareerResult(data) {
  if (!data || typeof data !== "object") {
    throw new Error(
      "Respons Career AI tidak memiliki format yang valid."
    );
  }

  const dominant =
    data.dominant_category ||
    data.predicted_category ||
    "Kategori tidak tersedia";

  careerText("dominant-category", dominant);

  const selectedCV =
    careerSelect.options[careerSelect.selectedIndex]
      ?.textContent || "CV terpilih";

  careerText(
    "career-result-subtitle",
    `Rekomendasi berdasarkan ${selectedCV}.`
  );

  renderCareerRoles(data);
  renderCareerSkills(data);
  renderCareerProbabilities(data);
  renderCareerLearning(data);

  const section = document.getElementById("career-result");
  section.hidden = false;

  section.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

careerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearCareerMessage();

  const resumeId = careerSelect.value;

  if (!resumeId) {
    careerMessage("Pilih CV terlebih dahulu.");
    return;
  }

  careerButton.disabled = true;
  careerButton.textContent = "Career AI sedang menganalisis...";

  document.getElementById("career-result").hidden = true;

  try {
    const result = await ICMApi.generateCareer(resumeId);

    // Hasil baru berasal langsung dari backend.
    renderCareerResult(result);

  } catch (error) {
    careerMessage(error.message);

  } finally {
    careerButton.disabled = false;
    careerButton.textContent = "Generate Career AI";
  }
});

initializeCareer();
