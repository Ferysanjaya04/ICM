
"use strict";

const API_BASE_URL = "http://127.0.0.1:8000/api";

const AuthStorage = {
  getAccessToken() {
    return sessionStorage.getItem("icm_access");
  },

  getRefreshToken() {
    return sessionStorage.getItem("icm_refresh");
  },

  saveTokens(access, refresh) {
    sessionStorage.setItem("icm_access", access);
    sessionStorage.setItem("icm_refresh", refresh);
  },

  clear() {
    sessionStorage.removeItem("icm_access");
    sessionStorage.removeItem("icm_refresh");
  }
};

function extractErrorMessage(body, fallback) {
  if (typeof body?.error === "string") {
    return body.error;
  }

  if (typeof body?.error?.message === "string") {
    return body.error.message;
  }

  if (typeof body?.detail === "string") {
    return body.detail;
  }

  if (typeof body?.message === "string") {
    return body.message;
  }

  return fallback;
}

async function apiRequest(
  endpoint,
  { method = "GET", body = null, authenticated = false } = {}
) {
  const headers = {
    Accept: "application/json"
  };

  if (body !== null) {
    headers["Content-Type"] = "application/json";
  }

  if (authenticated) {
    const token = AuthStorage.getAccessToken();

    if (!token) {
      throw new Error("Sesi tidak tersedia. Silakan login kembali.");
    }

    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      body: body !== null ? JSON.stringify(body) : undefined
    });
  } catch {
    throw new Error(
      "Tidak dapat menghubungi server Django. " +
      "Pastikan backend sedang berjalan."
    );
  }

  const result = await response.json().catch(() => ({}));

  if (!response.ok || result.status === "error") {
    throw new Error(
      extractErrorMessage(
        result,
        `Permintaan gagal (HTTP ${response.status}).`
      )
    );
  }

  // API ICM menggunakan format:
  // { status: "success", data: {...} }
  return result.data ?? result;
}

const ICMApi = {
  login(username, password) {
    return apiRequest("/auth/login/", {
      method: "POST",
      body: { username, password }
    });
  },

  register(username, email, password) {
    return apiRequest("/auth/register/", {
      method: "POST",
      body: { username, email, password }
    });
  },

  getMe() {
    return apiRequest("/auth/me/", {
      authenticated: true
    });
  },

  async refreshAccessToken() {
    const refresh = AuthStorage.getRefreshToken();

    if (!refresh) {
      throw new Error("Sesi sudah berakhir. Silakan login kembali.");
    }

    const result = await apiRequest("/auth/refresh/", {
      method: "POST",
      body: { refresh }
    });

    if (!result.access) {
      throw new Error("Server tidak mengembalikan access token.");
    }

    sessionStorage.setItem("icm_access", result.access);

    if (result.refresh) {
      sessionStorage.setItem("icm_refresh", result.refresh);
    }

    return result.access;
  }
};


ICMApi.listResumes = function () {
  return apiRequest("/resume/list/", {
    authenticated: true
  });
};

ICMApi.uploadResume = async function (file) {
  const token = AuthStorage.getAccessToken();

  if (!token) {
    throw new Error("Silakan login terlebih dahulu.");
  }

  const formData = new FormData();

  // Harus sesuai dengan request.FILES.get("cv_file")
  formData.append("cv_file", file);

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/resume/upload/`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`
        },
        body: formData
      }
    );
  } catch {
    throw new Error(
      "Tidak dapat menghubungi backend Django."
    );
  }

  const result = await response.json().catch(() => ({}));

  if (!response.ok || result.status === "error") {
    const error = new Error(
      extractErrorMessage(
        result,
        `Upload gagal (HTTP ${response.status}).`
      )
    );

    error.httpStatus = response.status;
    throw error;
  }

  return result.data ?? result;
};


ICMApi.createJobMatch = async function (resumeId, jobText) {
  const endpoint = "/analysis/match/";

  async function send() {
    const token = AuthStorage.getAccessToken();

    if (!token) {
      throw new Error("Sesi habis. Silakan login kembali.");
    }

    let response;

    try {
      response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          resume_id: resumeId,
          job_text: jobText
        })
      });
    } catch {
      throw new Error(
        "Tidak dapat menghubungi Django. " +
        "Pastikan backend sedang berjalan."
      );
    }

    if (response.status === 401) {
      return { needsRefresh: true };
    }

    const result = await response.json().catch(() => ({}));

    if (!response.ok || result.status === "error") {
      const message = extractErrorMessage(
        result,
        `Analisis gagal (HTTP ${response.status}).`
      );

      const error = new Error(message);
      error.httpStatus = response.status;
      error.code = result.error?.code || result.code || null;
      throw error;
    }

    return {
      needsRefresh: false,
      data: result.data ?? result
    };
  }

  let result = await send();

  if (result.needsRefresh) {
    await ICMApi.refreshAccessToken();
    result = await send();
  }

  if (result.needsRefresh) {
    throw new Error(
      "Sesi tidak valid. Silakan login kembali."
    );
  }

  return result.data;
};


ICMApi.generateCareer = async function (resumeId) {
  async function send() {
    const token = AuthStorage.getAccessToken();

    if (!token) {
      throw new Error("Silakan login terlebih dahulu.");
    }

    let response;

    try {
      response = await fetch(
        `${API_BASE_URL}/recommendations/generate/`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            resume_id: resumeId
          })
        }
      );
    } catch {
      throw new Error("Tidak dapat menghubungi server Django.");
    }

    if (response.status === 401) {
      return { unauthorized: true };
    }

    const result = await response.json().catch(() => ({}));

    if (!response.ok || result.status === "error") {
      const error = new Error(
        extractErrorMessage(
          result,
          `Gagal menghasilkan rekomendasi (HTTP ${response.status}).`
        )
      );

      error.httpStatus = response.status;
      throw error;
    }

    return {
      unauthorized: false,
      data: result.data ?? result
    };
  }

  let result = await send();

  if (result.unauthorized) {
    await ICMApi.refreshAccessToken();
    result = await send();
  }

  if (result.unauthorized) {
    throw new Error("Sesi sudah berakhir. Silakan login kembali.");
  }

  return result.data;
};

ICMApi.listCareerRecommendations = function () {
  return apiRequest("/recommendations/", {
    authenticated: true
  });
};

ICMApi.getCareerRecommendation = function (id) {
  return apiRequest(
    `/recommendations/${encodeURIComponent(id)}/`,
    { authenticated: true }
  );
};


ICMApi.listJobMatches = function () {
  return apiRequest("/analysis/matches/", {
    authenticated: true
  });
};
