// Frontend configuration for Gluvia API
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    ENDPOINTS: {
        // Authentication endpoints
        REGISTER: '/auth/register',
        LOGIN: '/auth/login',
        PROFILE: '/auth/profile',

        // Prescription endpoints
        TEMPLATE: '/prescriptions/template',
        DAILY_QUESTIONNAIRE: '/prescriptions/daily-questionnaire',
        STATUS: '/prescriptions/status',
        HISTORY: '/prescriptions/doses/history',
        CREATE_PRESCRIPTION: '/prescriptions/',
        ACTIVE_PRESCRIPTION: '/prescriptions/active',
        UPLOAD: '/prescriptions/upload'
    }
};

// Utility function to make API calls
async function apiCall(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };

    // Add authorization header if token exists
    const token = localStorage.getItem('access_token');
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, finalOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Authentication helper functions
const auth = {
    isLoggedIn: () => !!localStorage.getItem('access_token'),

    login: async (username, password) => {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.LOGIN}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Login failed');
        }

        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        return data;
    },

    register: async (username, email, password) => {
        return await apiCall(API_CONFIG.ENDPOINTS.REGISTER, {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
    },

    logout: () => {
        localStorage.removeItem('access_token');
        window.location.href = 'index.html';
    },

    getProfile: async () => {
        return await apiCall(API_CONFIG.ENDPOINTS.PROFILE);
    }
};

// Check if user is authenticated and redirect if needed
function requireAuth() {
    if (!auth.isLoggedIn()) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// Display error messages to user
function showError(message, containerId = 'error-container') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="error-message" style="color: red; background: #ffe6e6; padding: 10px; border-radius: 5px; margin: 10px 0;">
                ${message}
            </div>
        `;
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    } else {
        alert(message);
    }
}

// Display success messages to user
function showSuccess(message, containerId = 'success-container') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="success-message" style="color: green; background: #e6ffe6; padding: 10px; border-radius: 5px; margin: 10px 0;">
                ${message}
            </div>
        `;
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    } else {
        alert(message);
    }
}

// Utility function to upload a file
async function uploadFile(file) {
    const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.UPLOAD}`;
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('access_token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    const response = await fetch(url, {
        method: 'POST',
        body: formData,
        headers
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'File upload failed');
    }
    return response.json();
}
