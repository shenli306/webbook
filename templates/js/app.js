// 猫娘小说下载器 - JavaScript交互逻辑

class NovelDownloader {
    constructor() {
        this.currentNovelUrl = null;
        this.currentTaskId = null;
        this.progressInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDownloadedNovels();
        this.showMessage('欢迎使用猫娘小说下载器喵～', 'info');
    }

    bindEvents() {
        // 搜索按钮事件
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.searchNovels();
        });

        // 搜索框回车事件
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchNovels();
            }
        });

        // 下载按钮事件
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.startDownload();
        });
    }

    // 显示加载动画
    showLoading(type = 'search') {
        document.getElementById('loadingOverlay').style.display = 'flex';
        this.startLoadingAnimation(type);
    }

    // 隐藏加载动画
    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
        this.stopLoadingAnimation();
    }

    // 开始加载动画
    startLoadingAnimation(type = 'search') {
        const terminalBody = document.getElementById('loadingTerminalBody');
        
        // 根据类型选择不同的消息
        let loadingMessages;
        if (type === 'download') {
            loadingMessages = [
                '正在连接服务器喵～',
                '检查网络状态中...',
                '初始化猫娘下载模块ฅ^•ﻌ•^ฅ',
                '准备下载环境...',
                '正在获取小说详情页面...',
                '解析章节列表中...',
                '检查章节完整性...',
                '创建EPUB文件结构...',
                '下载小说封面图片...',
                '开始下载章节内容...',
                '下载准备完成！开始批量下载喵～'
            ];
        } else {
            // 默认搜索消息
            loadingMessages = [
                '正在连接服务器喵～',
                '检查网络状态中...',
                '初始化猫娘模块ฅ^•ﻌ•^ฅ',
                '加载小说数据库...',
                '准备搜索引擎喵～',
                '正在解析搜索关键词...',
                '连接到笔趣阁数据源...',
                '搜索匹配的小说标题...',
                '检索作者信息中...',
                '分析小说分类标签...',
                '获取小说简介数据...',
                '下载封面图片中...',
                '计算相关度评分...',
                '排序搜索结果...',
                '过滤重复内容...',
                '优化显示格式...',
                '搜索完成！找到相关小说 ฅ^•ﻌ•^ฅ',
                '正在准备结果展示喵～'
            ];
        }
        
        let messageIndex = 0;
        this.loadingInterval = setInterval(() => {
            if (messageIndex < loadingMessages.length) {
                const newLine = document.createElement('div');
                newLine.className = 'terminal-line';
                
                // 为不同类型的消息添加不同的样式
                let messageClass = 'terminal-text';
                const message = loadingMessages[messageIndex];
                
                // 下载相关消息样式
                if (message.includes('正在获取') || message.includes('解析章节') || message.includes('检查章节')) {
                    messageClass += ' analyzing';
                } else if (message.includes('创建EPUB') || message.includes('准备下载') || message.includes('下载小说封面')) {
                    messageClass += ' processing';
                } else if (message.includes('开始下载章节') || message.includes('下载准备完成')) {
                    messageClass += ' found';
                } else if (message.includes('正在解析') || message.includes('搜索匹配') || message.includes('连接到')) {
                    messageClass += ' searching';
                } else if (message.includes('检索') || message.includes('分析') || message.includes('计算')) {
                    messageClass += ' analyzing';
                } else if (message.includes('下载封面') || message.includes('排序') || message.includes('过滤') || message.includes('优化')) {
                    messageClass += ' processing';
                } else if (message.includes('搜索完成！找到')) {
                    messageClass += ' found';
                } else if (message.includes('完成')) {
                    messageClass += ' completed';
                } else if (message.includes('正在下载')) {
                    messageClass += ' downloading';
                } else if (message.includes('下载进度')) {
                    messageClass += ' progress';
                } else if (message.includes('下载完成')) {
                    messageClass += ' success';
                }
                
                newLine.innerHTML = `
                    <span class="terminal-prompt">猫娘@下载器:~$</span>
                    <span class="${messageClass}">${loadingMessages[messageIndex]}</span>
                `;
                newLine.style.animation = 'typewriter 0.3s ease-out';
                terminalBody.appendChild(newLine);
                messageIndex++;
                
                // 保持终端滚动到底部
                terminalBody.scrollTop = terminalBody.scrollHeight;
            }
        }, 600);
    }

    // 停止加载动画
    stopLoadingAnimation() {
        if (this.loadingInterval) {
            clearInterval(this.loadingInterval);
            this.loadingInterval = null;
        }
        
        // 重置终端内容
        const terminalBody = document.getElementById('loadingTerminalBody');
        if (terminalBody) {
            terminalBody.innerHTML = `
                <div class="terminal-line">
                    <span class="terminal-prompt">猫娘@系统:~$</span>
                    <span class="terminal-text">正在初始化猫娘系统喵～</span>
                </div>
                <div class="terminal-line">
                    <span class="terminal-prompt">猫娘@系统:~$</span>
                    <span class="terminal-text loading-dots">加载中<span class="dots">...</span></span>
                </div>
            `;
        }
    }

    // 显示消息提示
    showMessage(message, type = 'info') {
        const toast = document.getElementById('messageToast');
        toast.textContent = message;
        toast.className = `message-toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // 搜索小说
    async searchNovels() {
        const keyword = document.getElementById('searchInput').value.trim();
        if (!keyword) {
            this.showMessage('请输入搜索关键词喵～', 'error');
            return;
        }

        this.showLoading('search');
        
        try {
            // 代理配置已移除
            const requestData = { keyword };
            
            const response = await fetch('/api/novel/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            
            if (data.success) {
                this.displaySearchResults(data.data);
                this.showMessage(`找到 ${data.data.length} 本小说喵～`, 'success');
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('搜索失败了喵～请检查网络连接', 'error');
            console.error('搜索错误:', error);
        } finally {
            this.hideLoading();
        }
    }

    // 显示搜索结果
    displaySearchResults(results) {
        const resultsContainer = document.getElementById('searchResults');
        const resultsSection = document.getElementById('resultsSection');
        
        resultsContainer.innerHTML = '';
        
        results.forEach(novel => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.innerHTML = `
                <img src="${novel.cover_url || '/static/images/default-cover.svg'}" alt="封面" class="novel-cover" onerror="this.src='/static/images/default-cover.svg'">
                <div class="result-content">
                    <div class="result-title">${this.escapeHtml(novel.title)}</div>
                    <div class="result-author">作者: ${this.escapeHtml(novel.author)}</div>
                    <div class="result-desc">${this.escapeHtml(novel.intro || novel.description || '暂无简介')}</div>
                </div>
            `;
            
            card.addEventListener('click', () => {
                this.selectNovel(novel.url);
            });
            
            resultsContainer.appendChild(card);
        });
        
        resultsSection.style.display = 'block';
        
        // 平滑滚动到结果区域
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 选择小说
    async selectNovel(novelUrl) {
        this.currentNovelUrl = novelUrl;
        this.showLoading('download');
        
        try {
            // 代理配置已移除
            const requestData = { url: novelUrl };
            
            const response = await fetch('/api/novel/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayNovelDetail(data.data, data.data.chapter_count);
                this.showMessage('小说信息加载完成喵～', 'success');
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('获取小说信息失败喵～', 'error');
            console.error('获取小说信息错误:', error);
        } finally {
            this.hideLoading();
        }
    }

    // 显示小说详情
    displayNovelDetail(novelInfo, chapterCount) {
        const detailContainer = document.getElementById('novelDetail');
        const detailSection = document.getElementById('novelDetailSection');
        const downloadSection = document.getElementById('downloadSection');
        
        detailContainer.innerHTML = `
            <div class="novel-info">
                <img src="${novelInfo.cover_url || novelInfo.cover || '/static/images/default-cover.svg'}" alt="封面" class="novel-cover" onerror="this.src='/static/images/default-cover.svg'">
                <div class="novel-meta">
                    <h3>${this.escapeHtml(novelInfo.title)}</h3>
                    <p><strong>作者:</strong> ${this.escapeHtml(novelInfo.author)}</p>
                    <p><strong>状态:</strong> ${this.escapeHtml(novelInfo.status || '未知')}</p>
                    <p><strong>字数:</strong> ${this.escapeHtml(novelInfo.word_count || '未知')}</p>
                    <p><strong>章节数:</strong> ${chapterCount} 章</p>
                    <p><strong>最后更新:</strong> ${this.escapeHtml(novelInfo.last_update || '未知')}</p>
                    <p><strong>简介:</strong></p>
                    <p style="margin-top: 10px; line-height: 1.6;">${this.escapeHtml(novelInfo.intro || novelInfo.description || '暂无简介')}</p>
                </div>
            </div>
        `;
        
        // 设置章节范围
        const endChapterInput = document.getElementById('endChapter');
        endChapterInput.max = chapterCount;
        endChapterInput.placeholder = `最大 ${chapterCount} 章`;
        
        detailSection.style.display = 'block';
        downloadSection.style.display = 'block';
        
        // 平滑滚动到详情区域
        detailSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 开始下载
    async startDownload() {
        if (!this.currentNovelUrl) {
            this.showMessage('请先选择要下载的小说喵～', 'error');
            return;
        }

        const startChapter = parseInt(document.getElementById('startChapter').value) || 1;
        const endChapterValue = document.getElementById('endChapter').value;
        const endChapter = endChapterValue ? parseInt(endChapterValue) : null;

        if (startChapter < 1) {
            this.showMessage('起始章节不能小于1喵～', 'error');
            return;
        }

        if (endChapter && endChapter < startChapter) {
            this.showMessage('结束章节不能小于起始章节喵～', 'error');
            return;
        }

        this.showLoading();
        
        try {
            // 代理配置已移除
            const requestData = { url: this.currentNovelUrl };
            
            const response = await fetch('/api/novel/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            
            if (data.success) {
                // 显示下载链接
                this.showDownloadLink(data.data);
                this.showMessage('小说下载完成喵～', 'success');
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('启动下载失败喵～', 'error');
            console.error('下载错误:', error);
        } finally {
            this.hideLoading();
        }
    }

    // 显示下载链接
    showDownloadLink(downloadData) {
        // 创建下载链接按钮并显示在页面上
        const downloadSection = document.getElementById('downloadSection');
        const linkContainer = document.createElement('div');
        linkContainer.className = 'download-result';
        linkContainer.innerHTML = `
            <div class="download-success">
                <h3>✓ 下载完成喵～</h3>
                <p>《${downloadData.title}》已成功下载</p>
                <button class="download-file-btn" onclick="novelDownloader.downloadFile('${downloadData.filename}')">
                    <i class="fas fa-download"></i>
                    下载EPUB文件
                </button>
            </div>
        `;
        downloadSection.appendChild(linkContainer);
        linkContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // 加载已下载的小说列表
    async loadDownloadedNovels() {
        try {
            const response = await fetch('/api/downloaded-novels');
            const data = await response.json();
            
            if (data.success) {
                this.renderDownloadedNovels(data.novels);
            } else {
                console.error('获取已下载小说列表失败:', data.message);
            }
        } catch (error) {
            console.error('加载已下载小说列表出错:', error);
        }
    }

    // 渲染已下载小说列表
    renderDownloadedNovels(novels) {
        const grid = document.querySelector('.downloaded-novels-grid');
        
        if (novels.length === 0) {
            grid.innerHTML = `
                <div class="no-novels">
                    <i class="fas fa-book-open"></i>
                    <p>还没有下载任何小说喵～</p>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = novels.map(novel => `
            <div class="novel-item">
                <div class="novel-cover">
                    <i class="fas fa-book"></i>
                </div>
                <div class="novel-info">
                    <h3 class="novel-title">${this.escapeHtml(novel.title)}</h3>
                    <p class="novel-format">EPUB格式</p>
                    <a href="/uploads/${encodeURIComponent(novel.filename)}" class="download-link-btn" download>
                        <i class="fas fa-download"></i>
                        下载
                    </a>
                </div>
            </div>
        `).join('');
    }

    // HTML转义
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    novelDownloaderInstance = new NovelDownloader();
});

// 添加一些实用的工具函数
window.novelDownloader = {
    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // 格式化时间
    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    },
    
    // 下载文件
    downloadFile(filename) {
        try {
            // 创建一个隐藏的a标签来触发下载
            const link = document.createElement('a');
            link.href = `/uploads/${encodeURIComponent(filename)}`;
            link.download = filename;
            link.style.display = 'none';
            
            // 添加到DOM，点击，然后移除
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            console.log(`开始下载文件: ${filename}`);
        } catch (error) {
            console.error('下载文件失败:', error);
            alert('下载失败，请重试喵～');
        }
    }
};

// 添加一些可爱的交互效果
document.addEventListener('DOMContentLoaded', () => {
    // 为按钮添加点击波纹效果
    const buttons = document.querySelectorAll('button, .result-card');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // 添加CSS动画
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

});

// 全局实例
let novelDownloaderInstance = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    novelDownloaderInstance = new NovelDownloader();
});