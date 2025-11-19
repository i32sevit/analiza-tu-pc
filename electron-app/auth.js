// auth.js
const API_BASE = "http://localhost:8000";

class AuthService {
    constructor() {
        this.token = localStorage.getItem("auth_token");
        this.user = JSON.parse(localStorage.getItem("user") || "null");

        this.initEventListeners();
    }

    initEventListeners() {
        document.querySelectorAll(".auth-tab").forEach(tab => {
            tab.addEventListener("click", (e) => this.switchTab(e.target.dataset.tab));
        });

        document.getElementById("showRegister").addEventListener("click", () => this.switchTab("register"));
        document.getElementById("showLogin").addEventListener("click", () => this.switchTab("login"));

        document.getElementById("loginForm").addEventListener("submit", (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        document.getElementById("registerForm").addEventListener("submit", (e) => {
            e.preventDefault();
            this.handleRegister();
        });

        document.getElementById("guestButton").addEventListener("click", () => this.continueAsGuest());

        this.initRealTimeValidation();
    }

    switchTab(tabName) {
        document.querySelectorAll(".auth-tab").forEach(tab => {
            tab.classList.toggle("active", tab.dataset.tab === tabName);
        });

        document.querySelectorAll(".auth-form").forEach(form => {
            form.classList.toggle("active", form.id === `${tabName}Form`);
        });

        this.clearErrors();
    }

    clearErrors() {
        document.querySelectorAll(".error-message").forEach(e => e.classList.remove("show"));
        document.querySelectorAll("input").forEach(inp => inp.classList.remove("error"));
    }

    showError(inputId, message) {
        const input = document.getElementById(inputId);
        const error = document.getElementById(`${inputId}Error`);

        input.classList.add("error");
        error.textContent = message;
        error.classList.add("show");
    }

    clearFieldError(fieldId) {
        document.getElementById(fieldId).classList.remove("error");
        document.getElementById(`${fieldId}Error`).classList.remove("show");
    }

    initRealTimeValidation() {
        const pass = document.getElementById("registerPassword");
        const confirm = document.getElementById("registerConfirmPassword");

        const validate = () => {
            if (pass.value && confirm.value && pass.value !== confirm.value) {
                this.showError("registerConfirmPassword", "Las contraseñas no coinciden");
            } else {
                this.clearFieldError("registerConfirmPassword");
            }
        };

        pass.addEventListener("input", validate);
        confirm.addEventListener("input", validate);
    }

    async handleLogin() {
        const username = document.getElementById("loginUsername").value.trim();
        const password = document.getElementById("loginPassword").value;

        if (!username || !password) {
            this.showError("loginUsername", "Ingresa usuario y contraseña");
            this.showError("loginPassword", "");
            return;
        }

        const btn = document.getElementById("loginButton");
        const txt = document.getElementById("loginText");
        const loading = document.getElementById("loginLoading");

        txt.style.display = "none";
        loading.style.display = "inline-block";
        btn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Credenciales incorrectas");

            this.token = data.access_token;
            this.user = data.user;

            localStorage.setItem("auth_token", this.token);
            localStorage.setItem("user", JSON.stringify(this.user));

            this.redirectToApp();

        } catch (err) {
            this.showError("loginPassword", err.message);
        } finally {
            txt.style.display = "inline-block";
            loading.style.display = "none";
            btn.disabled = false;
        }
    }

    async handleRegister() {
        const username = document.getElementById("registerUsername").value.trim();
        const email = document.getElementById("registerEmail").value.trim();
        const password = document.getElementById("registerPassword").value;
        const confirmPassword = document.getElementById("registerConfirmPassword").value;

        if (!username || !email || !password || !confirmPassword) {
            this.showError("registerUsername", "Completa todos los campos");
            return;
        }

        if (password.length < 6) {
            this.showError("registerPassword", "La contraseña debe tener al menos 6 caracteres");
            return;
        }

        if (password !== confirmPassword) {
            this.showError("registerConfirmPassword", "Las contraseñas no coinciden");
            return;
        }

        const btn = document.getElementById("registerButton");
        const txt = document.getElementById("registerText");
        const loading = document.getElementById("registerLoading");

        txt.style.display = "none";
        loading.style.display = "inline-block";
        btn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password })
            });

            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Error en el registro");

            document.getElementById("successMessage").classList.add("show");

            setTimeout(() => {
                this.handleAutoLogin(username, password);
            }, 2000);

        } catch (err) {
            if (err.message.includes("email")) this.showError("registerEmail", err.message);
            else if (err.message.includes("username")) this.showError("registerUsername", err.message);
            else this.showError("registerUsername", "Error en el registro");
        } finally {
            txt.style.display = "inline-block";
            loading.style.display = "none";
            btn.disabled = false;
        }
    }

    async handleAutoLogin(username, password) {
        try {
            const res = await fetch(`${API_BASE}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await res.json();
            if (!res.ok) throw new Error();

            this.token = data.access_token;
            this.user = data.user;

            localStorage.setItem("auth_token", this.token);
            localStorage.setItem("user", JSON.stringify(this.user));

            this.redirectToApp();

        } catch {
            this.switchTab("login");
        }
    }

    continueAsGuest() {
        localStorage.setItem("is_guest", "true");
        this.redirectToApp();
    }

    redirectToApp() {
        window.location.href = "index.html";
    }

    isAuthenticated() {
        return !!this.token;
    }

    isGuest() {
        return localStorage.getItem("is_guest") === "true";
    }

    logout() {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("user");
        localStorage.removeItem("is_guest");
        window.location.href = "auth.html";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.authService = new AuthService();
});
