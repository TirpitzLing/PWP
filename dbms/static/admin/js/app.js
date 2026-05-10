const API_BASE = '/api';

const app = {
    apiKey: null,
    currentUser: null,

    init() {
        this.apiKey = localStorage.getItem('admin_api_key');
        if (this.apiKey) {
            this.showView('dashboard-view');
            this.loadData('users');
            this.setupTabs();
        } else {
            this.showView('login-view');
        }
        this.setupForms();
        
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
    },

    showView(viewId) {
        document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
        document.getElementById(viewId).classList.add('active');
    },

    showModal(modalId) {
        document.getElementById(modalId).classList.add('active');
        document.getElementById(modalId).querySelector('form').reset();
        document.getElementById(modalId.replace('modal', 'id')).value = '';
        if (modalId === 'user-modal') {
            document.getElementById('user-modal-title').textContent = 'Add User';
            document.getElementById('user-pwd-group').style.display = 'block';
            document.getElementById('user-pwd').required = true;
        } else if (modalId === 'ingredient-modal') {
            document.getElementById('ingredient-modal-title').textContent = 'Add Ingredient';
        } else if (modalId === 'recipe-modal') {
            document.getElementById('recipe-modal-title').textContent = 'Add Recipe';
        }
    },

    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    },

    setupTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                e.target.classList.add('active');
                const targetId = e.target.getAttribute('data-target');
                document.getElementById(`${targetId}-tab`).classList.add('active');
                
                this.loadData(targetId);
            });
        });
    },

    setupForms() {
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorMsg = document.getElementById('login-error');
            
            if (username !== 'admin') {
                errorMsg.textContent = 'Only admin account is allowed.';
                return;
            }

            try {
                // First, find the admin user's email
                const usersRes = await fetch(`${API_BASE}/users/`);
                const users = await usersRes.json();
                const adminUser = users.find(u => u.username === 'admin');
                
                if (!adminUser) {
                    errorMsg.textContent = 'Admin user not found in the system.';
                    return;
                }

                // Then login
                const res = await fetch(`${API_BASE}/tokens/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: adminUser.email, pwd: password })
                });

                if (res.ok) {
                    const data = await res.json();
                    this.apiKey = data.token;
                    this.currentUser = adminUser;
                    localStorage.setItem('admin_api_key', this.apiKey);
                    errorMsg.textContent = '';
                    this.showView('dashboard-view');
                    this.setupTabs();
                    this.loadData('users');
                } else {
                    const errorData = await res.json();
                    errorMsg.textContent = errorData.description || 'Login failed';
                }
            } catch (err) {
                console.error(err);
                errorMsg.textContent = 'An error occurred during login.';
            }
        });

        document.getElementById('user-form').addEventListener('submit', (e) => this.handleSave(e, 'user'));
        document.getElementById('ingredient-form').addEventListener('submit', (e) => this.handleSave(e, 'ingredient'));
        document.getElementById('recipe-form').addEventListener('submit', (e) => this.handleSave(e, 'recipe'));
    },

    async logout() {
        if (this.apiKey) {
            try {
                await fetch(`${API_BASE}/tokens/`, {
                    method: 'DELETE',
                    headers: { 'dbms-api-key': this.apiKey }
                });
            } catch (err) {
                console.error(err);
            }
        }
        localStorage.removeItem('admin_api_key');
        this.apiKey = null;
        this.currentUser = null;
        this.showView('login-view');
    },

    async fetchAPI(url, options = {}) {
        const headers = { 'dbms-api-key': this.apiKey };
        if (options.body && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }
        options.headers = { ...headers, ...options.headers };
        const res = await fetch(API_BASE + url, options);
        if (res.status === 401) {
            this.logout();
            throw new Error('Unauthorized');
        }
        return res;
    },

    async loadData(type) {
        try {
            const res = await this.fetchAPI(`/${type}/`);
            if (res.ok) {
                const data = await res.json();
                this.renderTable(type, data);
            }
        } catch (err) {
            console.error(`Error loading ${type}:`, err);
        }
    },

    renderTable(type, data) {
        const tbody = document.getElementById(`${type}-tbody`);
        tbody.innerHTML = '';
        
        data.forEach(item => {
            const tr = document.createElement('tr');
            let content = '';
            
            if (type === 'users') {
                content = `
                    <td>${item.id}</td>
                    <td>${item.username}</td>
                    <td>${item.email}</td>
                    <td>${new Date(item.created_at).toLocaleString()}</td>
                `;
            } else if (type === 'ingredients') {
                content = `
                    <td>${item.id}</td>
                    <td>${item.name}</td>
                    <td>${item.calories || '-'}</td>
                    <td>${item.carbs || '-'}/${item.protein || '-'}/${item.fat || '-'}</td>
                `;
            } else if (type === 'recipes') {
                content = `
                    <td>${item.id}</td>
                    <td>${item.title}</td>
                    <td>${item.servings || '-'}</td>
                    <td>${item.cuisine_type || '-'}</td>
                `;
            }

            content += `
                <td class="actions-cell">
                    ${type === 'users' ? '' : `<button class="btn btn-small" onclick="app.editItem('${type}', ${item.id})">Edit</button>`}
                    <button class="btn btn-small btn-danger" onclick="app.deleteItem('${type}', ${item.id})">Delete</button>
                </td>
            `;
            tr.innerHTML = content;
            tbody.appendChild(tr);
        });
    },

    async editItem(type, id) {
        try {
            const res = await this.fetchAPI(`/${type}/${id}/`);
            if (res.ok) {
                const item = await res.json();
                this.populateForm(type, item);
                this.showModal(`${type}-modal`);
            }
        } catch (err) {
            console.error('Error fetching item:', err);
        }
    },

    populateForm(type, item) {
        document.getElementById(`${type}-id`).value = item.id;
        document.getElementById(`${type}-modal-title`).textContent = `Edit ${type.charAt(0).toUpperCase() + type.slice(1)}`;
        
        if (type === 'user') {
            document.getElementById('user-username').value = item.username;
            document.getElementById('user-email').value = item.email;
            document.getElementById('user-allergies').value = item.allergies || '';
            document.getElementById('user-pwd-group').style.display = 'none';
            document.getElementById('user-pwd').required = false;
        } else if (type === 'ingredient') {
            document.getElementById('ingredient-name').value = item.name;
            document.getElementById('ingredient-img_url').value = item.img_url || '';
            document.getElementById('ingredient-allergy').value = item.allergy || '';
            document.getElementById('ingredient-calories').value = item.calories || '';
            document.getElementById('ingredient-carbs').value = item.carbs || '';
            document.getElementById('ingredient-protein').value = item.protein || '';
            document.getElementById('ingredient-fat').value = item.fat || '';
        } else if (type === 'recipe') {
            document.getElementById('recipe-title').value = item.title;
            document.getElementById('recipe-procedure').value = item.procedure || '';
            document.getElementById('recipe-servings').value = item.servings || '';
            document.getElementById('recipe-cuisine_type').value = item.cuisine_type || '';
            document.getElementById('recipe-cooking_methods').value = item.cooking_methods || '';
            document.getElementById('recipe-img_url').value = item.img_url || '';
        }
    },

    async handleSave(e, type) {
        e.preventDefault();
        const id = document.getElementById(`${type}-id`).value;
        const isEdit = !!id;
        const url = isEdit ? `/${type}s/${id}/` : `/${type}s/`;
        const method = isEdit ? 'PUT' : 'POST';
        
        let payload = {};
        if (type === 'user') {
            payload = {
                username: document.getElementById('user-username').value,
                email: document.getElementById('user-email').value,
                allergies: document.getElementById('user-allergies').value || null
            };
            if (!isEdit) {
                payload.pwd = document.getElementById('user-pwd').value;
            }
        } else if (type === 'ingredient') {
            payload = {
                name: document.getElementById('ingredient-name').value,
                img_url: document.getElementById('ingredient-img_url').value || null,
                allergy: document.getElementById('ingredient-allergy').value || null,
                calories: parseFloat(document.getElementById('ingredient-calories').value) || null,
                carbs: parseFloat(document.getElementById('ingredient-carbs').value) || null,
                protein: parseFloat(document.getElementById('ingredient-protein').value) || null,
                fat: parseFloat(document.getElementById('ingredient-fat').value) || null
            };
        } else if (type === 'recipe') {
            payload = {
                title: document.getElementById('recipe-title').value,
                procedure: document.getElementById('recipe-procedure').value || null,
                servings: parseInt(document.getElementById('recipe-servings').value) || null,
                cuisine_type: document.getElementById('recipe-cuisine_type').value || null,
                cooking_methods: document.getElementById('recipe-cooking_methods').value || null,
                img_url: document.getElementById('recipe-img_url').value || null
            };
        }

        try {
            const res = await this.fetchAPI(url, {
                method,
                body: JSON.stringify(payload)
            });

            if (res.ok || res.status === 201 || res.status === 204) {
                this.hideModal(`${type}-modal`);
                this.loadData(`${type}s`);
            } else {
                const data = await res.json();
                alert(`Error: ${data.description || 'Failed to save'}`);
            }
        } catch (err) {
            console.error('Error saving:', err);
            alert('An error occurred while saving.');
        }
    },

    async deleteItem(type, id) {
        if (!confirm(`Are you sure you want to delete this ${type.slice(0, -1)}?`)) return;
        
        try {
            const res = await this.fetchAPI(`/${type}/${id}/`, { method: 'DELETE' });
            if (res.ok || res.status === 204) {
                this.loadData(type);
            } else {
                const data = await res.json();
                alert(`Error: ${data.description || 'Failed to delete'}`);
            }
        } catch (err) {
            console.error('Error deleting:', err);
            alert('An error occurred while deleting.');
        }
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());
