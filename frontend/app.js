const API = '';

const state = {
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    currentUser: null,
    currentChatId: null,
    chats: [],
    isSending: false,
};

function saveTokens(access, refresh) {
    state.accessToken = access;
    state.refreshToken = refresh;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
    state.accessToken = null;
    state.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
}

async function apiRequest(method, path, body = null, retry = true) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.accessToken) headers['Authorization'] = `Bearer ${state.accessToken}`;
    
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    
    let res = await fetch(API + path, opts);
    
    if (res.status === 401 && retry && state.refreshToken) {
        const refreshed = await tryRefresh();
        if (refreshed) {
            headers['Authorization'] = `Bearer ${state.accessToken}`;
            res = await fetch(API + path, { ...opts, headers });
        } else {
            clearTokens();
            showAuth();
            return null;
        }
    }
    
    return res;
}

async function tryRefresh() {
    if (!state.refreshToken) return false;
    try {
        const res = await fetch(API + '/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: state.refreshToken }),
        });
        if (res.ok) {
            const data = await res.json();
            saveTokens(data.access_token, data.refresh_token);
            return true;
        }
    } catch (e) {}
    return false;
}

function showAuth() {
    document.getElementById('auth-view').classList.remove('hidden');
    document.getElementById('chat-view').classList.add('hidden');
}

function showChat() {
    document.getElementById('auth-view').classList.add('hidden');
    document.getElementById('chat-view').classList.remove('hidden');
}

function showError(elementId, msg) {
    const el = document.getElementById(elementId);
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}

async function handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    if (!username || !password) return showError('login-error', 'Please fill in all fields');
    
    const btn = document.getElementById('login-btn');
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    
    try {
        const res = await fetch(API + '/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        
        if (res.ok) {
            const data = await res.json();
            saveTokens(data.access_token, data.refresh_token);
            await initApp();
        } else {
            const err = await res.json();
            showError('login-error', err.detail || 'Login failed');
        }
    } catch (e) {
        showError('login-error', 'Network error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

async function handleRegister() {
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    if (!username || !password) return showError('reg-error', 'Username and password are required');
    
    const btn = document.getElementById('register-btn');
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    
    try {
        const res = await fetch(API + '/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email: email || null }),
        });
        
        if (res.ok) {
            const data = await res.json();
            saveTokens(data.access_token, data.refresh_token);
            await initApp();
        } else {
            const err = await res.json();
            showError('reg-error', err.detail || 'Registration failed');
        }
    } catch (e) {
        showError('reg-error', 'Network error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}

async function handleLogout() {
    if (state.refreshToken) {
        await apiRequest('POST', '/api/auth/logout', { refresh_token: state.refreshToken }, false);
    }
    clearTokens();
    state.currentUser = null;
    state.currentChatId = null;
    state.chats = [];
    showAuth();
}

async function loadCurrentUser() {
    const res = await apiRequest('GET', '/api/auth/me');
    if (res && res.ok) {
        state.currentUser = await res.json();
        const initial = state.currentUser.username[0].toUpperCase();
        document.getElementById('user-avatar').textContent = initial;
        document.getElementById('username-display').textContent = state.currentUser.username;
    }
}

async function loadChats() {
    const res = await apiRequest('GET', '/api/chats');
    if (res && res.ok) {
        state.chats = await res.json();
        renderChatList();
    }
}

function renderChatList() {
    const list = document.getElementById('chat-list');
    list.innerHTML = '';
    
    if (state.chats.length === 0) {
        list.innerHTML = '<p style="text-align:center;color:var(--text-secondary);font-size:0.8rem;padding:1rem;">No chats yet</p>';
        return;
    }
    
    state.chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = 'chat-item' + (chat.id === state.currentChatId ? ' active' : '');
        item.dataset.id = chat.id;
        item.innerHTML = `
            <span class="chat-item-title">${escapeHtml(chat.title)}</span>
            <button class="chat-delete-btn" data-id="${chat.id}" title="Delete chat">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        `;
        
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.chat-delete-btn')) {
                selectChat(chat.id);
            }
        });
        
        item.querySelector('.chat-delete-btn').addEventListener('click', async (e) => {
            e.stopPropagation();
            await deleteChat(chat.id);
        });
        
        list.appendChild(item);
    });
}

async function createNewChat() {
    const res = await apiRequest('POST', '/api/chats', { title: 'New Chat' });
    if (res && res.ok) {
        const chat = await res.json();
        state.chats.unshift(chat);
        renderChatList();
        await selectChat(chat.id);
    }
}

async function deleteChat(chatId) {
    if (!confirm('Delete this chat?')) return;
    const res = await apiRequest('DELETE', `/api/chats/${chatId}`);
    if (res && (res.ok || res.status === 204)) {
        state.chats = state.chats.filter(c => c.id !== chatId);
        if (state.currentChatId === chatId) {
            state.currentChatId = null;
            document.getElementById('chat-window').classList.add('hidden');
            document.getElementById('empty-state').classList.remove('hidden');
        }
        renderChatList();
    }
}

