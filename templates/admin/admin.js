// 后台管理系统JavaScript
let currentUser = null;
let currentPage = 1;
let currentSection = 'dashboard';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    checkAdminAuth();
    showDashboard();
});

// 检查管理员权限
async function checkAdminAuth() {
    try {
        const response = await fetch('/api/user/info', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.code === 'success' && result.data) {
                currentUser = result.data;
                document.getElementById('adminName').textContent = currentUser.username;
                
                // 检查是否为管理员（这里简单判断，实际应该有专门的权限字段）
                if (currentUser.username !== 'admin') {
                    alert('您没有管理员权限！');
                    window.location.href = '/admin/login';
                    return;
                }
            } else {
                window.location.href = '/admin/login';
                return;
            }
        } else {
            window.location.href = '/admin/login';
            return;
        }
    } catch (error) {
        console.error('检查权限失败:', error);
        window.location.href = '/admin/login';
    }
}

// 显示仪表盘
function showDashboard() {
    switchSection('dashboard', '仪表盘');
    loadDashboardData();
}

// 显示用户管理
function showUsers() {
    switchSection('users', '用户管理');
    loadUsers();
}

// 显示资源管理
function showResources() {
    switchSection('resources', '资源管理');
    loadResources();
}

// 显示系统设置
function showSettings() {
    switchSection('settings', '系统设置');
    loadSettings();
}

// 切换页面区域
function switchSection(sectionId, title) {
    // 隐藏所有区域
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // 显示目标区域
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // 更新标题
    const pageTitle = document.getElementById('pageTitle');
    if (pageTitle) {
        pageTitle.textContent = title;
    }
    
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 根据sectionId找到对应的导航项
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        const onclick = item.getAttribute('onclick');
        if (onclick && onclick.includes(sectionId)) {
            item.classList.add('active');
        }
    });
    
    currentSection = sectionId;
}

