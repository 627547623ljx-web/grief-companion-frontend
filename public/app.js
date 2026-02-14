// 预定义的后端地址集合
const BACKEND_PRESETS = {
    'local': 'http://localhost:7860',
    'cloud': 'https://1332551170-4tuhxe4fzv.ap-guangzhou.tencentscf.com/api',
    'custom': ''  // 用户自定义
};

// 获取后端 API 地址（支持多种配置方式）
function getBackendApiUrl() {
    // 优先级 0: 检查是否由后端注入了地址（当由后端serve时）
    if (typeof window.BACKEND_AUTH_API_INJECTED !== 'undefined' && window.BACKEND_AUTH_API_INJECTED) {
        console.log('使用后端注入的 API 地址:', window.BACKEND_AUTH_API_INJECTED);
        return window.BACKEND_AUTH_API_INJECTED;
    }
    
    // 优先级 1: URL 参数 (?api=xxx)
    const urlParams = new URLSearchParams(window.location.search);
    const paramApi = urlParams.get('api');
    if (paramApi) {
        console.log('从 URL 参数读取 API 地址:', paramApi);
        return paramApi;
    }
    
    // 优先级 2: localStorage 中用户自定义的地址
    const savedApi = localStorage.getItem('customBackendUrl');
    if (savedApi) {
        console.log('从本地存储读取 API 地址:', savedApi);
        return savedApi;
    }
    
    // 优先级 3: 本地开发环境自动检测
    const localhost = 'http://localhost:7860';
    const cloudService = 'https://1332551170-4tuhxe4fzv.ap-guangzhou.tencentscf.com/api';
    
    if (window.location.hostname === 'localhost' || 
        window.location.hostname === '127.0.0.1' || 
        window.location.hostname === '0.0.0.0') {
        console.log('检测到本地环境，使用本地后端');
        return localhost;
    }
    
    // 默认: 使用云端服务
    console.log('使用云端服务');
    return cloudService;
}

// 初始化 API 地址
let BACKEND_AUTH_API = getBackendApiUrl();
let BACKEND_STATS_API = BACKEND_AUTH_API + "/user/statistics";
let BACKEND_HISTORY_API = BACKEND_AUTH_API + "/user/emotion-history";
const BACKEND_API = BACKEND_AUTH_API + "/chat";

let currentUser = null;
let isLoginMode = true;  // true=登录模式, false=注册模式
let currentUserType = 'Partner';
let conversationCount = 0;
let moodHistory = [];