async function selectChat(chatId) {
    state.currentChatId = chatId;
    renderChatList();
    
    const res = await apiRequest('GET', `/api/chats/${chatId}`);
    if (res && res.ok) {
        const chat = await res.json();
        document.getElementById('chat-title').textContent = chat.title;
        document.getElementById('empty-state').classList.add('hidden');
        document.getElementById('chat-window').classList.remove('hidden');
        renderMessages(chat.messages || []);
    }
}

function renderMessages(messages) {
    const container = document.getElementById('messages-container');
    container.innerHTML = '';
    messages.forEach(msg => appendMessage(msg));
    scrollToBottom();
}

function appendMessage(msg) {
    const container = document.getElementById('messages-container');
    const div = document.createElement('div');
    div.className = `message ${msg.role}`;
    
    const avatarText = msg.role === 'user'
        ? (state.currentUser ? state.currentUser.username[0].toUpperCase() : 'U')
        : 'AI';
    
    div.innerHTML = `
        <div class="message-avatar">${avatarText}</div>
        <div class="message-bubble">${escapeHtml(msg.content)}</div>
    `;
    
    container.appendChild(div);
    return div;
}

function addTypingIndicator() {
    const container = document.getElementById('messages-container');
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = 'typing-indicator';
    div.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    container.appendChild(div);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
    if (state.isSending || !state.currentChatId) return;
    
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    if (!content) return;
    
    state.isSending = true;
    input.value = '';
    input.style.height = 'auto';
    updateSendButton();
    
    appendMessage({ role: 'user', content });
    scrollToBottom();
    addTypingIndicator();
    
    try {
        const res = await apiRequest('POST', `/api/chats/${state.currentChatId}/messages`, { content });
        removeTypingIndicator();
        
        if (res && res.ok) {
            const data = await res.json();
            appendMessage(data.assistant_message);
            scrollToBottom();
            
            // Auto-update title from first message if still "New Chat"
            const chat = state.chats.find(c => c.id === state.currentChatId);
            if (chat && chat.title === 'New Chat') {
                const newTitle = content.substring(0, 40) + (content.length > 40 ? '...' : '');
                const patchRes = await apiRequest('PATCH', `/api/chats/${state.currentChatId}`, { title: newTitle });
                if (patchRes && patchRes.ok) {
                    const updatedChat = await patchRes.json();
                    chat.title = updatedChat.title;
                    document.getElementById('chat-title').textContent = updatedChat.title;
                    renderChatList();
                }
            }
        } else {
            appendMessage({ role: 'assistant', content: 'Error: Failed to get response. Please try again.' });
        }
    } catch (e) {
        removeTypingIndicator();
        appendMessage({ role: 'assistant', content: 'Error: Network issue. Please try again.' });
    } finally {
        state.isSending = false;
        updateSendButton();
    }
}

function updateSendButton() {
    const btn = document.getElementById('send-btn');
    const input = document.getElementById('message-input');
    btn.disabled = state.isSending || !input.value.trim();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function handleOAuthCallback() {
    const hash = window.location.hash;
    if (hash.startsWith('#/oauth')) {
        const params = new URLSearchParams(hash.replace('#/oauth?', ''));
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        if (accessToken && refreshToken) {
            saveTokens(accessToken, refreshToken);
            window.history.replaceState(null, '', '/');
            return true;
        }
    }
    return false;
}

async function initApp() {
    if (!state.accessToken) {
        showAuth();
        return;
    }
    
    await loadCurrentUser();
    if (!state.currentUser) {
        clearTokens();
        showAuth();
        return;
    }
    
    showChat();
    await loadChats();
}

document.addEventListener('DOMContentLoaded', async () => {
    handleOAuthCallback();
    
    // Auth tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const tab = btn.dataset.tab;
            document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
            document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
        });
    });
    
    document.getElementById('login-btn').addEventListener('click', handleLogin);
    document.getElementById('login-password').addEventListener('keydown', e => {
        if (e.key === 'Enter') handleLogin();
    });
    
    document.getElementById('register-btn').addEventListener('click', handleRegister);
    document.getElementById('reg-password').addEventListener('keydown', e => {
        if (e.key === 'Enter') handleRegister();
    });
    
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    document.getElementById('new-chat-btn').addEventListener('click', createNewChat);
    document.getElementById('start-chat-btn').addEventListener('click', createNewChat);
    
    document.getElementById('delete-chat-btn').addEventListener('click', () => {
        if (state.currentChatId) deleteChat(state.currentChatId);
    });
    
    const input = document.getElementById('message-input');
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
        updateSendButton();
    });
    
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    
    await initApp();
});
