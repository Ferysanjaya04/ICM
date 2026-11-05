
"use strict";

function setText(id, value) {
  const element = document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

function redirectToLogin() {
  AuthStorage.clear();
  window.location.replace("./login.html");
}

function renderUserProfile(user) {
  const username = user.username || "ICM User";
  const email = user.email || "Email tidak tersedia";

  const initial = username.charAt(0).toUpperCase();

  setText("welcome-title", `Welcome back, ${username}!`);

  setText("sidebar-username", username);
  setText("sidebar-email", email);
  setText("sidebar-avatar", initial);

  setText("topbar-avatar", initial);

  setText("profile-username", username);
  setText("profile-avatar", initial);
  setText("profile-field-username", username);
  setText("profile-field-email", email);
}

async function initializeDashboard() {
  const loading = document.getElementById("app-loading");
  const app = document.getElementById("dashboard-app");

  if (!AuthStorage.getAccessToken()) {
    redirectToLogin();
    return;
  }

  try {
    let user;

    try {
      user = await ICMApi.getMe();
    } catch (error) {
      // Coba refresh sekali jika access token gagal.
      // Endpoint /me/ akan diuji lagi setelah refresh.
      if (!AuthStorage.getRefreshToken()) {
        throw error;
      }

      await ICMApi.refreshAccessToken();
      user = await ICMApi.getMe();
    }

    renderUserProfile(user);

    loading.hidden = true;
    app.hidden = false;

  } catch (error) {
    console.error(
      "Gagal memverifikasi sesi:",
      error.message
    );

    redirectToLogin();
  }
}

function setupLogout() {
  const logoutButton =
    document.getElementById("logout-button");

  logoutButton.addEventListener("click", () => {
    redirectToLogin();
  });
}

function setupMobileSidebar() {
  const sidebar = document.getElementById("sidebar");
  const menuButton = document.getElementById("menu-button");
  const overlay = document.getElementById("sidebar-overlay");

  function closeSidebar() {
    sidebar.classList.remove("is-open");
    overlay.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
  }

  menuButton.addEventListener("click", () => {
    const isOpen = sidebar.classList.toggle("is-open");

    overlay.hidden = !isOpen;

    menuButton.setAttribute(
      "aria-expanded",
      String(isOpen)
    );
  });

  overlay.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSidebar();
    }
  });
}

function setupComingSoonButtons() {
  const notice = document.getElementById("dashboard-notice");

  let noticeTimeout;

  document.querySelectorAll("[data-coming-soon]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        const feature = button.dataset.comingSoon;

        notice.textContent =
          `${feature} akan kita hubungkan ` +
          "pada tahap frontend berikutnya.";

        notice.hidden = false;

        window.clearTimeout(noticeTimeout);

        noticeTimeout = window.setTimeout(() => {
          notice.hidden = true;
        }, 3500);
      });
    });
}

setupLogout();
setupMobileSidebar();
setupComingSoonButtons();
initializeDashboard();