// API交互逻辑 - 波奇酱前端API模块 (◕ᴗ◕✿)

const API_BASE_URL = 'http://127.0.0.1:5000/api';
let currentUser = null;
let currentPage = 1;
let currentMode = 'public'; // 'public', 'my', 'search'

// 页面加载时检查用户登录状态
document.addEventListener('DOMContentLoaded', async function() {
    await checkUserStatus();
    loadResources();
});

// 检查用户登录状态
async function checkUserStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/info`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.code === 'success') {
                currentUser = result.data;
                updateUIForLoggedInUser();
            } else {
                updateUIForLoggedOutUser();
            }
        } else {
            updateUIForLoggedOutUser();
        }
    } catch (error) {
        console.error('检查用户状态失败:', error);
        updateUIForLoggedOutUser();
    }
}

// 更新已登录用户的UI
function updateUIForLoggedInUser() {
    // 显示用户信息
    const userInfo = document.getElementById('userInfo');
    const userNickname = document.getElementById('userNickname');
    const myResourcesLink = document.getElementById('myResourcesLink');
    const logoutLink = document.getElementById('logoutLink');
    const loginLink = document.getElementById('loginLink');
    const adminWelcome = document.getElementById('adminWelcome');
    
    if (userInfo) userInfo.style.display = 'block';
    if (userNickname) userNickname.textContent = currentUser.nickname || currentUser.username;
    if (myResourcesLink) myResourcesLink.style.display = 'inline';
    if (logoutLink) logoutLink.style.display = 'inline';
    if (loginLink) loginLink.style.display = 'none';
    
    // 如果是管理员，显示欢迎词
    if (adminWelcome && currentUser && (currentUser.role === 'admin' || currentUser.is_admin)) {
        adminWelcome.style.display = 'block';
    }
}

// 更新未登录用户的UI
function updateUIForLoggedOutUser() {
    const userInfo = document.getElementById('userInfo');
    const myResourcesLink = document.getElementById('myResourcesLink');
    const logoutLink = document.getElementById('logoutLink');
    const loginLink = document.getElementById('loginLink');
    const adminWelcome = document.getElementById('adminWelcome');
    
    if (userInfo) userInfo.style.display = 'none';
    if (myResourcesLink) myResourcesLink.style.display = 'none';
    if (logoutLink) logoutLink.style.display = 'none';
    if (loginLink) loginLink.style.display = 'inline';
    if (adminWelcome) adminWelcome.style.display = 'none';
    
    currentUser = null;
}

// 加载资源列表
async function loadResources() {
    // 开始加载资源
    const cardGrid = document.getElementById('cardGrid');
    
    if (cardGrid) cardGrid.innerHTML = '';
    
    try {
        let url;
        if (currentMode === 'my') {
            url = `${API_BASE_URL}/my-resources`;
        } else {
            url = `${API_BASE_URL}/resources?page=${currentPage}&limit=12`;
        }
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (result.code === 'success') {
            displayResources(result.data);
        } else {
            console.error('加载资源失败:', result.message);
        }
    } catch (error) {
        console.error('加载资源错误:', error);
    }
}

// 显示资源列表
function displayResources(data) {
    const cardGrid = document.getElementById('cardGrid');
    
    if (!cardGrid) return;
    
    const resources = data;
    
    if (!resources || resources.length === 0) {
        cardGrid.innerHTML = '';
        return;
    }
    
    cardGrid.innerHTML = '';
    
    resources.forEach(resource => {
        const card = createResourceCard(resource);
        cardGrid.appendChild(card);
    });
}

// 创建资源卡片
function createResourceCard(resource) {
    const card = document.createElement('div');
    card.className = 'card';
    
    // 设置背景图片
    const backgroundImage = resource.cover || '/static/img/preview.jpg';
    card.style.backgroundImage = `linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.3)), url('${backgroundImage}')`;
    
    // 截取描述文字，保持简洁
    const shortDescription = resource.description && resource.description.length > 30 
        ? resource.description.substring(0, 30) + '...' 
        : resource.description || '精彩内容等你发现';
    
    card.innerHTML = `
        <div class="card-content">
            <h3>${resource.title}</h3>
            <p>${shortDescription}</p>
        </div>
    `;
    
    // 点击事件 - 显示详细信息或下载
    card.addEventListener('click', () => {
        if (resource.download_url) {
            window.open(resource.download_url, '_blank');
        } else {
            alert(`资源详情:\n标题: ${resource.title}\n描述: ${resource.description}\n分类: ${resource.category}\n作者: ${resource.author}`);
        }
    });
    
    return card;
}

// 显示发布表单
function showPublishForm() {
    if (!currentUser) {
        alert('请先登录喵~ (>﹏<)');
        return;
    }
    
    const publishForm = document.getElementById('publishForm');
    if (publishForm) {
        publishForm.style.display = 'block';
        publishForm.scrollIntoView({ behavior: 'smooth' });
    }
}

// 隐藏发布表单
function hidePublishForm() {
    const publishForm = document.getElementById('publishForm');
    if (publishForm) {
        publishForm.style.display = 'none';
        // 清空表单
        document.getElementById('resourceForm').reset();
        const publishMessage = document.getElementById('publishMessage');
        if (publishMessage) publishMessage.textContent = '';
    }
}

// 发布资源表单提交
document.addEventListener('DOMContentLoaded', function() {
    const resourceForm = document.getElementById('resourceForm');
    if (resourceForm) {
        resourceForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const title = document.getElementById('resourceTitle').value;
            const description = document.getElementById('resourceDescription').value;
            const downloadUrl = document.getElementById('resourceDownloadUrl').value;
            const category = document.getElementById('resourceCategory').value;
            const tags = document.getElementById('resourceTags').value;
            const publishMessage = document.getElementById('publishMessage');
            
            try {
                const response = await fetch(`${API_BASE_URL}/resources`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        title,
                        description,
                        download_url: downloadUrl,
                        category,
                        tags
                    })
                });
                
                const result = await response.json();
                
                if (result.code === 'success') {
                    publishMessage.style.color = '#28a745';
                    publishMessage.textContent = result.message;
                    
                    // 清空表单并隐藏
                    setTimeout(() => {
                        hidePublishForm();
                        // 如果当前在"我的资源"页面，重新加载
                        if (currentMode === 'my') {
                            loadResources();
                        }
                    }, 1500);
                } else {
                    publishMessage.style.color = '#ff6b6b';
                    publishMessage.textContent = result.message;
                }
            } catch (error) {
                publishMessage.style.color = '#ff6b6b';
                publishMessage.textContent = '发布失败，请稍后重试喵~ (>﹏<)';
                console.error('发布资源错误:', error);
            }
        });
    }
});

// 显示公共资源
function showResources() {
    currentMode = 'public';
    currentPage = 1;
    loadResources();
}

// 显示我的资源
function showMyResources() {
    if (!isLoggedIn) {
        alert('请先登录喵~ (◕ᴗ◕✿)');
        return;
    }
    currentMode = 'user';
    currentPage = 1;
    loadResources();
}

// 用户登出
async function logout() {
    try {
        const response = await fetch(`${API_BASE_URL}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (result.code === 'success') {
            updateUIForLoggedOutUser();
            // 如果当前在"我的资源"页面，切换到公共资源
            if (currentMode === 'my') {
                showResources();
            }
            alert(result.message);
        }
    } catch (error) {
        console.error('登出错误:', error);
        alert('登出失败，请稍后重试喵~ (>﹏<)');
    }
}

