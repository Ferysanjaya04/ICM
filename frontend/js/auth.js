
"use strict";

function showAuthMessage(message, type = "error") {
  const element = document.getElementById("login-message")
    || document.getElementById("register-message");

  if (!element) return;

  element.textContent = message;
  element.hidden = false;

  element.style.background =
    type === "success" ? "#eaf8ee" : "#fff0f0";

  element.style.color =
    type === "success" ? "#167342" : "#bd3434";
}

function hideAuthMessage() {
  const element = document.getElementById("login-message")
    || document.getElementById("register-message");

  if (element) {
    element.hidden = true;
    element.textContent = "";
  }
}

function setSubmitLoading(button, loading, defaultText) {
  if (!button) return;

  button.disabled = loading;
  button.textContent = loading ? "Memproses..." : defaultText;
}

const loginForm = document.getElementById("login-form");

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAuthMessage();

    const username =
      document.getElementById("username").value.trim();

    const password =
      document.getElementById("password").value;

    const button =
      document.getElementById("login-button");

    if (!username || !password) {
      showAuthMessage("Username dan password wajib diisi.");
      return;
    }

    setSubmitLoading(button, true, "Sign In");

    try {
      const result = await ICMApi.login(username, password);

      if (!result.access || !result.refresh) {
        throw new Error(
          "Respons login tidak memiliki token JWT yang lengkap."
        );
      }

      AuthStorage.saveTokens(
        result.access,
        result.refresh
      );

      // Verifikasi bahwa token benar-benar dapat
      // mengakses endpoint pengguna Django.
      await ICMApi.getMe();

      window.location.replace("./dashboard.html");

    } catch (error) {
      AuthStorage.clear();
      showAuthMessage(error.message);

    } finally {
      setSubmitLoading(button, false, "Sign In");
    }
  });
}

const registerForm = document.getElementById("register-form");

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAuthMessage();

    const username =
      document.getElementById("username").value.trim();

    const email =
      document.getElementById("email").value.trim();

    const password =
      document.getElementById("password").value;

    const confirmPassword =
      document.getElementById("confirm-password").value;

    const button =
      document.getElementById("register-button");

    if (!username || !email || !password) {
      showAuthMessage("Semua field wajib diisi.");
      return;
    }

    if (password !== confirmPassword) {
      showAuthMessage("Konfirmasi password tidak cocok.");
      return;
    }

    if (password.length < 8) {
      showAuthMessage("Gunakan password minimal 8 karakter.");
      return;
    }

    setSubmitLoading(button, true, "Create Account");

    try {
      await ICMApi.register(username, email, password);

      showAuthMessage(
        "Registrasi berhasil. Mengalihkan ke halaman login...",
        "success"
      );

      registerForm.reset();

      window.setTimeout(() => {
        window.location.replace("./login.html");
      }, 900);

    } catch (error) {
      showAuthMessage(error.message);

    } finally {
      setSubmitLoading(button, false, "Create Account");
    }
  });
}