// ===== 认证相关函数 =====
async function handleAuthSubmit(event) {
    event.preventDefault();
    clearAuthErrors();
    
    const username = document.getElementById('authUsername').value.trim();
    const password = document.getElementById('authPassword').value;
    
    if (username.length < 3) {
        showAuthError('usernameError', '用户名至少3个字符');
        return;
    }
    if (password.length < 6) {
        showAuthError('passwordError', '密码至少6个字符');
        return;
    }
    
    if (isLoginMode) {
        // 登录
        console.log('[AUTH DEBUG] **LOGIN MODE** - username:', username);
        try {
            const response = await fetch(`${BACKEND_AUTH_API}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            console.log('[AUTH DEBUG] Login response:', JSON.stringify(data));
            if (data.success) {
                console.log('[AUTH DEBUG] Login successful, saving to localStorage:', 
                    'userId=' + data.userId + ', userName=' + data.userName + ', token=' + (data.token ? 'exists' : 'missing'));
                localStorage.setItem('token', data.token);
                localStorage.setItem('userId', data.userId);
                localStorage.setItem('userName', data.userName);
                currentUser = { id: data.userId, name: data.userName };
                console.log('[AUTH DEBUG] currentUser set to:', JSON.stringify(currentUser));
                console.log('[AUTH DEBUG] localStorage keys after login:', Object.keys(localStorage));
                showApp();
            } else {
                showAuthError('authError', data.error || '登录失败');
            }
        } catch (error) {
            console.error('Login error:', error);
            showAuthError('authError', '网络连接失败，请检查后端是否运行：\n' + BACKEND_AUTH_API);
        }
    } else {
        // 注册
        console.log('[AUTH DEBUG] **REGISTER MODE** - username:', username);
        const confirmPassword = document.getElementById('authConfirm').value;
        if (password !== confirmPassword) {
            showAuthError('confirmError', '两次密码不一致');
            return;
        }
        
        try {
            const response = await fetch(`${BACKEND_AUTH_API}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            console.log('[AUTH DEBUG] Register response:', JSON.stringify(data));
            if (data.success) {
                console.log('[AUTH DEBUG] Register successful, saving to localStorage:', 
                    'userId=' + data.userId + ', userName=' + data.userName + ', token=' + (data.token ? 'exists' : 'missing'));
                localStorage.setItem('token', data.token);
                localStorage.setItem('userId', data.userId);
                localStorage.setItem('userName', data.userName);
                currentUser = { id: data.userId, name: data.userName };
                console.log('[AUTH DEBUG] currentUser set to:', JSON.stringify(currentUser));
                console.log('[AUTH DEBUG] localStorage keys after register:', Object.keys(localStorage));
                showApp();
            } else {
                showAuthError('authError', data.error || '注册失败');
            }
        } catch (error) {
            console.error('Register error:', error);
            showAuthError('authError', '网络连接失败，请检查后端是否运行：\n' + BACKEND_AUTH_API);
        }
    }
}

function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    clearAuthErrors();
    
    const title = document.getElementById('authTitle');
    const subtitle = document.getElementById('authSubtitle');
    const authBtn = document.getElementById('authBtn');
    const toggleText = document.getElementById('toggleText');
    const confirmGroup = document.getElementById('confirmPasswordGroup');
    
    if (isLoginMode) {
        title.textContent = '登录陪伴机器人';
        subtitle.textContent = '请输入您的用户名和密码';
        authBtn.textContent = '登录';
        toggleText.textContent = '还没有账号？';
        confirmGroup.style.display = 'none';
        document.getElementById('authConfirm').removeAttribute('required');
    } else {
        title.textContent = '注册账号';
        subtitle.textContent = '创建新账号以开始使用';
        authBtn.textContent = '注册';
        toggleText.textContent = '已有账号？';
        confirmGroup.style.display = 'block';
        document.getElementById('authConfirm').setAttribute('required', '');
    }
}

function showAuthError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.display = 'block';
    }
}

function clearAuthErrors() {
    document.getElementById('usernameError').textContent = '';
    document.getElementById('passwordError').textContent = '';
    document.getElementById('confirmError').textContent = '';
    document.getElementById('authError').textContent = '';
}

function showApp() {
    // 在显示 app 之前，先从后端同步该用户的同意状态（若后端记录存在）
    const userId = localStorage.getItem('userId') || (currentUser && currentUser.id) || null;
    console.log('[SHOWAPP DEBUG] userId:', userId, 'currentUser:', currentUser);
    (async function() {
        if (userId) {
            try {
                const localApiUrl = 'http://localhost:7861/api/consent/' + encodeURIComponent(userId);
                let apiUrl = BACKEND_AUTH_API + '/consent/' + encodeURIComponent(userId);
                if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                    apiUrl = localApiUrl;
                }
                console.log('[SHOWAPP DEBUG] Fetching consent from:', apiUrl);
                const resp = await fetch(apiUrl, { method: 'GET' });
                console.log('[SHOWAPP DEBUG] Consent fetch response status:', resp.status);
                if (resp.ok) {
                    const j = await resp.json();
                    console.log('[SHOWAPP DEBUG] Consent response data:', j);
                    const consentKey = `consent_agreed_${userId}`;
                    if (j.consent === true) {
                        console.log('[SHOWAPP DEBUG] Backend consent=true, storing locally');
                        localStorage.setItem(consentKey, 'true');
                        localStorage.setItem(consentKey + '_date', j.date || new Date().toISOString());
                    } else if (j.consent === false) {
                        console.log('[SHOWAPP DEBUG] Backend consent=false, storing locally');
                        localStorage.setItem(consentKey, 'false');
                        localStorage.setItem(consentKey + '_date', j.date || new Date().toISOString());
                    } else {
                        console.log('[SHOWAPP DEBUG] Backend consent=null (new user), not setting localStorage consent');
                    }
                }
            } catch (e) {
                console.warn('[SHOWAPP DEBUG] Failed to fetch consent from backend:', e);
                console.warn('Unable to fetch consent from server:', e);
            }
        }

        console.log('[SHOWAPP DEBUG] Transitioning to app view, about to call initApp()');
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('appPage').style.display = 'block';
        document.getElementById('userNameDisplay').textContent = currentUser.name;
        // 初始化应用（initApp 会再次检查本地的 per-user consent key）
        initApp();
    })();
}

