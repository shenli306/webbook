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

# Selenium相关导入
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium未安装，部分功能可能不可用")

class LdzvNovelDownloader:
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
        self.base_url = 'https://www.ldzv.cc'
        
    def search_novels(self, keyword, page=1):
        """搜索小说喵～"""
        try:
            print(f"正在搜索: {keyword}")
            
            # 使用Selenium进行动态搜索
            if SELENIUM_AVAILABLE:
                return self.selenium_search(keyword)
            else:
                print("Selenium不可用，使用静态搜索方法")
                return self.static_search(keyword)
                
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def static_search(self, keyword):
        """静态搜索方法喵～"""
        try:
            # 尝试直接访问搜索页面
            search_url = f"{self.base_url}/search?q={quote(keyword)}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                return self.parse_search_results(response.text)
            else:
                print(f"搜索请求失败，状态码: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"静态搜索失败: {e}")
            return []
    
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
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # 启动浏览器
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # 访问主页
            print("正在访问主页...")
            driver.get(self.base_url)
            time.sleep(2)
            
            # 查找搜索框
            search_input = None
            search_selectors = [
                'input[name="searchkey"]',
                'input[placeholder*="搜索"]',
                'input[type="search"]',
                '.search-input',
                '#search-input',
                'input.form-control'
            ]
            
            for selector in search_selectors:
                try:
                    search_input = driver.find_element(By.CSS_SELECTOR, selector)
                    if search_input.is_displayed():
                        print(f"找到搜索框: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                print("未找到搜索框")
                return []
            
            # 输入搜索关键词
            print(f"输入搜索关键词: {keyword}")
            search_input.clear()
            search_input.send_keys(keyword)
            time.sleep(1)
            
            # 查找搜索按钮并点击
            search_button = None
            button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.search-btn',
                '#search-btn',
                'button.btn'
            ]
            
            for selector in button_selectors:
                try:
                    search_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if search_button.is_displayed():
                        print(f"找到搜索按钮: {selector}")
                        break
                except:
                    continue
            
            if search_button:
                search_button.click()
            else:
                # 如果没找到按钮，尝试按回车
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
            
            print("等待搜索结果加载...")
            time.sleep(3)
            
            # 滚动页面加载更多结果
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            max_scrolls = 5
            
            while scroll_count < max_scrolls:
                # 滚动到页面底部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 检查是否有新内容加载
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scroll_count += 1
                print(f"第{scroll_count}次滚动，页面高度: {new_height}")
            
            # 获取页面源码并解析
            page_source = driver.page_source
            results = self.parse_search_results(page_source)
            
            # 去重处理
            unique_results = self.deduplicate_results(results)
            
            print(f"搜索完成，找到 {len(results)} 个结果，去重后 {len(unique_results)} 个")
            return unique_results
            
        except Exception as e:
            print(f"Selenium搜索过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def parse_search_results(self, html):
        """解析搜索结果页面喵～"""
        soup = BeautifulSoup(html, 'html.parser')
        novels = []
        
        print(f"HTML长度: {len(html)}")
        print(f"页面标题: {soup.title.text if soup.title else '无标题'}")
        
        # 尝试多种可能的搜索结果容器
        result_containers = [
            soup.find_all('div', class_=re.compile(r'book|novel|result|item')),
            soup.find_all('li', class_=re.compile(r'book|novel|result|item')),
            soup.find_all('a', href=re.compile(r'/book/|/novel/')),
            soup.find_all('div', attrs={'data-book-id': True}),
        ]
        
        for containers in result_containers:
            if containers:
                print(f"找到 {len(containers)} 个可能的结果容器")
                break
        
        # 解析每个结果
        processed_urls = set()
        
        for containers in result_containers:
            for item in containers:
                try:
                    novel_info = self.extract_novel_info(item)
                    if novel_info and novel_info.get('url') not in processed_urls:
                        novels.append(novel_info)
                        processed_urls.add(novel_info['url'])
                        print(f"提取到小说: {novel_info.get('title', '未知')}")
                except Exception as e:
                    print(f"解析单个结果时出错: {e}")
                    continue
        
        if not novels:
            print("未找到搜索结果，尝试备用解析方法")
            # 备用解析方法
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/book/' in href or '/novel/' in href:
                    try:
                        novel_info = self.extract_novel_info_from_link(link)
                        if novel_info and novel_info.get('url') not in processed_urls:
                            novels.append(novel_info)
                            processed_urls.add(novel_info['url'])
                    except:
                        continue
        
        print(f"总共找到 {len(novels)} 个搜索结果")
        return novels
    
    def extract_novel_info(self, element):
        """从元素中提取小说信息喵～"""
        try:
            # 查找标题
            title_elem = (
                element.find('h3') or 
                element.find('h4') or 
                element.find('h2') or
                element.find(class_=re.compile(r'title|name')) or
                element.find('a')
            )
            
            title = ''
            url = ''
            
            if title_elem:
                if title_elem.name == 'a':
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                else:
                    title = title_elem.get_text(strip=True)
                    # 查找链接
                    link_elem = element.find('a', href=True)
                    if link_elem:
                        url = link_elem.get('href', '')
            
            if not title or not url:
                return None
            
            # 处理相对URL
            if url.startswith('/'):
                url = self.base_url + url
            elif not url.startswith('http'):
                url = urljoin(self.base_url, url)
            
            # 提取作者
            author_elem = (
                element.find(class_=re.compile(r'author|writer')) or
                element.find('span', string=re.compile(r'作者|Author'))
            )
            author = author_elem.get_text(strip=True) if author_elem else '未知作者'
            
            # 提取简介
            intro_elem = (
                element.find(class_=re.compile(r'intro|desc|summary')) or
                element.find('p')
            )
            intro = intro_elem.get_text(strip=True) if intro_elem else '暂无简介'
            
            # 提取状态
            status_elem = element.find(class_=re.compile(r'status|state'))
            status = status_elem.get_text(strip=True) if status_elem else '未知状态'
            
            # 构建book_url
            book_id_match = re.search(r'/book/(\d+)', url)
            if book_id_match:
                book_id = book_id_match.group(1)
                book_url = f"https://www.ldzv.cc/#/book/{book_id}"
            else:
                book_url = url
            
            return {
                'title': title,
                'author': author,
                'intro': intro[:200] + '...' if len(intro) > 200 else intro,
                'status': status,
                'url': book_url,
                'cover_url': ''
            }
            
        except Exception as e:
            print(f"提取小说信息时出错: {e}")
            return None
    
    def extract_novel_info_from_link(self, link_elem):
        """从链接元素中提取小说信息喵～"""
        try:
            title = link_elem.get_text(strip=True)
            url = link_elem.get('href', '')
            
            if not title or not url or len(title) < 2:
                return None
            
            # 处理相对URL
            if url.startswith('/'):
                url = self.base_url + url
            elif not url.startswith('http'):
                url = urljoin(self.base_url, url)
            
            # 构建book_url
            book_id_match = re.search(r'/book/(\d+)', url)
            if book_id_match:
                book_id = book_id_match.group(1)
                book_url = f"https://www.ldzv.cc/#/book/{book_id}"
            else:
                book_url = url
            
            return {
                'title': title,
                'author': '未知作者',
                'intro': '暂无简介',
                'status': '未知状态',
                'url': book_url,
                'cover_url': ''
            }
            
        except Exception as e:
            print(f"从链接提取信息时出错: {e}")
            return None
    
    def deduplicate_results(self, results):
        """去重处理喵～"""
        seen = set()
        unique_results = []
        
        for result in results:
            # 使用标题和作者作为去重标识
            key = (result.get('title', ''), result.get('author', ''))
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results
    
    def get_novel_info(self, book_id):
        """获取小说详细信息喵～"""
        try:
            # 首先尝试API获取
            api_url = f"{self.base_url}/api/book/{book_id}"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data')
                except:
                    pass
            
            # 如果API失败，尝试解析网页
            book_url = f"{self.base_url}/#/book/{book_id}"
            response = self.session.get(book_url, timeout=10)
            
            if response.status_code == 200:
                return self.parse_novel_page(response.text)
            
            return None
            
        except Exception as e:
            print(f"获取小说信息失败: {e}")
            return None
    
    def parse_novel_page(self, html):
        """解析小说页面喵～"""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # 提取基本信息
            title_elem = soup.find('h1') or soup.find(class_=re.compile(r'title|name'))
            title = title_elem.get_text(strip=True) if title_elem else '未知标题'
            
            author_elem = soup.find(class_=re.compile(r'author|writer'))
            author = author_elem.get_text(strip=True) if author_elem else '未知作者'
            
            intro_elem = soup.find(class_=re.compile(r'intro|desc|summary'))
            intro = intro_elem.get_text(strip=True) if intro_elem else '暂无简介'
            
            return {
                'title': title,
                'author': author,
                'intro': intro,
                'status': '连载中',
                'cover_url': ''
            }
            
        except Exception as e:
            print(f"解析小说页面失败: {e}")
            return None
    
    def download_novel(self, book_id, output_dir='.'):
        """下载小说喵～"""
        try:
            print(f"开始下载小说 ID: {book_id}")
            
            # 获取小说信息
            novel_info = self.get_novel_info(book_id)
            if not novel_info:
                print("获取小说信息失败")
                return False
            
            print(f"小说信息: {novel_info.get('title', '未知')} - {novel_info.get('author', '未知')}")
            
            # 获取章节列表
            chapters = self.get_chapter_list(book_id)
            if not chapters:
                print("获取章节列表失败")
                return False
            
            print(f"找到 {len(chapters)} 个章节")
            
            # 下载章节内容
            chapter_contents = self.download_chapters(chapters)
            
            # 生成EPUB文件
            filename = f"{novel_info.get('title', 'novel')}_{book_id}.epub"
            filepath = os.path.join(output_dir, filename)
            
            self.create_epub(novel_info, chapter_contents, filepath)
            
            print(f"下载完成: {filepath}")
            return True
            
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def get_chapter_list(self, book_id):
        """获取章节列表喵～"""
        try:
            # 尝试API获取章节列表
            api_url = f"{self.base_url}/api/book/{book_id}/chapters"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data', [])
                except:
                    pass
            
            # 如果API失败，返回空列表
            print("获取章节列表失败")
            return []
            
        except Exception as e:
            print(f"获取章节列表出错: {e}")
            return []
    
    def download_chapters(self, chapters):
        """下载章节内容喵～"""
        chapter_contents = []
        
        for i, chapter in enumerate(chapters):
            try:
                print(f"下载第{i+1}章: {chapter.get('title', '未知章节')}")
                
                content = self.get_chapter_content(chapter.get('id'))
                if content:
                    chapter_contents.append({
                        'title': chapter.get('title', f'第{i+1}章'),
                        'content': content
                    })
                else:
                    print(f"第{i+1}章下载失败")
                    
                time.sleep(1)  # 避免请求过快
                
            except Exception as e:
                print(f"下载第{i+1}章时出错: {e}")
                continue
        
        return chapter_contents
    
    def get_chapter_content(self, chapter_id):
        """获取章节内容喵～"""
        try:
            api_url = f"{self.base_url}/api/chapter/{chapter_id}"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        return data.get('data', {}).get('content', '')
                except:
                    pass
            
            return ''
            
        except Exception as e:
            print(f"获取章节内容失败: {e}")
            return ''
    
    def create_epub(self, novel_info, chapters, output_path):
        """创建EPUB文件喵～"""
        try:
            book = epub.EpubBook()
            
            # 设置书籍信息
            book.set_identifier('id123456')
            book.set_title(novel_info.get('title', '未知小说'))
            book.set_language('zh')
            book.add_author(novel_info.get('author', '未知作者'))
            
            # 添加章节
            epub_chapters = []
            for i, chapter in enumerate(chapters):
                c = epub.EpubHtml(
                    title=chapter['title'],
                    file_name=f'chap_{i+1:03d}.xhtml',
                    lang='zh'
                )
                c.content = f'<h1>{chapter["title"]}</h1><div>{chapter["content"]}</div>'
                book.add_item(c)
                epub_chapters.append(c)
            
            # 添加目录
            book.toc = epub_chapters
            
            # 添加导航文件
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # 设置spine
            book.spine = ['nav'] + epub_chapters
            
            # 写入文件
            epub.write_epub(output_path, book, {})
            print(f"EPUB文件创建成功: {output_path}")
            
        except Exception as e:
            print(f"创建EPUB文件失败: {e}")

def main():
    downloader = LdzvNovelDownloader()
    
    while True:
        print("\n=== 书城小说下载器 ===喵～")
        print("1. 搜索小说")
        print("2. 下载小说")
        print("3. 退出")
        
        choice = input("请选择操作 (1-3): ").strip()
        
        if choice == '1':
            keyword = input("请输入搜索关键词: ").strip()
            if not keyword:
                print("关键词不能为空喵～")
                continue
            
            print(f"正在搜索: {keyword}...")
            novels = downloader.search_novels(keyword)
            
            if novels:
                print(f"\n找到 {len(novels)} 本小说:")
                for i, novel in enumerate(novels[:10], 1):
                    print(f"{i}. {novel.get('title', '未知')} - {novel.get('author', '未知')}")
                    print(f"   简介: {novel.get('intro', '暂无')[:50]}...")
                    print(f"   状态: {novel.get('status', '未知')}")
                    print()
            else:
                print("没有找到相关小说喵～")
        
        elif choice == '2':
            book_id = input("请输入小说ID: ").strip()
            if not book_id:
                print("小说ID不能为空喵～")
                continue
            
            output_dir = input("请输入保存目录 (默认当前目录): ").strip() or '.'
            
            if downloader.download_novel(book_id, output_dir):
                print("下载成功喵～")
            else:
                print("下载失败喵～")
        
        elif choice == '3':
            print("再见喵～")
            break
        
        else:
            print("无效选择，请重新输入喵～")

if __name__ == '__main__':
    main()