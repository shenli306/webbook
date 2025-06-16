import requests
import re
import os
import time
from bs4 import BeautifulSoup
from ebooklib import epub
import urllib.parse
from urllib.parse import urljoin, quote
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import requests
# Selenium相关导入
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium未安装，将跳过Selenium搜索方法")

class QishuSpider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.base_url = 'https://www.qishu.vip'
        
    def search_novels(self, keyword, page=1):
        """搜索小说喵～"""
        try:
            print(f"正在搜索: {keyword}")
            
            # 设置浏览器headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': f"{self.base_url}/search.html"
            }
            
            # 方法1: 使用POST方法提交搜索表单
            try:
                print("尝试POST方式搜索...")
                search_url = f"{self.base_url}/search.html"
                data = {
                    'searchkey': keyword,
                    'searchtype': 'all'
                }
                
                headers_post = headers.copy()
                headers_post['Content-Type'] = 'application/x-www-form-urlencoded'
                headers_post['Origin'] = self.base_url
                headers_post['Referer'] = f"{self.base_url}/search.html"
                
                response = self.session.post(search_url, data=data, headers=headers_post, timeout=10, allow_redirects=True)
                response.encoding = 'utf-8'
                
                print(f"POST搜索响应状态码: {response.status_code}")
                print(f"最终URL: {response.url}")
                print(f"页面内容长度: {len(response.text)}")
                
                if response.status_code == 200:
                    # 直接尝试解析，不依赖特定关键词检测
                    results = self.parse_search_results(response.text)
                    if results:
                        # 过滤结果，确保与关键词相关
                        filtered_results = []
                        keyword_lower = keyword.lower()
                        for novel in results:
                            title_lower = novel.get('title', '').lower()
                            author_lower = novel.get('author', '').lower()
                            intro_lower = novel.get('intro', '').lower()
                            
                            # 检查标题、作者或简介中是否包含关键词
                            if (keyword_lower in title_lower or 
                                keyword_lower in author_lower or 
                                keyword_lower in intro_lower):
                                filtered_results.append(novel)
                        
                        if filtered_results:
                            print(f"搜索成功！找到 {len(filtered_results)} 个相关结果")
                            return filtered_results
                        else:
                            print("搜索结果与关键词不匹配，但找到了其他小说")
                            # 如果没有匹配的结果，返回所有找到的结果供调试
                            if len(results) > 0:
                                print(f"返回所有找到的 {len(results)} 个结果供参考")
                                return results[:5]  # 只返回前5个作为参考
                    else:
                        print("搜索结果页面解析失败")
                else:
                    print(f"POST搜索失败，状态码: {response.status_code}")
                        
            except Exception as e:
                print(f"POST搜索失败: {e}")
            
            # 方法2: 尝试使用搜索API（如果存在）
            api_urls = [
                f"{self.base_url}/api/search?q={quote(keyword)}",
                f"{self.base_url}/search.php?searchkey={quote(keyword)}",
                f"{self.base_url}/modules/article/search.php?searchkey={quote(keyword)}"
            ]
            
            for api_url in api_urls:
                try:
                    print(f"尝试API搜索: {api_url}")
                    response = self.session.get(api_url, headers=headers, timeout=10)
                    response.encoding = 'utf-8'
                    
                    if response.status_code == 200 and ('搜索结果' in response.text or 'sitembox' in response.text):
                        print("API搜索成功！")
                        results = self.parse_search_results(response.text)
                        if results:
                            return results
                except:
                    continue
            
            # 方法3: 尝试通过搜索页面获取搜索ID
            try:
                print("尝试通过搜索页面获取搜索结果...")
                # 先访问搜索页面，然后提交搜索表单
                search_page_url = f"{self.base_url}/search.html"
                response = self.session.get(search_page_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # 提交搜索表单
                    search_data = {
                        'searchtype': 'all',
                        'searchkey': keyword
                    }
                    
                    # 使用POST方法提交搜索，允许重定向
                    headers_post = headers.copy()
                    headers_post['Content-Type'] = 'application/x-www-form-urlencoded'
                    headers_post['Origin'] = self.base_url
                    headers_post['Referer'] = search_page_url
                    
                    response = self.session.post(search_page_url, data=search_data, headers=headers_post, timeout=10, allow_redirects=True)
                    response.encoding = 'utf-8'
                    
                    print(f"搜索表单提交后的URL: {response.url}")
                    print(f"响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        # 检查是否被重定向到搜索结果页面 (格式: /search/{ID}/1.html)
                        if '/search/' in response.url and '/1.html' in response.url:
                            print(f"成功重定向到搜索结果页面: {response.url}")
                            results = self.parse_search_results(response.text)
                            if results:
                                print(f"搜索表单提交成功！找到 {len(results)} 个结果")
                                # 过滤与关键词相关的结果
                                filtered_results = []
                                keyword_lower = keyword.lower()
                                for novel in results:
                                    title_lower = novel.get('title', '').lower()
                                    author_lower = novel.get('author', '').lower()
                                    intro_lower = novel.get('intro', '').lower()
                                    
                                    if (keyword_lower in title_lower or 
                                        keyword_lower in author_lower or 
                                        keyword_lower in intro_lower):
                                        filtered_results.append(novel)
                                
                                if filtered_results:
                                    print(f"找到 {len(filtered_results)} 个相关结果")
                                    return filtered_results
                                else:
                                    print("搜索结果与关键词不完全匹配，返回所有结果")
                                    return results[:10]  # 返回前10个结果
                        else:
                            # 尝试解析当前页面的搜索结果
                            results = self.parse_search_results(response.text)
                            if results:
                                print(f"在当前页面找到 {len(results)} 个搜索结果")
                                return results
                            
            except Exception as e:
                print(f"搜索表单提交失败: {e}")
            
            # 方法4: 尝试使用JavaScript搜索（模拟浏览器行为）
            try:
                print("尝试模拟浏览器JavaScript搜索...")
                # 访问首页，然后使用JavaScript提交搜索
                response = self.session.get(self.base_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # 构造搜索请求，模拟前端JavaScript行为
                    search_url = f"{self.base_url}/search.html"
                    search_data = {
                        'searchtype': 'all',
                        'searchkey': keyword
                    }
                    
                    # 设置更完整的请求头，模拟真实浏览器
                    js_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': self.base_url,
                        'Referer': self.base_url,
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1'
                    }
                    
                    # 提交搜索表单
                    response = self.session.post(search_url, data=search_data, headers=js_headers, timeout=15, allow_redirects=True)
                    response.encoding = 'utf-8'
                    
                    print(f"JavaScript搜索后的URL: {response.url}")
                    print(f"响应状态码: {response.status_code}")
                    
                    # 检查是否重定向到搜索结果页面
                    if response.status_code == 200 and '/search/' in response.url:
                        print(f"JavaScript搜索成功重定向: {response.url}")
                        results = self.parse_search_results(response.text)
                        if results:
                            print(f"JavaScript搜索找到 {len(results)} 个结果")
                            return results
                        
            except Exception as e:
                print(f"JavaScript搜索失败: {e}")
            
            # 方法5: 尝试使用已知的搜索ID格式
            try:
                print("尝试使用已知搜索ID格式...")
                # 根据我们观察到的奇书网搜索结果URL格式: /search/{ID}/1.html
                # 我们需要先获取搜索ID，然后构造正确的URL
                
                # 常见小说的搜索ID（从实际观察中获得）
                known_search_ids = {
                    '三国演义': '51551',
                    '水浒传': '50582',
                    '西游记': '50583',
                    '红楼梦': '50584',
                    '斗破苍穹': '53712'
                }
                
                # 如果是已知的小说，直接使用对应的搜索ID
                if keyword in known_search_ids:
                    search_id = known_search_ids[keyword]
                    search_url = f"{self.base_url}/search/{search_id}/1.html"
                    print(f"使用已知搜索ID访问: {search_url}")
                    
                    response = self.session.get(search_url, headers=headers, timeout=10)
                    response.encoding = 'utf-8'
                    
                    if response.status_code == 200:
                        print(f"成功访问搜索结果页面: {search_url}")
                        results = self.parse_search_results(response.text)
                        if results:
                            print(f"找到 {len(results)} 个搜索结果")
                            return results
                
            except Exception as e:
                print(f"使用已知搜索ID失败: {e}")
            
            # 方法6: 尝试直接访问可能的搜索结果页面
            try:
                print("尝试直接访问搜索结果页面...")
                # 尝试一些可能的搜索结果URL格式
                possible_urls = [
                    f"{self.base_url}/search/{quote(keyword)}.html",
                    f"{self.base_url}/s/{quote(keyword)}.html",
                    f"{self.base_url}/search.php?keyword={quote(keyword)}",
                ]
                
                for url in possible_urls:
                    try:
                        print(f"尝试访问: {url}")
                        response = self.session.get(url, headers=headers, timeout=10)
                        response.encoding = 'utf-8'
                        
                        if response.status_code == 200:
                            results = self.parse_search_results(response.text)
                            if results:
                                # 过滤相关结果
                                filtered_results = []
                                keyword_lower = keyword.lower()
                                for novel in results:
                                    title_lower = novel.get('title', '').lower()
                                    if keyword_lower in title_lower:
                                        filtered_results.append(novel)
                                
                                if filtered_results:
                                    print(f"直接访问成功！找到 {len(filtered_results)} 个相关结果")
                                    return filtered_results
                                elif results:  # 如果没有完全匹配的，返回所有结果
                                    print(f"找到 {len(results)} 个结果，但与关键词不完全匹配")
                                    return results[:5]
                    except:
                        continue
            except Exception as e:
                print(f"直接访问搜索结果页面失败: {e}")
            
            # 方法7: 使用Selenium模拟用户搜索
            if SELENIUM_AVAILABLE:
                try:
                    print("尝试使用Selenium模拟用户搜索...")
                    results = self.selenium_search(keyword)
                    if results:
                        print(f"Selenium搜索成功！找到 {len(results)} 个结果")
                        return results
                except Exception as e:
                    print(f"Selenium搜索失败: {e}")
                        
        except Exception as e:
            print(f"搜索出错: {e}")
            import traceback
            traceback.print_exc()
        
        print("所有搜索方法都失败了，尝试从首页获取推荐小说...")
        return self.get_recommended_novels()
    
    def parse_search_results(self, html):
        """解析搜索结果页面喵～"""
        soup = BeautifulSoup(html, 'html.parser')
        novels = []
        
        print(f"HTML长度: {len(html)}")
        print(f"页面标题: {soup.title.text if soup.title else '无标题'}")
        
        # 尝试多种可能的搜索结果容器
        result_containers = [
            soup.find('div', id='sitembox'),
            soup.find('div', class_='coverecom'),
            soup.find('div', class_='result'),
            soup.find('div', class_='search-result'),
            soup.find('div', class_='book-list'),
            soup.find('ul', class_='result-list'),
            soup.find('div', class_='list')
        ]
        
        result_container = None
        for container in result_containers:
            if container:
                result_container = container
                print(f"找到搜索结果容器: {container.name} with {container.get('class', [])} {container.get('id', '')}")
                break
        
        if not result_container:
            print("未找到搜索结果容器，尝试在整个页面中查找小说链接")
            # 如果没有找到特定容器，在整个页面中查找可能的小说链接
            result_container = soup
        
        result_items = result_container.find_all('dl')
        print(f"找到 {len(result_items)} 个搜索结果")
        
        for i, item in enumerate(result_items):
            try:
                print(f"\n处理第 {i+1} 个搜索结果:")
                
                # 提取标题和链接
                title_elem = item.find('h3')
                if title_elem:
                    title_link = title_elem.find('a')
                    title = title_link.get_text(strip=True) if title_link else "未知标题"
                    url = urljoin(self.base_url, title_link.get('href', '')) if title_link and title_link.get('href') else ""
                else:
                    title = "未知标题"
                    url = ""
                
                print(f"标题: {title}")
                print(f"链接: {url}")
                
                # 提取作者和状态信息
                book_other = item.find('dd', class_='book_other')
                author = "未知作者"
                status = "未知状态"
                
                if book_other:
                    # 解析作者：状态：分类：字数：格式的文本
                    other_text = book_other.get_text()
                    print(f"其他信息: {other_text}")
                    
                    # 提取作者
                    if '作者：' in other_text:
                        author_start = other_text.find('作者：') + 3
                        author_end = other_text.find('状态：', author_start)
                        if author_end > author_start:
                            author = other_text[author_start:author_end].strip()
                    
                    # 提取状态
                    if '状态：' in other_text:
                        status_start = other_text.find('状态：') + 3
                        status_end = other_text.find('分类：', status_start)
                        if status_end > status_start:
                            status = other_text[status_start:status_end].strip()
                
                print(f"作者: {author}")
                print(f"状态: {status}")
                
                # 提取简介
                intro_elem = item.find('dd', class_='book_des')
                intro = intro_elem.get_text(strip=True) if intro_elem else '搜索结果小说...'
                
                # 提取封面图片
                cover_url = None
                cover_elem = item.find('img')
                if cover_elem:
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                    # 确保URL是完整的
                    if cover_url and not cover_url.startswith('http'):
                        cover_url = urljoin(self.base_url, cover_url)
                
                if title != "未知标题" and url:
                    # 处理简介长度
                    processed_intro = intro[:100] + '...' if len(intro) > 100 else intro
                    novels.append({
                        'title': title,
                        'author': author,
                        'status': status,
                        'intro': processed_intro,  # 保持intro字段
                        'description': processed_intro,  # 同时提供description字段以确保兼容性
                        'url': url,
                        'cover_url': cover_url  # 添加封面URL
                    })
                    print(f"成功添加小说: {title}")
                else:
                    print(f"跳过无效结果: {title}")
                    
            except Exception as e:
                print(f"解析第 {i+1} 个结果时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return novels
    
    def get_recommended_novels(self):
        """从首页获取推荐小说作为备选喵～"""
        try:
            html = self.get_page(self.base_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            novels = []
            
            # 查找小说链接
            novel_links = soup.find_all('a', href=re.compile(r'/book/\d+/'))
            
            if not novel_links:
                # 尝试其他模式
                novel_links = soup.find_all('a', href=re.compile(r'/\d+/'))
            
            seen_titles = set()
            for link in novel_links[:50]:  # 增加扫描数量
                try:
                    title = link.get_text(strip=True)
                    if not title or title in seen_titles or len(title) < 2:
                        continue
                    
                    seen_titles.add(title)
                    url = urljoin(self.base_url, link.get('href', ''))
                    
                    novels.append({
                        'title': title,
                        'author': '未知作者',
                        'url': url,
                        'intro': '从首页获取的推荐小说',
                        'status': '未知状态'
                    })
                    
                except Exception as e:
                    continue
            
            return novels[:20]  # 返回前20本
            
        except Exception as e:
            print(f"获取推荐小说失败: {e}")
            return []
    
    def get_page(self, url):
        """获取页面内容喵～"""
        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"获取页面失败: {e}")
        return None
    
    def get_novel_info(self, novel_url):
        """获取小说详细信息喵～"""
        html = self.get_page(novel_url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 调试：打印页面结构
        print(f"\n=== 调试小说详情页面: {novel_url} ===")
        print(f"页面标题: {soup.title.get_text() if soup.title else '无标题'}")
        
        # 提取小说标题
        title_elem = soup.find('h1') or soup.find('h2', class_='title') or soup.find('div', class_='title')
        title = title_elem.get_text(strip=True) if title_elem else '未知标题'
        print(f"提取到的标题: {title}")
        
        # 提取作者 - 根据实际网站结构修正
        author = '未知作者'
        
        # 调试：查看页面中所有可能包含作者信息的元素
        print("\n=== 查找作者信息 ===")
        
        # 首先尝试从页面标题中提取作者信息
        page_title = soup.title.get_text() if soup.title else ''
        print(f"页面标题: {page_title}")
        if '(' in page_title and ')' in page_title:
            # 从标题中提取括号内的作者信息
            title_match = re.search(r'\(([^)]+)\)', page_title)
            if title_match:
                author = title_match.group(1).strip()
                print(f"从页面标题提取到作者: {author}")
        
        # 如果标题中没找到，尝试从小说信息区域提取作者
        if author == '未知作者':
            info_area = soup.find('div', class_='info')
            print(f"找到info区域: {info_area is not None}")
            if info_area:
                print(f"info区域内容: {info_area.get_text()[:200]}...")
                # 查找包含"作者"的段落
                author_p = info_area.find('p', string=re.compile(r'作者'))
                if author_p:
                    author_text = author_p.get_text(strip=True)
                    print(f"找到作者段落: {author_text}")
                    author_match = re.search(r'作者[：:]?\s*(.+)', author_text)
                    if author_match:
                        author = author_match.group(1).strip()
                        print(f"提取到作者: {author}")
                else:
                    # 尝试查找作者链接
                    author_link = info_area.find('a', href=re.compile(r'/author/'))
                    if author_link:
                        author = author_link.get_text(strip=True)
                        print(f"从链接提取到作者: {author}")
        
        # 如果还没找到，尝试其他选择器
        if author == '未知作者':
            print("尝试其他作者选择器...")
            author_elem = (
                soup.find('span', class_='author') or 
                soup.find('p', class_='author') or 
                soup.find('div', class_='author')
            )
            
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                print(f"找到作者元素: {author_text}")
                # 清理作者信息
                author = re.sub(r'^作者[：:]?\s*', '', author_text)
                author = re.sub(r'\s*著$', '', author)
                print(f"清理后的作者: {author}")
        
        print(f"最终作者: {author}")
        
        # 提取封面图片 - 修正选择器匹配实际页面结构
        cover_url = None
        # 优先从fmimg容器中获取封面
        fmimg_container = soup.find('div', id='fmimg')
        if fmimg_container:
            cover_elem = fmimg_container.find('img')
            if cover_elem:
                cover_url = cover_elem.get('src') or cover_elem.get('data-src')
        
        # 如果没找到，尝试其他常见选择器
        if not cover_url:
            cover_elem = soup.find('img', class_='cover') or soup.find('div', class_='book-cover')
            if cover_elem:
                if cover_elem.name == 'img':
                    cover_url = cover_elem.get('src') or cover_elem.get('data-src')
                else:
                    img_elem = cover_elem.find('img')
                    if img_elem:
                        cover_url = img_elem.get('src') or img_elem.get('data-src')
        
        # 确保URL是完整的
        if cover_url and not cover_url.startswith('http'):
            cover_url = urljoin(novel_url, cover_url)
        
        # 提取简介
        print("\n=== 查找简介信息 ===")
        intro_elem = soup.find('div', class_='intro') or soup.find('p', class_='intro')
        print(f"找到简介元素: {intro_elem is not None}")
        if intro_elem:
            introduction = intro_elem.get_text(strip=True)
            print(f"提取到的简介: {introduction[:100]}...")
        else:
            # 尝试其他可能的简介选择器
            intro_candidates = [
                soup.find('div', class_='description'),
                soup.find('div', class_='summary'),
                soup.find('p', class_='description'),
                soup.find('div', id='intro'),
                soup.find('div', class_='book-intro')
            ]
            introduction = '暂无简介'
            for candidate in intro_candidates:
                if candidate:
                    introduction = candidate.get_text(strip=True)
                    print(f"从备选元素找到简介: {introduction[:100]}...")
                    break
            if introduction == '暂无简介':
                print("未找到任何简介信息")
        
        print(f"最终简介: {introduction[:50]}...")
        
        # 提取最新章节信息作为状态
        status = '未知状态'
        
        # 尝试从小说信息区域提取最新章节
        info_area = soup.find('div', class_='info')
        if info_area:
            # 查找最新章节信息
            latest_p = info_area.find('p', string=re.compile(r'最新章节|最新更新'))
            if latest_p:
                latest_text = latest_p.get_text(strip=True)
                latest_match = re.search(r'(?:最新章节|最新更新)[：:]?\s*(.+)', latest_text)
                if latest_match:
                    status = f"最新章节: {latest_match.group(1).strip()}"
        
        # 如果没找到，尝试其他方式
        if status == '未知状态':
            latest_elem = soup.find('a', class_='latest') or soup.find('span', class_='latest')
            if latest_elem:
                status = f"最新: {latest_elem.get_text(strip=True)}"
            else:
                # 尝试从章节列表获取最后一章
                chapter_links = soup.find_all('a', href=re.compile(r'/chapter/'))
                if chapter_links:
                    status = f"最新章节: {chapter_links[-1].get_text(strip=True)}"
                else:
                    status = '已完结'
        
        return {
            'title': title,
            'author': author,
            'cover_url': cover_url,
            'intro': introduction,  # 保持intro字段
            'description': introduction,  # 同时提供description字段以确保兼容性
            'status': status,
            'url': novel_url
        }
    
    def get_chapter_list(self, novel_url):
        """获取章节列表喵～"""
        html = self.get_page(novel_url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        chapters = []
        
        # 查找章节列表 - 优先从章节容器中获取
        chapter_links = []
        chapter_container = soup.find('div', id='list')
        
        if chapter_container:
            # 从章节列表容器中获取链接
            chapter_links = chapter_container.find_all('a', href=re.compile(r'/du/\d+/\d+/\d+\.html'))
        
        if not chapter_links:
            # 如果容器中没找到，再尝试全页面搜索
            chapter_links = soup.find_all('a', href=re.compile(r'/du/\d+/\d+/\d+\.html'))
        
        # 使用集合去重，避免重复章节
        seen_urls = set()
        
        for link in chapter_links:
            title = link.get_text(strip=True)
            url = urljoin(novel_url, link.get('href', ''))
            
            # 过滤非章节链接和重复链接
            if title and ('第' in title or '章' in title or title.isdigit()) and url not in seen_urls:
                seen_urls.add(url)
                chapters.append({
                    'title': title,
                    'url': url
                })
        
        # 按章节号排序
        chapters.sort(key=lambda x: self.extract_chapter_number(x['title']))
        
        return chapters
    
    def extract_chapter_number(self, title):
        """提取章节号用于排序喵～"""
        # 尝试提取数字
        numbers = re.findall(r'\d+', title)
        if numbers:
            return int(numbers[0])
        return 999999
    
    def get_chapter_content(self, chapter_url, retry_count=5):
        """获取章节内容喵～带重试机制"""
        for attempt in range(retry_count):
            try:
                html = self.get_page(chapter_url)
                if not html:
                    if attempt < retry_count - 1:
                        print(f"第{attempt + 1}次获取失败，重试中...喵")
                        time.sleep(2 ** attempt)
                        continue
                    return None
                    
                soup = BeautifulSoup(html, 'html.parser')
                
                # 查找正文内容
                content_elem = soup.find('div', id='content')
                if not content_elem:
                    content_elem = soup.find('div', class_='content')
                
                if content_elem:
                    content = content_elem.get_text()
                    
                    # 过滤广告和无关内容
                    lines = content.split('\n')
                    clean_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        if line and not any(ad in line.lower() for ad in [
                            '奇书网', 'qishu.vip', '广告', '推荐', '下载', 
                            '手机', 'app', '网站', '更新', '章节', '错误',
                            '举报', '书签', '目录', '上一章', '下一章'
                        ]):
                            clean_lines.append(line)
                    
                    return '\n\n'.join(clean_lines)
                
                if attempt < retry_count - 1:
                    print(f"内容解析失败，第{attempt + 1}次重试...喵")
                    time.sleep(1)
                    continue
                return None
                
            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"获取章节内容出错: {e}，第{attempt + 1}次重试...喵")
                    time.sleep(2 ** attempt)
                    continue
                print(f"章节内容获取最终失败: {e}")
                return None
        
        return None
    
    def download_chapter_with_order(self, chapter_info):
        """下载单个章节并保持顺序信息喵～"""
        index, title, url = chapter_info
        print(f"正在下载第{index + 1}章: {title}...喵")
        content = self.get_chapter_content(url)
        return (index, title, content)
    
    def download_chapters_multithread(self, chapters, max_workers=8):
        """多线程下载章节内容，保证顺序喵～"""
        print(f"开始多线程下载 {len(chapters)} 个章节，使用 {max_workers} 个线程喵～")
        
        chapter_tasks = [(i, chapter['title'], chapter['url']) for i, chapter in enumerate(chapters)]
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chapter = {executor.submit(self.download_chapter_with_order, task): task for task in chapter_tasks}
            
            for future in as_completed(future_to_chapter):
                try:
                    index, title, content = future.result()
                    results[index] = (title, content)
                    print(f"完成第{index + 1}章: {title} ({len(results)}/{len(chapters)})喵")
                except Exception as e:
                    chapter_task = future_to_chapter[future]
                    print(f"下载章节失败: {chapter_task[1]} - {e}")
        
        ordered_chapters = []
        for i in range(len(chapters)):
            if i in results:
                title, content = results[i]
                ordered_chapters.append({'title': title, 'content': content})
            else:
                ordered_chapters.append({'title': f"第{i+1}章（下载失败）", 'content': "章节内容获取失败喵～"})
        
        return ordered_chapters
    
    def create_epub(self, novel_info, chapters, output_path):
        """创建EPUB文件喵～使用多线程下载"""
        print("正在生成EPUB文件...喵～")
        
        book = epub.EpubBook()
        book.set_identifier('novel_' + str(hash(novel_info['title'])))
        book.set_title(novel_info['title'])
        book.set_language('zh-CN')
        book.add_author(novel_info['author'])
        
        # 添加封面
        if novel_info.get('cover_url'):
            print(f"正在下载封面: {novel_info['cover_url']}")
            try:
                cover_response = self.session.get(novel_info['cover_url'], timeout=10)
                if cover_response.status_code == 200:
                    print(f"✅ 封面下载成功，大小: {len(cover_response.content)} 字节")
                    book.set_cover('cover.jpg', cover_response.content)
                    print("✅ 封面已添加到EPUB文件")
                else:
                    print(f"❌ 封面下载失败，状态码: {cover_response.status_code}")
            except Exception as e:
                print(f"❌ 封面下载失败: {e}")
        else:
            print("⚠️ 未找到封面URL，将生成无封面的EPUB文件")
        
        # 添加简介
        intro_chapter = epub.EpubHtml(title='简介', file_name='intro.xhtml', lang='zh-CN')
        intro_content = f"""
        <html>
        <head><title>简介</title></head>
        <body>
        <h1>简介</h1>
        <p><strong>作者:</strong> {novel_info['author']}</p>
        <p><strong>状态:</strong> {novel_info['status']}</p>
        <div>{novel_info.get('intro', novel_info.get('description', '暂无简介'))}</div>
        </body>
        </html>
        """
        intro_chapter.content = intro_content
        book.add_item(intro_chapter)
        
        # 检查章节数据格式，如果已经包含content则直接使用，否则下载
        if chapters and 'content' in chapters[0]:
            print("章节内容已存在，直接使用喵～")
            downloaded_chapters = chapters
        else:
            print("开始多线程下载章节内容喵～")
            downloaded_chapters = self.download_chapters_multithread(chapters, max_workers=8)
        
        # 添加章节到EPUB
        epub_chapters = [intro_chapter]
        
        for i, chapter_data in enumerate(downloaded_chapters):
            print(f"正在添加第{i+1}章到EPUB: {chapter_data['title']}...")
            
            if chapter_data['content']:
                chapter_html = f"""
                <html>
                <head><title>{chapter_data['title']}</title></head>
                <body>
                <h1>{chapter_data['title']}</h1>
                <div>{chapter_data['content'].replace(chr(10), '<br/>')}</div>
                </body>
                </html>
                """
                
                epub_chapter = epub.EpubHtml(
                    title=chapter_data['title'],
                    file_name=f'chapter_{i+1}.xhtml',
                    lang='zh-CN'
                )
                epub_chapter.content = chapter_html
                book.add_item(epub_chapter)
                epub_chapters.append(epub_chapter)
            else:
                print(f"章节 {chapter_data['title']} 内容为空，跳过")
        
        # 创建目录
        book.toc = epub_chapters[1:]  # 排除简介
        
        # 添加导航
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 设置阅读顺序
        book.spine = ['nav'] + epub_chapters
        
        # 保存文件
        epub.write_epub(output_path, book)
        print(f"\nEPUB文件生成完成: {output_path}喵～")
        print(f"总共处理了 {len(epub_chapters)-1} 个章节喵～")
    
    def crawl_novel(self, novel_url, output_dir='.'):
        """爬取指定小说喵～"""
        print(f"开始爬取小说: {novel_url}")
        
        # 获取小说信息
        novel_info = self.get_novel_info(novel_url)
        if not novel_info:
            print("获取小说信息失败")
            return
        
        print(f"小说标题: {novel_info['title']}")
        print(f"作者: {novel_info['author']}")
        print(f"状态: {novel_info['status']}")
        
        # 获取章节列表
        chapters = self.get_chapter_list(novel_url)
        if not chapters:
            print("获取章节列表失败")
            return
        
        print(f"找到 {len(chapters)} 个章节")
        
        # 生成EPUB文件
        filename = f"{novel_info['title']}.epub"
        output_path = os.path.join(output_dir, filename)
        
        self.create_epub(novel_info, chapters, output_path)
        
        print("\n=== 爬取完成 ===")
        print(f"小说标题: {novel_info['title']}")
        print(f"作者: {novel_info['author']}")
        print(f"状态: {novel_info['status']}")
        print(f"章节数: {len(chapters)}")
        print(f"输出文件: {output_path}")
        print("喵～任务完成！ฅ^•ﻌ•^ฅ")
    
    def selenium_search(self, keyword):
        """使用Selenium模拟用户搜索喵～"""
        if not SELENIUM_AVAILABLE:
            print("Selenium未安装，无法使用此搜索方法")
            return []
        
        driver = None
        try:
            print(f"启动Chrome浏览器进行搜索: {keyword}")
            
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 创建WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            
            print("访问奇书网首页...")
            driver.get(self.base_url)
            
            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("查找搜索框...")
            # 尝试多种可能的搜索框选择器
            search_selectors = [
                '#searchInput',
                'input[name="searchkey"]',
                'input[placeholder*="搜索"]',
                'input[type="text"]',
                '.search-input',
                '#search'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"找到搜索框: {selector}")
                    break
                except:
                    continue
            
            if not search_input:
                print("未找到搜索框")
                return []
            
            print(f"输入搜索关键词: {keyword}")
            search_input.clear()
            search_input.send_keys(keyword)
            
            # 查找搜索按钮
            print("查找搜索按钮...")
            search_button_selectors = [
                '#searchButton',
                'button[type="submit"]',
                'input[type="submit"]',
                '.search-btn',
                '.search-button',
                'button:contains("搜索")',
                'input[value*="搜索"]'
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"找到搜索按钮: {selector}")
                    break
                except:
                    continue
            
            if search_button:
                print("点击搜索按钮...")
                driver.execute_script("arguments[0].click();", search_button)
            else:
                print("未找到搜索按钮，尝试按回车键")
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
            
            # 等待搜索结果页面加载
            print("等待搜索结果...")
            time.sleep(3)
            
            # 检查是否跳转到搜索结果页面
            current_url = driver.current_url
            print(f"当前页面URL: {current_url}")
            
            # 等待搜索结果容器出现
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: '/search/' in d.current_url or 
                             d.find_elements(By.CSS_SELECTOR, 'dl') or
                             d.find_elements(By.CSS_SELECTOR, '.result') or
                             d.find_elements(By.CSS_SELECTOR, '.book-list')
                )
            except:
                print("等待搜索结果超时")
            
            # 获取页面HTML并解析
            print("获取搜索结果页面内容...")
            page_html = driver.page_source
            
            # 使用现有的解析方法
            results = self.parse_search_results(page_html)
            
            if results:
                print(f"Selenium搜索成功，找到 {len(results)} 个结果")
                # 过滤与关键词相关的结果
                filtered_results = []
                keyword_lower = keyword.lower()
                for novel in results:
                    title_lower = novel.get('title', '').lower()
                    author_lower = novel.get('author', '').lower()
                    intro_lower = novel.get('intro', '').lower()
                    
                    if (keyword_lower in title_lower or 
                        keyword_lower in author_lower or 
                        keyword_lower in intro_lower):
                        filtered_results.append(novel)
                
                if filtered_results:
                    print(f"过滤后找到 {len(filtered_results)} 个相关结果")
                    return filtered_results
                else:
                    print("搜索结果与关键词不匹配，返回所有结果")
                    return results[:10]  # 返回前10个结果
            else:
                print("Selenium搜索未找到结果")
                return []
                
        except Exception as e:
            print(f"Selenium搜索过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            if driver:
                try:
                    driver.quit()
                    print("浏览器已关闭")
                except:
                    pass

def main():
    spider = QishuSpider()
    
    while True:
        print("\n=== 奇书网小说爬虫 ===喵～")
        print("1. 搜索小说")
        print("2. 直接输入小说URL下载")
        print("3. 退出")
        
        choice = input("请选择操作 (1-3): ").strip()
        
        if choice == '1':
            keyword = input("请输入搜索关键词: ").strip()
            if not keyword:
                print("关键词不能为空喵～")
                continue
            
            print(f"正在搜索: {keyword}...")
            novels = spider.search_novels(keyword)
            
            if not novels:
                print("没有找到相关小说喵～")
                continue
            
            print(f"\n找到 {len(novels)} 本小说:")
            for i, novel in enumerate(novels, 1):
                print(f"{i}. {novel['title']}")
                print(f"   作者: {novel['author']}")
                print(f"   状态: {novel['status']}")
                print(f"   简介: {novel['intro']}")
                print()
            
            try:
                choice_num = int(input(f"请选择要下载的小说 (1-{len(novels)}): "))
                if 1 <= choice_num <= len(novels):
                    selected_novel = novels[choice_num - 1]
                    print(f"开始下载: {selected_novel['title']}")
                    spider.crawl_novel(selected_novel['url'])
                else:
                    print("选择无效喵～")
            except ValueError:
                print("请输入有效数字喵～")
        
        elif choice == '2':
            url = input("请输入小说URL: ").strip()
            if not url:
                print("URL不能为空喵～")
                continue
            
            if 'qishu.vip' not in url:
                print("请输入奇书网的小说URL喵～")
                continue
            
            spider.crawl_novel(url)
        
        elif choice == '3':
            print("再见喵～ฅ^•ﻌ•^ฅ")
            break
        
        else:
            print("无效选择，请重新输入喵～")

if __name__ == '__main__':
    main()