function logout() {
    if (confirm('确认要登出吗？')) {
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        localStorage.removeItem('userName');
        currentUser = null;
        
        document.getElementById('loginPage').style.display = 'block';
        document.getElementById('appPage').style.display = 'none';
        document.getElementById('authUsername').value = '';
        document.getElementById('authPassword').value = '';
        document.getElementById('authConfirm').value = '';
        clearAuthErrors();
        isLoginMode = true;
        toggleAuthMode();  // 重置为登录模式
    }
}

// 启动时检查是否已登录
window.addEventListener('load', function() {
    console.log('[WINDOW LOAD EVENT] App loading, checking for existing session...');
    const token = localStorage.getItem('token');
    const userId = localStorage.getItem('userId');
    const userName = localStorage.getItem('userName');
    
    console.log('[WINDOW LOAD EVENT] token:', token ? 'exists' : 'null');
    console.log('[WINDOW LOAD EVENT] userId:', userId);
    console.log('[WINDOW LOAD EVENT] userName:', userName);
    
    if (token && userId && userName) {
        console.log('[WINDOW LOAD EVENT] Session exists, restoring user:', userId);
        currentUser = { id: userId, name: userName };
        showApp();
    } else {
        console.log('[WINDOW LOAD EVENT] No session, showing login page');
        document.getElementById('loginPage').style.display = 'block';
        document.getElementById('appPage').style.display = 'none';
    }
});

// 问卷题目数据
const surveyQuestions = [
    { id: 1, text: '在过去的一周内，您是否感到悲伤或沮丧？', options: ['完全没有', '偶尔', '经常', '几乎总是'] },
    { id: 2, text: '您是否能从日常活动中获得快乐感？', options: ['能', '有时能', '很少能', '无法获得'] },
    { id: 3, text: '您是否感到生活失去了目标或意义？', options: ['完全没有', '有所感受', '相当程度上', '非常同意'] },
    { id: 4, text: '您对未来是否有希望？', options: ['很有希望', '有所希望', '希望不大', '完全没有希望'] },
    { id: 5, text: '您是否经历过睡眠困难或过度睡眠？', options: ['没有', '有时', '经常', '严重困扰'] }
];

// 初始化（只在用户登录后由 `showApp()` 调用）
function initApp() {
    console.log('[INITAPP DEBUG] App initializing...');

    // 仅在已有登录用户时检查并展示知情同意书（每个用户只需确认一次）
    const consentModal = document.getElementById('consentModal');
    console.log('[INITAPP DEBUG] consentModal element:', consentModal, 'display:', consentModal ? window.getComputedStyle(consentModal).display : 'N/A');

    const userId = (currentUser && currentUser.id) || localStorage.getItem('userId') || null;
    const consentKey = userId ? `consent_agreed_${userId}` : 'consent_agreed';
    const consentVal = localStorage.getItem(consentKey);
    console.log('[INITAPP DEBUG] userId:', userId, 'consentKey:', consentKey, 'consentVal:', consentVal, 'typeof:', typeof consentVal);
    console.log('[INITAPP DEBUG] Consent check: !consentVal=' + !consentVal + ', consentVal===\'false\'=' + (consentVal === 'false'));

    if (userId) {
        // 已登录用户：如果未同意，则强制显示并阻止继续使用
        console.log('[INITAPP DEBUG] Checking consent for logged-in user, consentVal=' + JSON.stringify(consentVal));
        if (!consentVal || consentVal === 'false') {
            console.log('[INITAPP DEBUG] **SHOWING CONSENT MODAL** for user:', userId);
            if (consentModal) {
                consentModal.classList.add('active');
                console.log('[INITAPP DEBUG] Modal class list after add:', consentModal.className);
            } else {
                console.error('[INITAPP DEBUG] consentModal is null!');
            }
            // 禁用页面其他交互
            document.getElementById('appPage').style.pointerEvents = 'none';
            document.getElementById('appPage').style.opacity = '0.5';
            // 停止初始化，等待用户同意或拒绝
            return;
        } else {
            console.log('[INITAPP DEBUG] Consent already recorded (consentVal=' + JSON.stringify(consentVal) + '), continuing init');
            consentModal.classList.remove('active');
            document.getElementById('appPage').style.pointerEvents = 'auto';
            document.getElementById('appPage').style.opacity = '1';
        }
    } else {
        // 未登录状态：不弹出同意框，等待用户登录/注册后再检查
        console.log('[DEBUG] No logged-in user; skipping consent check until after login.');
    }

    // 检查是否需要显示问卷
    checkAndShowSurvey();

    setupEventListeners();
    initializeSurvey();
    loadUserStatistics();
    loadMoodHistory();
}

