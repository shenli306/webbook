document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");

    const expand = () => {
        searchBtn.classList.toggle("close");
        input.classList.toggle("square");
        if (searchBtn.classList.contains("close")) {
            input.focus();
        }
    };

    searchBtn.addEventListener("click", expand);
});

function checkSearch(event) {
    event.preventDefault(); // 阻止表单默认提交
    
    const searchInput = document.getElementById('search-input');
    const searchValue = searchInput.value.trim().toLowerCase();
    
    // 检查是否输入了"zyd"
    if (searchValue === 'zyd') {
        window.location.href = '0v0.html'; // 跳转到0v0.html
        return false;
    }
    
    // 这里可以添加正常搜索功能的代码
    // ... 
    
    return false; // 防止表单提交
}

// 为搜索按钮添加点击事件
document.getElementById('search-btn').addEventListener('click', function(e) {
    const searchInput = document.getElementById('search-input');
    const searchValue = searchInput.value.trim().toLowerCase();
    
    if (searchValue === 'zyd') {
        window.location.href = '0v0.html';
    }
    // 其他搜索逻辑...
});

// 分类筛选功能
function filterByCategory(category) {
    console.log('筛选分类:', category);
    
    // 更新当前选中的分类标签样式
    const tags = document.querySelectorAll('#categoryTags .tag');
    tags.forEach(tag => tag.classList.remove('active'));
    
    // 找到并高亮当前选中的标签
    const currentTag = Array.from(tags).find(tag => {
        const text = tag.textContent.trim();
        if (category === '') return text.includes('全部');
        return text.includes(category);
    });
    
    if (currentTag) {
        currentTag.classList.add('active');
    }
    
    // 调用API.js中的loadResources函数进行筛选
    if (typeof loadResources === 'function') {
        loadResources(1, category);
    } else {
        console.warn('loadResources函数未找到，请检查api.js是否正确加载');
    }
}

// 头像下拉菜单功能
document.addEventListener('DOMContentLoaded', function() {
    const profileAvatar = document.getElementById('profile-avatar');
    const dropdownMenu = document.getElementById('dropdown-menu');
    
    // 初始化时检查登录状态并更新菜单
    updateDropdownMenu();
    
    // 点击头像切换下拉菜单显示状态
    profileAvatar.addEventListener('click', function(e) {
        e.stopPropagation(); // 阻止事件冒泡
        dropdownMenu.classList.toggle('show');
    });
    
    // 点击页面其他地方关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!profileAvatar.contains(e.target)) {
            dropdownMenu.classList.remove('show');
        }
    });
    
    // 阻止下拉菜单内部点击事件冒泡
    dropdownMenu.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});

// 更新下拉菜单内容
function updateDropdownMenu() {
    const dropdownMenu = document.getElementById('dropdown-menu');
    const userInfo = localStorage.getItem('user');
    
    if (dropdownMenu) {
        if (userInfo) {
            // 已登录，显示退出登录按钮
            const user = JSON.parse(userInfo);
            let menuItems = '<a href="#" class="dropdown-item" onclick="logout(); return false;">退出登录</a>';
            
            // 如果是管理员，添加管理面板链接
            if (user.role === 'admin' || user.is_admin) {
                menuItems += '<a href="/static/admin.html" class="dropdown-item">管理面板</a>';
            }
            
            dropdownMenu.innerHTML = menuItems;
        } else {
            // 未登录，显示登录/注册按钮
            dropdownMenu.innerHTML = `
                <a href="/static/login.html" class="dropdown-item">登录</a>
                <a href="/static/register.html" class="dropdown-item">注册</a>
            `;
        }
    }
}

// 退出登录函数
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    console.log('已退出登录喵~ (◕ᴗ◕✿)');
    
    // 隐藏管理员欢迎信息
    const adminWelcome = document.getElementById('adminWelcome');
    if (adminWelcome) {
        adminWelcome.style.display = 'none';
    }
    
    // 更新下拉菜单
    updateDropdownMenu();
    
    // 刷新页面
    window.location.reload();
}