/**
 * ICM REST API Client (JavaScript Fetch + JWT)
 * Jembatan komunikasi Frontend ke Backend REST API
 */
(function() {
    const API_BASE_URL = window.location.origin;

    const API = {
        getToken() {
            return localStorage.getItem('icm_access_token');
        },
        setTokens(access, refresh) {
            if (access) localStorage.setItem('icm_access_token', access);
            if (refresh) localStorage.setItem('icm_refresh_token', refresh);
        },
        removeTokens() {
            localStorage.removeItem('icm_access_token');
            localStorage.removeItem('icm_refresh_token');
        },

        getHeaders(isJson = true) {
            const headers = {};
            if (isJson) {
                headers['Content-Type'] = 'application/json';
            }
            const token = this.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            return headers;
        },

        // POST /api/auth/login/
        async login(username, password) {
            const res = await fetch(`${API_BASE_URL}/api/auth/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            const data = await res.json();
            if (res.ok && data.data && data.data.access) {
                this.setTokens(data.data.access, data.data.refresh);
            }
            return { ok: res.ok, status: res.status, data };
        },

        // POST /api/auth/register/
        async register(username, email, password) {
            const res = await fetch(`${API_BASE_URL}/api/auth/register/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password }),
            });
            const data = await res.json();
            return { ok: res.ok, status: res.status, data };
        },

        // GET /api/auth/me/
        async getMe() {
            const res = await fetch(`${API_BASE_URL}/api/auth/me/`, {
                method: 'GET',
                headers: this.getHeaders(true),
            });
            const data = await res.json();
            return { ok: res.ok, status: res.status, data };
        },

        // POST /api/resume/upload/ (multipart/form-data)
        async uploadResume(file) {
            const formData = new FormData();
            formData.append('cv_file', file);

            const headers = {};
            const token = this.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const res = await fetch(`${API_BASE_URL}/api/resume/upload/`, {
                method: 'POST',
                headers: headers,
                body: formData,
            });
            const data = await res.json();
            return { ok: res.ok, status: res.status, data };
        },
    };

    window.ICM_API = API;
})();
