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
    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }

    // 隐藏加载动画
    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
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

        this.showLoading();
        
        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ keyword })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displaySearchResults(data.results);
                this.showMessage(`找到 ${data.results.length} 本小说喵～`, 'success');
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
        this.showLoading();
        
        try {
            const response = await fetch('/novel_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: novelUrl })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayNovelDetail(data.novel_info, data.chapter_count);
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
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: this.currentNovelUrl,
                    start_chapter: startChapter,
                    end_chapter: endChapter
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentTaskId = data.task_id;
                this.showDownloadProgress();
                this.startProgressMonitoring();
                this.showMessage('下载任务已启动喵～', 'success');
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

    // 显示下载进度区域
    showDownloadProgress() {
        const progressSection = document.getElementById('progressSection');
        progressSection.style.display = 'block';
        
        // 重置进度
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('progressText').textContent = '0%';
        document.getElementById('progressMessage').textContent = '准备中...';
        document.getElementById('downloadLink').style.display = 'none';
        
        // 平滑滚动到进度区域
        progressSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 开始监控下载进度
    startProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.progressInterval = setInterval(() => {
            this.checkDownloadProgress();
        }, 1000);
    }

    // 检查下载进度
    async checkDownloadProgress() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/status/${this.currentTaskId}`);
            const data = await response.json();
            
            if (data.success) {
                this.updateProgress(data.data);
                
                // 如果下载完成或出错，停止监控
                if (data.data.status === 'completed' || data.data.status === 'error') {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                }
            }
        } catch (error) {
            console.error('获取进度失败:', error);
        }
    }

    // 更新进度显示
    updateProgress(progressData) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const progressMessage = document.getElementById('progressMessage');
        const downloadLink = document.getElementById('downloadLink');
        
        progressFill.style.width = `${progressData.progress}%`;
        progressText.textContent = `${progressData.progress}%`;
        progressMessage.textContent = progressData.message;
        
        if (progressData.status === 'completed' && progressData.filename) {
            downloadLink.innerHTML = `
                <button class="download-file-btn" onclick="novelDownloader.downloadFile('${progressData.filename}')">
                    <i class="fas fa-download"></i>
                    下载EPUB文件
                </button>
            `;
            downloadLink.style.display = 'block';
            this.showMessage('下载完成喵～可以下载文件了！', 'success');
        } else if (progressData.status === 'error') {
            this.showMessage(progressData.message, 'error');
        }
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
    new NovelDownloader();
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
            link.href = `/download_file/${encodeURIComponent(filename)}`;
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