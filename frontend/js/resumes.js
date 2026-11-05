
"use strict";

const MAX_CV_SIZE = 10 * 1024 * 1024;
const ALLOWED_CV_EXTENSIONS = [".pdf", ".docx"];

const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("cv-file");
const uploadButton = document.getElementById("upload-button");
const refreshButton = document.getElementById("refresh-button");

function showResumeMessage(id, message, success = false) {
  const element = document.getElementById(id);

  element.textContent = message;
  element.hidden = false;
  element.classList.toggle("success", success);
}

function clearResumeMessage(id) {
  const element = document.getElementById(id);
  element.hidden = true;
  element.textContent = "";
  element.classList.remove("success");
}

function goToLogin() {
  AuthStorage.clear();
  window.location.replace("./login.html");
}

async function verifySession() {
  if (!AuthStorage.getAccessToken()) {
    goToLogin();
    return false;
  }

  try {
    let user;

    try {
      user = await ICMApi.getMe();
    } catch {
      await ICMApi.refreshAccessToken();
      user = await ICMApi.getMe();
    }

    document.getElementById("current-user").textContent =
      user.username || "ICM User";

    document.getElementById("page-loading").hidden = true;
    document.getElementById("resumes-app").hidden = false;

    return true;
  } catch {
    goToLogin();
    return false;
  }
}

async function withTokenRetry(operation) {
  try {
    return await operation();
  } catch (error) {
    // Refresh hanya untuk error HTTP 401,
    // bukan untuk semua kesalahan request.
    const isUnauthorized =
      error.httpStatus === 401 ||
      /HTTP 401/.test(error.message);

    if (!isUnauthorized) {
      throw error;
    }

    await ICMApi.refreshAccessToken();
    return operation();
  }
}

function formatUploadDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Tanggal tidak tersedia";
  }

  return date.toLocaleString("id-ID", {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function createResumeItem(resume) {
  const item = document.createElement("article");
  item.className = "resume-item";

  const icon = document.createElement("div");
  icon.className = "resume-file-icon";

  const filename = resume.original_filename || "Untitled CV";
  const extension = filename.toLowerCase().endsWith(".docx")
    ? "DOCX"
    : "PDF";

  icon.textContent = extension;

  const info = document.createElement("div");
  info.className = "resume-file-info";

  const title = document.createElement("strong");
  title.textContent = filename;

  const detail = document.createElement("span");

  const extractionStatus = resume.has_extracted_text
    ? "Teks berhasil diekstraksi"
    : "Teks belum tersedia";

  detail.textContent =
    `${formatUploadDate(resume.uploaded_at)} · ${extractionStatus}`;

  info.append(title, detail);
  item.append(icon, info);

  return item;
}

async function loadResumes() {
  const listElement = document.getElementById("resume-list");

  refreshButton.disabled = true;
  clearResumeMessage("list-message");

  listElement.replaceChildren();

  const loading = document.createElement("p");
  loading.className = "empty-state";
  loading.textContent = "Memuat daftar CV...";
  listElement.append(loading);

  try {
    const result = await withTokenRetry(
      () => ICMApi.listResumes()
    );

    const resumes = Array.isArray(result.resumes)
      ? result.resumes
      : [];

    document.getElementById("resume-count").textContent =
      `${resumes.length} CV`;

    listElement.replaceChildren();

    if (resumes.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent =
        "Belum ada CV. Silakan upload CV pertamamu.";

      listElement.append(empty);
      return;
    }

    resumes.forEach((resume) => {
      listElement.append(createResumeItem(resume));
    });

  } catch (error) {
    listElement.replaceChildren();

    showResumeMessage(
      "list-message",
      error.message
    );

    document.getElementById("resume-count").textContent = "— CV";

  } finally {
    refreshButton.disabled = false;
  }
}

function validateCVFile(file) {
  if (!file) {
    throw new Error("Silakan pilih file CV.");
  }

  const filename = file.name.toLowerCase();

  const validExtension = ALLOWED_CV_EXTENSIONS.some(
    (extension) => filename.endsWith(extension)
  );

  if (!validExtension) {
    throw new Error(
      "Format file harus PDF atau DOCX."
    );
  }

  if (file.size === 0) {
    throw new Error("File CV tidak boleh kosong.");
  }

  if (file.size > MAX_CV_SIZE) {
    throw new Error("Ukuran file maksimal 10 MB.");
  }
}

fileInput.addEventListener("change", () => {
  clearResumeMessage("upload-message");

  const file = fileInput.files[0];
  const selected = document.getElementById("selected-file");

  if (!file) {
    selected.hidden = true;
    selected.textContent = "";
    return;
  }

  selected.hidden = false;

  selected.textContent =
    `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResumeMessage("upload-message");

  const file = fileInput.files[0];

  try {
    validateCVFile(file);
  } catch (error) {
    showResumeMessage("upload-message", error.message);
    return;
  }

  uploadButton.disabled = true;
  uploadButton.textContent = "Mengunggah & mengekstraksi CV...";

  try {
    const result = await withTokenRetry(
      () => ICMApi.uploadResume(file)
    );

    showResumeMessage(
      "upload-message",
      `CV "${result.original_filename || file.name}" berhasil diunggah.`,
      true
    );

    uploadForm.reset();

    document.getElementById("selected-file").hidden = true;
    document.getElementById("selected-file").textContent = "";

    await loadResumes();

  } catch (error) {
    showResumeMessage(
      "upload-message",
      error.message
    );

  } finally {
    uploadButton.disabled = false;
    uploadButton.textContent = "Upload CV";
  }
});

refreshButton.addEventListener("click", loadResumes);

async function initializeResumesPage() {
  const authenticated = await verifySession();

  if (authenticated) {
    await loadResumes();
  }
}

initializeResumesPage();
