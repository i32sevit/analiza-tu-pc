// auth.js
const API_BASE = 'http://localhost:8000';

class AuthService {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
        this.initEventListeners();
    }

    initEventListeners() {
        // Tabs de login/registro
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Enlaces para cambiar entre formularios
        document.getElementById('showRegister').addEventListener('click', () => {
            this.switchTab('register');
        });

        document.getElementById('showLogin').addEventListener('click', () => {
            this.switchTab('login');
        });

        // Formularios
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        document.getElementById('registerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });

        // Botón de invitado
        document.getElementById('guestButton').addEventListener('click', () => {
            this.continueAsGuest();
        });

        // Validación en tiempo real
        this.initRealTimeValidation();
    }

    switchTab(tabName) {
        // Actualizar tabs
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Mostrar formulario correspondiente
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${tabName}Form`);
        });

        // Limpiar errores
        this.clearErrors();
    }

    clearErrors() {
        document.querySelectorAll('.error-message').forEach(error => {
            error.classList.remove('show');
        });
        document.querySelectorAll('input').forEach(input => {
            input.classList.remove('error');
        });
    }

    showError(inputId, message) {
        const input = document.getElementById(inputId);
        const errorElement = document.getElementById(`${inputId}Error`);
        
        input.classList.add('error');
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }

    initRealTimeValidation() {
        // Validación de confirmación de contraseña
        const confirmPassword = document.getElementById('registerConfirmPassword');
        const password = document.getElementById('registerPassword');

        confirmPassword.addEventListener('input', () => {
            if (confirmPassword.value && password.value !== confirmPassword.value) {
                this.showError('registerConfirmPassword', 'Las contraseñas no coinciden');
            } else {
                this.clearFieldError('registerConfirmPassword');
            }
        });

        password.addEventListener('input', () => {
            if (confirmPassword.value && password.value !== confirmPassword.value) {
                this.showError('registerConfirmPassword', 'Las contraseñas no coinciden');
            } else {
                this.clearFieldError('registerConfirmPassword');
            }
        });
    }

    clearFieldError(fieldId) {
        const input = document.getElementById(fieldId);
        const errorElement = document.getElementById(`${fieldId}Error`);
        
        input.classList.remove('error');
        errorElement.classList.remove('show');
    }

    async handleLogin() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const loginButton = document.getElementById('loginButton');
        const loginText = document.getElementById('loginText');
        const loginLoading = document.getElementById('loginLoading');

        // Validación básica
        if (!username || !password) {
            this.showError('loginUsername', 'Completa todos los campos');
            return;
        }

        // Mostrar loading
        loginText.style.display = 'none';
        loginLoading.style.display = 'inline-block';
        loginButton.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Error en el inicio de sesión');
            }

            // Guardar token y usuario
            this.token = data.access_token;
            this.user = data.user;
            
            localStorage.setItem('auth_token', this.token);
            localStorage.setItem('user', JSON.stringify(this.user));

            // Redirigir a la aplicación principal
            this.redirectToApp();

        } catch (error) {
            this.showError('loginPassword', error.message);
        } finally {
            // Ocultar loading
            loginText.style.display = 'inline-block';
            loginLoading.style.display = 'none';
            loginButton.disabled = false;
        }
    }

    async handleRegister() {
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('registerConfirmPassword').value;
        const registerButton = document.getElementById('registerButton');
        const registerText = document.getElementById('registerText');
        const registerLoading = document.getElementById('registerLoading');

        // Validaciones
        if (!username || !email || !password || !confirmPassword) {
            this.showError('registerUsername', 'Completa todos los campos');
            return;
        }

        if (password !== confirmPassword) {
            this.showError('registerConfirmPassword', 'Las contraseñas no coinciden');
            return;
        }

        if (password.length < 6) {
            this.showError('registerPassword', 'La contraseña debe tener al menos 6 caracteres');
            return;
        }

        // Mostrar loading
        registerText.style.display = 'none';
        registerLoading.style.display = 'inline-block';
        registerButton.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, email, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Error en el registro');
            }

            // Mostrar mensaje de éxito
            document.getElementById('successMessage').classList.add('show');

            // Auto-login después del registro
            setTimeout(() => {
                this.handleAutoLogin(username, password);
            }, 2000);

        } catch (error) {
            if (error.message.includes('email')) {
                this.showError('registerEmail', error.message);
            } else if (error.message.includes('username')) {
                this.showError('registerUsername', error.message);
            } else {
                this.showError('registerUsername', error.message);
            }
        } finally {
            // Ocultar loading
            registerText.style.display = 'inline-block';
            registerLoading.style.display = 'none';
            registerButton.disabled = false;
        }
    }

    async handleAutoLogin(username, password) {
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (response.ok) {
                this.token = data.access_token;
                this.user = data.user;
                
                localStorage.setItem('auth_token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));

                this.redirectToApp();
            }
        } catch (error) {
            // Si falla el auto-login, mostrar formulario de login
            this.switchTab('login');
            document.getElementById('loginUsername').value = username;
            document.getElementById('loginPassword').value = password;
        }
    }

    continueAsGuest() {
        // Guardar estado de invitado
        localStorage.setItem('is_guest', 'true');
        this.redirectToApp();
    }

    redirectToApp() {
        // Redirigir a la aplicación principal
        window.location.href = 'index.html';
    }

    isAuthenticated() {
        return !!this.token;
    }

    isGuest() {
        return localStorage.getItem('is_guest') === 'true';
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        localStorage.removeItem('is_guest');
        
        // Redirigir a la página de auth
        window.location.href = 'auth.html';
    }

    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json',
        };
    }

    async makeAuthenticatedRequest(url, options = {}) {
        if (!this.isAuthenticated()) {
            throw new Error('Usuario no autenticado');
        }

        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                ...this.getAuthHeaders(),
            },
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('Sesión expirada');
        }

        return response;
    }
}

// Inicializar el servicio de autenticación cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    window.authService = new AuthService();

    // Si ya está autenticado, redirigir a la app
    if (window.authService.isAuthenticated() || window.authService.isGuest()) {
        window.authService.redirectToApp();
    }
});