// 初始化问卷HTML
function initializeSurvey() {
    const container = document.getElementById('surveyContainer');
    container.innerHTML = '';
    surveyQuestions.forEach(q => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'survey-item';
        itemDiv.innerHTML = `
            <div class="survey-question">${q.id}. ${q.text}</div>
            <div class="survey-options">
                ${q.options.map((opt, idx) => `
                    <label class="survey-radio">
                        <input type="radio" name="question_${q.id}" value="${idx}" />
                        <span>${opt}</span>
                    </label>
                `).join('')}
            </div>
        `;
        container.appendChild(itemDiv);
    });
}

// 知情同意书 - 同意
function acceptConsent() {
    console.log('[CONSENT DEBUG] acceptConsent called');
    const userId = (currentUser && currentUser.id) || localStorage.getItem('userId') || null;
    const consentKey = userId ? `consent_agreed_${userId}` : 'consent_agreed';
    console.log('[CONSENT DEBUG] Accepting consent for userId:', userId, 'consentKey:', consentKey);
    localStorage.setItem(consentKey, 'true');
    localStorage.setItem(`${consentKey}_date`, new Date().toISOString());
    console.log('[CONSENT DEBUG] Stored to localStorage: ' + consentKey + '=true');
    document.getElementById('consentModal').classList.remove('active');
    // 恢复页面交互
    document.getElementById('appPage').style.pointerEvents = 'auto';
    document.getElementById('appPage').style.opacity = '1';
    // 同步到后端记录
    (async function() {
        try {
            const userId = (currentUser && currentUser.id) || localStorage.getItem('userId') || null;
            const localApiUrl = 'http://localhost:7861/api/consent';
            let apiUrl = BACKEND_AUTH_API + '/consent';
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                apiUrl = localApiUrl;
            }
            if (userId) {
                console.log('[CONSENT DEBUG] Syncing consent=true to backend:', apiUrl);
                const syncResp = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: userId, consent: true, date: new Date().toISOString() })
                });
                console.log('[CONSENT DEBUG] Backend sync response status:', syncResp.status);
            }
        } catch (e) {
            console.warn('Failed to sync consent to server:', e);
        }
    })();

    // 继续初始化应用
    console.log('[CONSENT DEBUG] Continuing app initialization...');
    checkAndShowSurvey();
    setupEventListeners();
    initializeSurvey();
    loadUserStatistics();
    loadMoodHistory();
}

// 知情同意书 - 拒绝
function declineConsent() {
    console.log('[CONSENT DEBUG] declineConsent called');
    alert('您已拒绝数据收集。页面将关闭以保护您的选择。');
    const userId = (currentUser && currentUser.id) || localStorage.getItem('userId') || null;
    const consentKey = userId ? `consent_agreed_${userId}` : 'consent_agreed';
    console.log('[CONSENT DEBUG] Declining consent for userId:', userId, 'consentKey:', consentKey);
    localStorage.setItem(consentKey, 'false');
    (async function() {
        try {
            const localApiUrl = 'http://localhost:7861/api/consent';
            let apiUrl = BACKEND_AUTH_API + '/consent';
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                apiUrl = localApiUrl;
            }
            if (userId) {
                console.log('[CONSENT DEBUG] Syncing consent=false to backend:', apiUrl);
                const syncResp = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: userId, consent: false, date: new Date().toISOString() })
                });
                console.log('[CONSENT DEBUG] Backend sync response status:', syncResp.status);
            }
        } catch (e) {
            console.warn('Failed to sync declined consent to server:', e);
        } finally {
            // 强制退出页面（尽量重定向到空白页）
            console.log('[CONSENT DEBUG] Forcing page exit via about:blank');
            try {
                window.location.replace('about:blank');
            } catch (e) {
                // 作为回退，清空页面内容并阻止交互
                console.log('[CONSENT DEBUG] about:blank failed, using fallback clearing');
                document.body.innerHTML = '<div style="padding:40px;font-size:18px;color:#333;">您已拒绝知情同意，页面已关闭。</div>';
            }
        }
    })();
}