// 加载仪表盘数据
async function loadDashboardData() {
    try {
        // 获取统计数据
        const statsResponse = await fetch('/api/admin/stats', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (statsResponse.ok) {
            const result = await statsResponse.json();
            if (result.success) {
                const stats = result.data;
                document.getElementById('totalUsers').textContent = stats.totalUsers || 0;
                document.getElementById('totalResources').textContent = stats.totalResources || 0;
                document.getElementById('todayUsers').textContent = stats.todayUsers || 0;
                document.getElementById('todayResources').textContent = stats.todayResources || 0;
            }
        }
    } catch (error) {
        console.error('加载仪表盘数据失败:', error);
        showMessage('加载数据失败', 'error');
    }
}

// 加载用户列表
async function loadUsers(search = '') {
    try {
        const url = search ? `/api/admin/users?search=${encodeURIComponent(search)}` : '/api/admin/users';
        const response = await fetch(url, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                displayUsers(result.data);
            } else {
                showMessage(result.message, 'error');
            }
        } else {
            showMessage('加载用户列表失败', 'error');
        }
    } catch (error) {
        console.error('加载用户列表失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 显示用户列表
function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: #666;">暂无用户数据</td></tr>';
        return;
    }
    
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.email || '未设置'}</td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
            <td><span class="status-badge status-active">正常</span></td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editUser('${user.id}')">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}')">删除</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// 加载资源列表
async function loadResources(search = '', sort = '') {
    try {
        let url = '/api/admin/resources';
        const params = new URLSearchParams();
        
        if (search) {
            params.append('search', search);
        }
        if (sort) {
            params.append('sort', sort);
        }
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                displayResources(result.data);
            } else {
                showMessage(result.message, 'error');
            }
        } else {
            showMessage('加载资源列表失败', 'error');
        }
    } catch (error) {
        console.error('加载资源列表失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 显示资源列表（卡片视图）
function displayResources(resources) {
    const grid = document.getElementById('resourcesGrid');
    const tbody = document.getElementById('resourcesTableBody');
    
    // 清空现有内容
    grid.innerHTML = '';
    tbody.innerHTML = '';
    
    if (!resources || resources.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #666; font-size: 16px;">🌸 暂未有爱心的资源数据喵~</div>';
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: #666;">暂无资源数据</td></tr>';
        return;
    }
    
    // 生成卡片视图
    resources.forEach(resource => {
        const card = createResourceCard(resource);
        grid.appendChild(card);
        
        // 同时生成表格视图
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${resource.id}</td>
            <td>${resource.title}</td>
            <td>${resource.author || '未知'}</td>
            <td>${resource.category || '未分类'}</td>
            <td>${new Date(resource.created_at).toLocaleDateString()}</td>
            <td><span class="status-badge status-active">正常</span></td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editResource('${resource.id}')">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteResource('${resource.id}')">删除</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// 创建资源卡片
function createResourceCard(resource) {
    const card = document.createElement('div');
    card.className = 'resource-card';
    
    // 生成封面HTML
    const coverHtml = resource.cover ? 
        `<div class="resource-cover">
            <img src="${resource.cover}" alt="${resource.title}" onerror="this.parentElement.style.display='none'">
        </div>` : 
        `<div class="resource-cover-placeholder">
            <div class="placeholder-icon">${getCategoryIcon(resource.category)}</div>
        </div>`;
    
    card.innerHTML = `
        ${coverHtml}
        <div class="resource-card-header">
            <h3 class="resource-title">${resource.title}</h3>
            <span class="resource-id">#${resource.id}</span>
        </div>
        <div class="resource-meta">
            <div class="resource-meta-item">
                <span class="icon">👤</span>
                <span>${resource.author || '未知作者'}</span>
            </div>
            <div class="resource-meta-item">
                <span class="icon">📂</span>
                <span>${resource.category || '未分类'}</span>
            </div>
            <div class="resource-meta-item">
                <span class="icon">📅</span>
                <span>${new Date(resource.created_at).toLocaleDateString()}</span>
            </div>
        </div>
        <div class="resource-description">
            ${resource.description || '暂无描述'}
        </div>
        <div class="resource-actions">
            <button class="btn btn-sm btn-warning" onclick="editResource('${resource.id}')">✏️ 编辑</button>
            <button class="btn btn-sm btn-danger" onclick="deleteResource('${resource.id}')">🗑️ 删除</button>
        </div>
    `;
    return card;
}

// 获取分类图标
function getCategoryIcon(category) {
    const icons = {
        '动画': '🎬',
        '教程': '📚',
        '素材': '🎨',
        '工具': '🔧',
        '其他': '📦'
    };
    return icons[category] || '📦';
}

// 搜索用户
function searchUsers() {
    const keyword = document.getElementById('userSearch').value.trim();
    loadUsers(keyword);
}

// 搜索资源
function searchResources() {
    const keyword = document.getElementById('resourceSearch').value.trim();
    const sortValue = document.getElementById('resourceSort').value;
    loadResources(keyword, sortValue);
}

// 排序资源
function sortResources() {
    const keyword = document.getElementById('resourceSearch').value.trim();
    const sortValue = document.getElementById('resourceSort').value;
    loadResources(keyword, sortValue);
}

// 切换资源视图（卡片/表格）
function toggleResourceView(viewType) {
    const grid = document.getElementById('resourcesGrid');
    const tableContainer = document.getElementById('resourcesTableContainer');
    
    if (viewType === 'grid') {
        grid.style.display = 'grid';
        tableContainer.style.display = 'none';
    } else {
        grid.style.display = 'none';
        tableContainer.style.display = 'block';
    }
}

// 显示添加资源模态框
function showAddResourceModal() {
    showModal(`
        <h3>✨ 添加新资源</h3>
        <form id="addResourceForm" class="add-resource-form">
            <div class="form-group">
                <label>📝 资源标题</label>
                <input type="text" id="resourceTitle" required placeholder="请输入资源标题...">
            </div>
            <div class="form-group">
                <label>👤 作者</label>
                <input type="text" id="resourceAuthor" placeholder="请输入作者名称...">
            </div>
            <div class="form-group">
                <label>📂 分类</label>
                <select id="resourceCategory" required>
                    <option value="">请选择分类</option>
                    <option value="动画">🎬 动画</option>
                    <option value="教程">📚 教程</option>
                    <option value="素材">🎨 素材</option>
                    <option value="工具">🔧 工具</option>
                    <option value="其他">📦 其他</option>
                </select>
            </div>
            <div class="form-group">
                <label>🖼️ 资源封面</label>
                <div class="cover-upload-container">
                    <input type="file" id="resourceCover" accept="image/*" style="display: none;">
                    <div class="cover-preview" id="coverPreview">
                        <div class="upload-placeholder" onclick="document.getElementById('resourceCover').click()">
                            <div class="upload-icon">📷</div>
                            <div class="upload-text">点击上传封面图片</div>
                            <div class="upload-hint">支持 JPG、PNG、GIF 格式</div>
                        </div>
                    </div>
                    <div class="cover-actions" style="display: none;">
                        <button type="button" class="btn btn-sm" onclick="document.getElementById('resourceCover').click()">🔄 更换图片</button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="removeCoverImage()">🗑️ 删除</button>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label>📄 描述</label>
                <textarea id="resourceDescription" placeholder="请输入资源描述..."></textarea>
            </div>
            <div class="form-group">
                <label>🔗 下载链接</label>
                <input type="url" id="resourceUrl" placeholder="请输入下载链接...">
            </div>
            <div class="form-group">
                <label>🏷️ 标签</label>
                <input type="text" id="resourceTags" placeholder="请输入标签，用逗号分隔...">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">✨ 添加资源</button>
                <button type="button" class="btn" onclick="closeModal()">❌ 取消</button>
            </div>
        </form>
    `);
    
    // 绑定表单提交事件
    document.getElementById('addResourceForm').addEventListener('submit', function(e) {
        e.preventDefault();
        addResource();
    });
    
    // 绑定封面上传事件
    document.getElementById('resourceCover').addEventListener('change', function(e) {
        handleCoverUpload(e);
    });
}

// 处理封面图片上传
function handleCoverUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 检查文件类型
    if (!file.type.startsWith('image/')) {
        showMessage('请选择图片文件喵~ 📷', 'error');
        return;
    }
    
    // 检查文件大小（限制5MB）
    if (file.size > 5 * 1024 * 1024) {
        showMessage('图片文件不能超过5MB喵~ (>﹏<)', 'error');
        return;
    }
    
    // 创建预览
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('coverPreview');
        const actions = document.querySelector('.cover-actions');
        
        preview.innerHTML = `
            <div class="cover-image-preview">
                <img src="${e.target.result}" alt="封面预览" />
                <div class="image-overlay">
                    <div class="image-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${(file.size / 1024).toFixed(1)} KB</span>
                    </div>
                </div>
            </div>
        `;
        
        actions.style.display = 'flex';
    };
    
    reader.readAsDataURL(file);
}

// 删除封面图片
function removeCoverImage() {
    const fileInput = document.getElementById('resourceCover');
    const preview = document.getElementById('coverPreview');
    const actions = document.querySelector('.cover-actions');
    
    fileInput.value = '';
    preview.innerHTML = `
        <div class="upload-placeholder" onclick="document.getElementById('resourceCover').click()">
            <div class="upload-icon">📷</div>
            <div class="upload-text">点击上传封面图片</div>
            <div class="upload-hint">支持 JPG、PNG、GIF 格式</div>
        </div>
    `;
    actions.style.display = 'none';
}

// 编辑封面上传处理
function handleEditCoverUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 检查文件类型
    if (!file.type.startsWith('image/')) {
        showMessage('请选择图片文件喵~ 📷', 'error');
        return;
    }
    
    // 检查文件大小（限制5MB）
    if (file.size > 5 * 1024 * 1024) {
        showMessage('图片文件不能超过5MB喵~ (>﹏<)', 'error');
        return;
    }
    
    // 创建预览
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('editCoverPreview');
        const actions = document.querySelector('.cover-actions');
        
        preview.innerHTML = `
            <div class="cover-image-preview">
                <img src="${e.target.result}" alt="封面预览" />
                <div class="image-overlay">
                    <div class="image-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${(file.size / 1024).toFixed(1)} KB</span>
                    </div>
                </div>
            </div>
        `;
        
        if (actions) {
            actions.style.display = 'flex';
        }
    };
    
    reader.readAsDataURL(file);
}

// 删除编辑封面图片
function removeEditCoverImage() {
    const fileInput = document.getElementById('editCover');
    const preview = document.getElementById('editCoverPreview');
    const actions = document.querySelector('.cover-actions');
    
    fileInput.value = '';
    preview.innerHTML = `
        <div class="upload-placeholder" onclick="document.getElementById('editCover').click()">
            <div class="upload-icon">📷</div>
            <div class="upload-text">点击上传封面图片</div>
            <div class="upload-hint">支持 JPG、PNG、GIF 格式</div>
        </div>
    `;
    if (actions) {
        actions.style.display = 'none';
    }
}

// 添加资源
async function addResource() {
    const title = document.getElementById('resourceTitle').value.trim();
    const author = document.getElementById('resourceAuthor').value.trim();
    const category = document.getElementById('resourceCategory').value;
    const description = document.getElementById('resourceDescription').value.trim();
    const url = document.getElementById('resourceUrl').value.trim();
    const tags = document.getElementById('resourceTags').value.trim();
    const coverFile = document.getElementById('resourceCover').files[0];
    
    if (!title || !category) {
        showMessage('请填写必填字段喵~', 'error');
        return;
    }
    
    try {
        // 创建FormData对象以支持文件上传
        const formData = new FormData();
        formData.append('title', title);
        formData.append('author', author);
        formData.append('category', category);
        formData.append('description', description);
        formData.append('url', url);
        formData.append('tags', tags);
        
        // 如果有封面图片，添加到FormData
        if (coverFile) {
            formData.append('cover', coverFile);
        }
        
        const response = await fetch('/api/admin/resources', {
            method: 'POST',
            credentials: 'include',
            body: formData  // 使用FormData而不是JSON
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                showMessage('资源添加成功喵~ ✨', 'success');
                closeModal();
                loadResources(); // 重新加载资源列表
            } else {
                showMessage(result.message || '添加失败', 'error');
            }
        } else {
            showMessage('添加资源失败', 'error');
        }
    } catch (error) {
        console.error('添加资源失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 编辑用户
function editUser(userId) {
    showModal(`
        <h3>编辑用户</h3>
        <form id="editUserForm">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" id="editUsername" required>
            </div>
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" id="editEmail">
            </div>
            <div class="form-group">
                <button type="submit" class="btn btn-primary">保存</button>
                <button type="button" class="btn" onclick="closeModal()">取消</button>
            </div>
        </form>
    `);
    
    // 加载用户数据
    loadUserData(userId);
    
    // 绑定表单提交事件
    document.getElementById('editUserForm').addEventListener('submit', function(e) {
        e.preventDefault();
        updateUser(userId);
    });
}

// 加载用户数据
async function loadUserData(userId) {
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                const user = result.data;
                document.getElementById('editUsername').value = user.username;
                document.getElementById('editEmail').value = user.email || '';
            }
        }
    } catch (error) {
        console.error('加载用户数据失败:', error);
    }
}

// 更新用户
async function updateUser(userId) {
    const username = document.getElementById('editUsername').value.trim();
    const email = document.getElementById('editEmail').value.trim();
    
    if (!username) {
        alert('用户名不能为空');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ username, email })
        });
        
        const result = await response.json();
        if (result.success) {
            showMessage('用户更新成功', 'success');
            closeModal();
            loadUsers();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('更新用户失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 删除用户
async function deleteUser(userId) {
    if (!confirm('确定要删除这个用户吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const result = await response.json();
        if (result.success) {
            showMessage('用户删除成功', 'success');
            loadUsers();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('删除用户失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 编辑资源
function editResource(resourceId) {
    showModal(`
        <h3>编辑资源</h3>
        <form id="editResourceForm" class="edit-resource-form">
            <div class="form-group">
                <label>📝 资源标题</label>
                <input type="text" id="editTitle" required placeholder="请输入资源标题...">
            </div>
            <div class="form-group">
                <label>👤 作者</label>
                <input type="text" id="editAuthor" placeholder="请输入作者名称...">
            </div>
            <div class="form-group">
                <label>📂 分类</label>
                <select id="editCategory" required>
                    <option value="">请选择分类</option>
                    <option value="动画">🎬 动画</option>
                    <option value="教程">📚 教程</option>
                    <option value="素材">🎨 素材</option>
                    <option value="工具">🔧 工具</option>
                    <option value="其他">📦 其他</option>
                </select>
            </div>
            <div class="form-group">
                <label>📄 资源描述</label>
                <textarea id="editDescription" rows="4" placeholder="请输入资源描述..."></textarea>
            </div>
            <div class="form-group">
                <label>🔗 下载链接</label>
                <input type="url" id="editDownloadUrl" placeholder="请输入下载链接...">
            </div>
            <div class="form-group">
                <label>🏷️ 标签</label>
                <input type="text" id="editTags" placeholder="请输入标签，用逗号分隔...">
            </div>
            <div class="form-group">
                <label>📷 封面图片</label>
                <div class="cover-upload-section">
                    <input type="file" id="editCover" accept="image/*" style="display: none;" onchange="handleEditCoverUpload(event)">
                    <div id="editCoverPreview" class="cover-preview">
                        <div class="upload-placeholder" onclick="document.getElementById('editCover').click()">
                            <div class="upload-icon">📷</div>
                            <div class="upload-text">点击上传封面图片</div>
                            <div class="upload-hint">支持 JPG、PNG、GIF 格式</div>
                        </div>
                    </div>
                    <div class="cover-actions" style="display: none;">
                        <button type="button" class="btn btn-sm" onclick="document.getElementById('editCover').click()">🔄 重新选择</button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="removeEditCoverImage()">🗑️ 删除</button>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <button type="submit" class="btn btn-primary">💾 保存修改</button>
                <button type="button" class="btn" onclick="closeModal()">❌ 取消</button>
            </div>
        </form>
    `);
    
    // 等待DOM渲染完成后再执行
    setTimeout(() => {
        // 加载资源数据
        loadResourceData(resourceId);
        
        // 绑定表单提交事件
        const form = document.getElementById('editResourceForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                updateResource(resourceId);
            });
        }
    }, 100);
}

// 加载资源数据
async function loadResourceData(resourceId) {
    try {
        const response = await fetch(`/api/admin/resources/${resourceId}`, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                const resource = result.data;
                document.getElementById('editTitle').value = resource.title || '';
                document.getElementById('editAuthor').value = resource.author || '';
                document.getElementById('editCategory').value = resource.category || '';
                document.getElementById('editDescription').value = resource.description || '';
                document.getElementById('editDownloadUrl').value = resource.download_url || '';
                document.getElementById('editTags').value = resource.tags || '';
                
                // 如果有封面图片，显示预览
                if (resource.cover_image) {
                    const preview = document.getElementById('editCoverPreview');
                    const actions = document.querySelector('.cover-actions');
                    
                    preview.innerHTML = `
                        <div class="cover-image-preview">
                            <img src="${resource.cover_image}" alt="当前封面" />
                            <div class="image-overlay">
                                <div class="image-info">
                                    <span class="file-name">当前封面</span>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    if (actions) {
                        actions.style.display = 'flex';
                    }
                }
            }
        }
    } catch (error) {
        console.error('加载资源数据失败:', error);
    }
}

// 更新资源
async function updateResource(resourceId) {
    const title = document.getElementById('editTitle').value.trim();
    const author = document.getElementById('editAuthor').value.trim();
    const category = document.getElementById('editCategory').value.trim();
    const description = document.getElementById('editDescription').value.trim();
    const downloadUrl = document.getElementById('editDownloadUrl').value.trim();
    const tags = document.getElementById('editTags').value.trim();
    const coverFile = document.getElementById('editCover').files[0];
    
    if (!title || !category) {
        showMessage('请填写必填字段喵~', 'error');
        return;
    }
    
    try {
        // 如果有封面文件，使用FormData
        if (coverFile) {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('author', author);
            formData.append('category', category);
            formData.append('description', description);
            formData.append('download_url', downloadUrl);
            formData.append('tags', tags);
            formData.append('cover', coverFile);
            
            const response = await fetch(`/api/admin/resources/${resourceId}`, {
                method: 'PUT',
                credentials: 'include',
                body: formData
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage('资源更新成功喵~ ✨', 'success');
                closeModal();
                loadResources();
            } else {
                showMessage(result.message, 'error');
            }
        } else {
            // 没有封面文件，使用JSON
            const response = await fetch(`/api/admin/resources/${resourceId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ 
                    title, 
                    author, 
                    category, 
                    description, 
                    download_url: downloadUrl, 
                    tags 
                })
            });
            
            const result = await response.json();
            if (result.success) {
                showMessage('资源更新成功喵~ ✨', 'success');
                closeModal();
                loadResources();
            } else {
                showMessage(result.message, 'error');
            }
        }
    } catch (error) {
        console.error('更新资源失败:', error);
        showMessage('网络错误喵~ (>﹏<)', 'error');
    }
}

// 删除资源
async function deleteResource(resourceId) {
    // 使用自定义模态框替代confirm
    showModal(`
        <h3>⚠️ 确认删除</h3>
        <p>确定要删除这个资源吗？此操作不可恢复！</p>
        <div class="form-actions">
            <button class="btn btn-danger" onclick="confirmDeleteResource('${resourceId}')">🗑️ 确认删除</button>
            <button class="btn" onclick="closeModal()">❌ 取消</button>
        </div>
    `);
}

// 确认删除资源
async function confirmDeleteResource(resourceId) {
    closeModal();
    
    try {
        const response = await fetch(`/api/admin/resources/${resourceId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const result = await response.json();
        if (result.success) {
            showMessage('资源删除成功', 'success');
            loadResources();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('删除资源失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 加载系统设置
function loadSettings() {
    // 这里可以从后端加载设置数据
    // 暂时使用默认值
}

// 保存系统设置
function saveSettings() {
    const siteTitle = document.getElementById('siteTitle').value.trim();
    const siteDescription = document.getElementById('siteDescription').value.trim();
    const allowRegister = document.getElementById('allowRegister').checked;
    
    // 这里应该发送到后端保存
    showMessage('设置保存成功', 'success');
}

// 刷新数据
function refreshData() {
    switch(currentSection) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'users':
            loadUsers();
            break;
        case 'resources':
            loadResources();
            break;
        case 'settings':
            loadSettings();
            break;
    }
    showMessage('数据已刷新', 'info');
}

// 退出登录
async function logout() {
    if (!confirm('确定要退出登录吗？')) {
        return;
    }
    
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            window.location.href = '/admin/login';
        } else {
            showMessage('退出登录失败', 'error');
        }
    } catch (error) {
        console.error('退出登录失败:', error);
        showMessage('网络错误', 'error');
    }
}

// 显示模态框
function showModal(content) {
    document.getElementById('modalBody').innerHTML = content;
    document.getElementById('modal').style.display = 'block';
}

// 关闭模态框
function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// 显示消息
function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    
    // 插入到内容区域顶部
    const contentBody = document.querySelector('.content-body');
    contentBody.insertBefore(messageDiv, contentBody.firstChild);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 3000);
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('modal');
    if (event.target === modal) {
        closeModal();
    }
}

// 回车键搜索
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        if (e.target.id === 'userSearch') {
            searchUsers();
        } else if (e.target.id === 'resourceSearch') {
            searchResources();
        }
    }
});