// 搜索功能
function checkSearch(event) {
    event.preventDefault();
    const searchInput = document.getElementById('search-input');
    const keyword = searchInput.value.trim();
    
    if (keyword === 'zyd') {
        window.location.href = '0v0.html';
        return false;
    }
    
    if (keyword) {
        searchResources(keyword);
    }
    
    return false;
}

// 搜索小说
async function searchResources(keyword) {
    try {
        console.log('🔍 开始搜索小说:', keyword);
        
        // 显示加载状态
        const cardGrid = document.getElementById('cardGrid');
        if (cardGrid) {
            cardGrid.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">🔍 正在搜索小说中，请稍候喵～</div>';
        }
        
        const response = await fetch(`${API_BASE_URL}/novel/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ keyword: keyword })
        });
        
        const result = await response.json();
        
        if (result.success && result.data && result.data.length > 0) {
            currentMode = 'search';
            currentPage = 1;
            // 显示小说搜索结果
            displayNovels(result.data);
            console.log('✅ 搜索成功，找到', result.data.length, '本小说');
        } else {
            // 显示无结果信息
            if (cardGrid) {
                cardGrid.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">😿 没有找到相关小说喵～<br>试试其他关键词吧！</div>';
            }
            console.log('❌ 搜索结果为空:', result.message);
        }
    } catch (error) {
        console.error('❌ 搜索错误:', error);
        const cardGrid = document.getElementById('cardGrid');
        if (cardGrid) {
            cardGrid.innerHTML = '<div style="text-align: center; padding: 50px; color: #ff6b6b;">😿 搜索失败，请稍后重试喵～</div>';
        }
    }
}

// 显示小说搜索结果
function displayNovels(novels) {
    const cardGrid = document.getElementById('cardGrid');
    
    if (!cardGrid) return;
    
    if (!novels || novels.length === 0) {
        cardGrid.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">😿 没有找到相关小说喵～</div>';
        return;
    }
    
    cardGrid.innerHTML = '';
    
    novels.forEach(novel => {
        const card = createNovelCard(novel);
        cardGrid.appendChild(card);
    });
}

// 创建小说卡片
function createNovelCard(novel) {
    const card = document.createElement('div');
    card.className = 'card';
    
    // 截取简介文字
    const shortIntro = novel.intro && novel.intro.length > 50 
        ? novel.intro.substring(0, 50) + '...' 
        : novel.intro || '精彩小说等你阅读';
    
    card.innerHTML = `
        <a href="${novel.url}" target="_blank">
            <img src="${novel.cover_url || '/static/img/preview.jpg'}" alt="${novel.title}" onerror="this.src='/static/img/preview.jpg'">
            <div class="card-content">
                <h3>${novel.title}</h3>
                <p>${shortIntro}</p>
                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                    <span>作者: ${novel.author}</span>
                    <span style="margin-left: 15px;">状态: ${novel.status}</span>
                </div>
                <div style="margin-top: 5px; font-size: 12px; color: #28a745;">
                    <span>📖 点击阅读</span>
                </div>
            </div>
        </a>
    `;
    
    return card;
}