// 检查是否显示问卷
function checkAndShowSurvey() {
    const lastSurveyDate = localStorage.getItem('last_survey_date');
    const now = new Date();
    
    if (!lastSurveyDate) {
        // 第一次使用且同意了，5秒后弹出问卷
        if (localStorage.getItem('consent_agreed') === 'true') {
            setTimeout(() => {
                showSurvey();
            }, 3000);
        }
    } else {
        // 检查是否超过5-7天
        const lastDate = new Date(lastSurveyDate);
        const daysDiff = Math.floor((now - lastDate) / (1000 * 60 * 60 * 24));
        
        // 随机5-7天之间的某个时间
        const surveyInterval = 5 + Math.random() * 2; // 5-7天
        if (daysDiff >= surveyInterval) {
            setTimeout(() => {
                showSurvey();
            }, 2000);
        }
    }
}

// 显示问卷
function showSurvey() {
    document.getElementById('surveyModal').classList.add('active');
}

// 关闭问卷（不提交）
function dismissSurvey() {
    document.getElementById('surveyModal').classList.remove('active');
}

// 提交问卷
async function submitSurvey(retryCount = 0) {
    const responses = [];
    let isComplete = true;

    surveyQuestions.forEach(q => {
        const selected = document.querySelector(`input[name="question_${q.id}"]:checked`);
        if (!selected) {
            isComplete = false;
        }
        responses.push({
            question_id: q.id,
            question_text: q.text,
            answer_index: selected ? parseInt(selected.value) : null,
            answer_text: selected ? selected.nextElementSibling.textContent : null
        });
    });

    if (!isComplete) {
        alert('请完成所有问题再提交');
        return;
    }

    // 使用已登录用户的 userId（优先使用 localStorage，回退为 null）
    const userId = localStorage.getItem('userId') || (currentUser && currentUser.id) || null;
    if (!userId) {
        alert('未检测到登录用户，请先登录再提交问卷');
        return;
    }

    try {
        const surveyApi = BACKEND_AUTH_API + '/survey';
        // 尝试连接到本地API服务器（端口7861）
        const localApiUrl = 'http://localhost:7861/api/survey';
        const currentUrl = new URL(window.location.href);
        let apiUrl = surveyApi;
        
        // 如果在本地开发环境，优先使用独立的API服务器
        if (window.location.hostname === 'localhost' || 
            window.location.hostname === '127.0.0.1') {
            apiUrl = localApiUrl;  // 尝试7861端口的独立API服务器
        }
        
        const token = localStorage.getItem('token');

        console.log('正在提交问卷到: ' + apiUrl);

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {})
            },
            body: JSON.stringify({
                userId: userId,
                timestamp: new Date().toISOString(),
                responses: responses
            }),
            timeout: 10000  // 10秒超时
        });

        if (response.ok) {
            const result = await response.json();
            localStorage.setItem('last_survey_date', new Date().toISOString());
            document.getElementById('surveyModal').classList.remove('active');
            addMessage('bot', '✅ 感谢您完成问卷！您的反馈已被记录，这对我们了解您的心理状态非常帮助。');
        } else {
            const text = await response.text().catch(() => '');
            console.error('Survey API error', response.status, text);
            
            // 重试逻辑
            if ((response.status === 503 || response.status === 502 || response.status === 504) && retryCount < 3) {
                console.log('服务暂时不可用，3秒后重试...');
                setTimeout(() => {
                    submitSurvey(retryCount + 1);
                }, 3000);
            } else {
                alert(`问卷提交失败（错误 ${response.status}）\n\n可能的原因：\n1. 后端服务未启动\n2. 网络连接不稳定\n3. 后端服务器离线\n\n请检查后端是否运行或尝试稍后重试`);
            }
        }
    } catch (error) {
        console.error('Survey submission error:', error);
        
        // 提供更详细的错误诊断信息
        let errorMsg = '网络连接失败\n\n';
        if (error.message.includes('Failed to fetch')) {
            errorMsg += '原因：无法连接到后端服务器\n\n';
            errorMsg += '解决方案：\n';
            errorMsg += '1. 确保后端服务已启动\n';
            errorMsg += '   本地运行：python run_app.py\n';
            errorMsg += '2. 检查网络连接\n';
            errorMsg += '3. 确保防火墙未阻止连接\n\n';
            errorMsg += '后端地址：' + BACKEND_AUTH_API;
        } else {
            errorMsg += error.message;
        }
        
        // 自动重试
        if (retryCount < 2) {
            console.log('自动重试第 ' + (retryCount + 1) + ' 次...');
            setTimeout(() => {
                submitSurvey(retryCount + 1);
            }, 2000);
        } else {
            alert(errorMsg);
        }
    }
}

