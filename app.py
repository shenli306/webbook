from flask import Flask, render_template, request, jsonify, send_file
from qishu_spider import QishuSpider
import os
import threading
import time
from datetime import datetime

app = Flask(__name__)

# 全局变量存储下载状态
download_status = {}
download_threads = {}

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_novel():
    """搜索小说"""
    try:
        keyword = request.json.get('keyword', '').strip()
        if not keyword:
            return jsonify({'success': False, 'message': '请输入搜索关键词喵～'})
        
        spider = QishuSpider()
        results = spider.search_novels(keyword)
        
        if not results:
            return jsonify({'success': False, 'message': '没有找到相关小说喵～'})
        
        return jsonify({
            'success': True,
            'results': results  # 返回所有搜索结果
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'搜索出错了喵: {str(e)}'})

@app.route('/novel_info', methods=['POST'])
def get_novel_info():
    """获取小说详细信息"""
    try:
        novel_url = request.json.get('url', '').strip()
        if not novel_url:
            return jsonify({'success': False, 'message': '小说链接不能为空喵～'})
        
        spider = QishuSpider()
        novel_info = spider.get_novel_info(novel_url)
        chapter_list = spider.get_chapter_list(novel_url)
        
        return jsonify({
            'success': True,
            'novel_info': novel_info,
            'chapter_count': len(chapter_list)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取小说信息出错了喵: {str(e)}'})

@app.route('/download', methods=['POST'])
def download_novel():
    """开始下载小说"""
    try:
        data = request.json
        novel_url = data.get('url', '').strip()
        start_chapter = int(data.get('start_chapter', 1))
        end_chapter = data.get('end_chapter')
        
        if not novel_url:
            return jsonify({'success': False, 'message': '小说链接不能为空喵～'})
        
        # 生成下载任务ID
        task_id = f"task_{int(time.time())}"
        
        # 初始化下载状态
        download_status[task_id] = {
            'status': 'starting',
            'progress': 0,
            'message': '正在准备下载喵～',
            'start_time': datetime.now(),
            'filename': None
        }
        
        # 启动下载线程
        thread = threading.Thread(
            target=download_worker,
            args=(task_id, novel_url, start_chapter, end_chapter)
        )
        thread.daemon = True
        thread.start()
        
        download_threads[task_id] = thread
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '下载任务已启动喵～'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动下载失败喵: {str(e)}'})

def download_worker(task_id, novel_url, start_chapter, end_chapter):
    """下载工作线程"""
    try:
        spider = QishuSpider()
        
        # 更新状态：获取小说信息
        download_status[task_id].update({
            'status': 'getting_info',
            'progress': 10,
            'message': '正在获取小说信息喵～'
        })
        
        novel_info = spider.get_novel_info(novel_url)
        chapter_list = spider.get_chapter_list(novel_url)
        
        # 处理章节范围
        if end_chapter is None or end_chapter > len(chapter_list):
            end_chapter = len(chapter_list)
        
        selected_chapters = chapter_list[start_chapter-1:end_chapter]
        
        # 更新状态：开始下载章节
        download_status[task_id].update({
            'status': 'downloading',
            'progress': 20,
            'message': f'开始下载 {len(selected_chapters)} 个章节喵～'
        })
        
        # 下载章节内容
        chapters_data = []
        for i, chapter in enumerate(selected_chapters):
            try:
                content = spider.get_chapter_content(chapter['url'])
                chapters_data.append({
                    'title': chapter['title'],
                    'content': content
                })
                
                # 更新进度
                progress = 20 + int((i + 1) / len(selected_chapters) * 60)
                download_status[task_id].update({
                    'progress': progress,
                    'message': f'已下载 {i+1}/{len(selected_chapters)} 章节喵～'
                })
                
            except Exception as e:
                print(f"下载章节失败: {chapter['title']} - {e}")
                continue
        
        # 更新状态：生成EPUB
        download_status[task_id].update({
            'status': 'generating',
            'progress': 85,
            'message': '正在生成EPUB文件喵～'
        })
        
        # 生成文件名
        safe_title = "".join(c for c in novel_info['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}.epub"
        
        # 创建EPUB
        spider.create_epub(novel_info, chapters_data, filename)
        
        # 完成
        download_status[task_id].update({
            'status': 'completed',
            'progress': 100,
            'message': f'下载完成喵～共 {len(chapters_data)} 章节',
            'filename': filename,
            'end_time': datetime.now()
        })
        
    except Exception as e:
        download_status[task_id].update({
            'status': 'error',
            'progress': 0,
            'message': f'下载失败喵: {str(e)}',
            'end_time': datetime.now()
        })

@app.route('/status/<task_id>')
def get_download_status(task_id):
    """获取下载状态"""
    if task_id not in download_status:
        return jsonify({'success': False, 'message': '任务不存在喵～'})
    
    status = download_status[task_id].copy()
    
    # 转换时间格式
    if 'start_time' in status:
        status['start_time'] = status['start_time'].strftime('%Y-%m-%d %H:%M:%S')
    if 'end_time' in status:
        status['end_time'] = status['end_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'success': True, 'data': status})

@app.route('/download_file/<filename>')
def download_file(filename):
    """下载生成的EPUB文件"""
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在喵～'})
        
        # 使用send_file并设置正确的响应头
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/epub+zip'
        )
        
        # 添加额外的响应头确保浏览器下载
        # 处理中文文件名编码问题
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
        response.headers['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'\'{encoded_filename}'
        response.headers['Content-Type'] = 'application/epub+zip'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载文件失败喵: {str(e)}'})

if __name__ == '__main__':
    # 创建templates目录
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("🐱 猫娘小说下载器启动中喵～")
    print("📚 访问 http://localhost:5000 开始使用喵～")
    app.run(debug=True, host='0.0.0.0', port=5000)