// ===== API 设置相关函数 =====
function showApiSettings() {
    // 更新当前 API 信息
    document.getElementById('currentApiInfo').innerHTML = `
        <strong>当前使用的地址：</strong><br>
        ${BACKEND_AUTH_API}<br><br>
        <small>点击下方选项快速切换或输入自定义地址</small>
    `;
    
    // 更新自定义地址输入框
    const customUrl = localStorage.getItem('customBackendUrl');
    document.getElementById('customApiUrl').value = customUrl || '';
    
    // 显示弹窗
    document.getElementById('apiSettingsModal').classList.add('active');
    
    // 更新按钮状态
    updatePresetButtonStatus();
}

function updatePresetButtonStatus() {
    const localBtn = document.getElementById('presetLocalBtn');
    const cloudBtn = document.getElementById('presetCloudBtn');
    
    localBtn.classList.remove('active');
    cloudBtn.classList.remove('active');
    
    if (BACKEND_AUTH_API.includes('localhost') || BACKEND_AUTH_API.includes('127.0.0.1')) {
        localBtn.classList.add('active');
    } else if (BACKEND_AUTH_API.includes('tencentscf')) {
        cloudBtn.classList.add('active');
    }
}

function selectApiPreset(preset) {
    const url = BACKEND_PRESETS[preset];
    document.getElementById('customApiUrl').value = url;
}

async function testApiConnection() {
    const customUrl = document.getElementById('customApiUrl').value.trim();
    if (!customUrl) {
        alert('请输入 API 地址');
        return;
    }
    
    const result = document.getElementById('apiTestResult');
    result.style.display = 'block';
    result.textContent = '🔄 测试中...';
    result.style.background = '#fff3cd';
    result.style.color = '#856404';
    
    try {
        // 移除末尾的 /api 如果有的话
        let testUrl = customUrl;
        if (testUrl.endsWith('/api')) {
            testUrl = testUrl.slice(0, -4);
        }
        
        const response = await fetch(testUrl + '/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: 'test', userId: 'test' }),
            timeout: 5000
        });
        
        if (response.ok || response.status === 401 || response.status === 400) {
            // 401 或 400 表示后端响应了，虽然请求不合法，但说明连接成功
            result.textContent = '✅ 连接成功！后端服务正常工作';
            result.style.background = '#d4edda';
            result.style.color = '#155724';
        } else if (response.status === 503 || response.status === 502) {
            result.textContent = '⚠️ 后端服务暂时不可用（' + response.status + '）';
            result.style.background = '#f8d7da';
            result.style.color = '#721c24';
        } else {
            result.textContent = '❌ 连接失败（HTTP ' + response.status + '）';
            result.style.background = '#f8d7da';
            result.style.color = '#721c24';
        }
    } catch (error) {
        result.textContent = '❌ 无法连接到该地址：' + error.message;
        result.style.background = '#f8d7da';
        result.style.color = '#721c24';
    }
}

function saveApiSettings() {
    const customUrl = document.getElementById('customApiUrl').value.trim();
    
    if (!customUrl) {
        alert('请输入 API 地址');
        return;
    }
    
    // 保存到 localStorage
    localStorage.setItem('customBackendUrl', customUrl);
    
    // 更新全局变量
    BACKEND_AUTH_API = customUrl;
    BACKEND_STATS_API = BACKEND_AUTH_API + "/user/statistics";
    BACKEND_HISTORY_API = BACKEND_AUTH_API + "/user/emotion-history";
    
    alert('✅ API 地址已更新！\n\n' + customUrl + '\n\n请刷新页面以应用新配置');
    
    // 关闭弹窗
    document.getElementById('apiSettingsModal').classList.remove('active');
}

function setupEventListeners() {
    // 用户类型按钮
    document.querySelectorAll('.type-button').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.type-button').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const typeMap = {'伴侣': 'Partner', '亲人': 'Parent', '宠物': 'Pet'};
            currentUserType = typeMap[this.textContent] || 'Partner';
            updateStatusDisplay();
        });
    });
    
    // 回车发送
    document.getElementById('userInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

async function loadUserStatistics() {
    try {
        const userId = localStorage.getItem('userId');
        const token = localStorage.getItem('token');
        const response = await fetch(BACKEND_STATS_API + '/' + userId, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('interactionCount').textContent = data.totalInteractions || 0;
            const stability = Math.round((100 - Math.abs(data.averageEmotion - 0.5) * 200) * 100) / 100;
            document.getElementById('stabilityScore').textContent = stability.toFixed(1) + '%';
        }
    } catch (error) {
        console.log('Stats API error:', error);
    }
}

async function loadMoodHistory() {
    try {
        const userId = localStorage.getItem('userId');
        const token = localStorage.getItem('token');
        const response = await fetch(BACKEND_HISTORY_API + '/' + userId + '?days=7', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            moodHistory = data.history || [];
        }
    } catch (error) {
        console.log('History API error:', error);
    }
}

async function sendMessage() {
    const input = document.getElementById('userInput').value.trim();
    if (!input) return;
    
    addMessage('user', input);
    document.getElementById('userInput').value = '';
    
    const botMsg = addMessage('bot', '<span class="loading"></span><span class="loading"></span><span class="loading"></span>');
    
    try {
        const token = localStorage.getItem('token');
        const userId = localStorage.getItem('userId');
        
        console.log('正在发送消息到: ' + BACKEND_API);
        
        const response = await fetch(BACKEND_API, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                message: input,
                userId: userId,
                userType: currentUserType
            }),
            timeout: 30000  // 30秒超时
        });
        
        const data = await response.json();
        botMsg.remove();
        
        if (data.response) {
            let messageClass = 'bot-message';
            if (data.alertFlag === 'crisis') {
                messageClass = 'bot-message risk-message';
            }
            
            addMessage('bot', data.response, messageClass);
            updatePanels(data);
            conversationCount++;
            loadUserStatistics();
        } else {
            addMessage('bot', '抱歉，出现了问题。请稍后重试。');
        }
    } catch (error) {
        botMsg.remove();
        console.error('Message send error:', error);
        const errMsg = '网络连接失败\n\n可能的原因：\n1. 后端服务未启动\n2. 后端地址：' + BACKEND_API;
        addMessage('bot', errMsg);
    }
}

function addMessage(role, content, customClass = null) {
    const messageList = document.getElementById('messageList');
    const div = document.createElement('div');
    div.className = customClass || `message ${role}-message`;
    div.innerHTML = content;
    messageList.appendChild(div);
    messageList.scrollTop = messageList.scrollHeight;
    return div;
}

function updatePanels(data) {
    if (data.moodIndex) {
        const moodVal = parseFloat(data.moodIndex) || 50;
        document.getElementById('moodValue').textContent = Math.round(moodVal);
        document.getElementById('moodFill').style.width = moodVal + '%';
        const trend = moodVal > 50 ? '↘ 需要陪伴' : '↗ 逐步恢复';
        document.getElementById('moodTrend').textContent = trend;
    }
    
    if (data.stageInfo) {
        const stageMap = {
            '否认': '正在适应，需要时间',
            '愤怒': '情绪释放的过程',
            '讨价还价': '尝试改变现实',
            '抑郁': '深刻的悲伤感受',
            '接受': '开始新的生活'
        };
        document.getElementById('stageBadge').textContent = data.stageInfo;
        document.getElementById('stageDescription').textContent = stageMap[data.stageInfo] || '未知阶段';
    }
    
    document.getElementById('statusText').textContent = '进行中';
}

function updateStatusDisplay() {}

console.log('[APP.JS] All functions loaded and ready');
