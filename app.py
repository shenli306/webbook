from flask import Flask, request, jsonify, session, send_from_directory, redirect
from flask_cors import CORS
from pymongo import MongoClient
import bcrypt
import os
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from bson.errors import InvalidId
import uuid
import sqlite3
from werkzeug.utils import secure_filename
import base64
from PIL import Image
import io

app = Flask(__name__, static_folder='templates', static_url_path='/static')
app.secret_key = 'your-secret-key-change-this-in-production'  # 生产环境请更换密钥喵~
# 设置session持久化和超时时间
app.permanent_session_lifetime = timedelta(hours=24)  # session有效期24小时
CORS(app, supports_credentials=True)  # 允许跨域请求

# 文件上传配置
UPLOAD_FOLDER = 'templates/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 检查文件扩展名
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 处理图片压缩和优化
def process_cover_image(file):
    try:
        # 打开图片
        image = Image.open(file)
        
        # 转换为RGB模式（处理RGBA等格式）
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # 限制图片尺寸（最大800x600）
        max_size = (800, 600)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 保存为JPEG格式以减小文件大小
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"图片处理失败: {e}")
        return None

# MongoDB配置
# 如果有MongoDB Atlas连接字符串，请替换下面的URI
# MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/"
MONGO_URI = "mongodb://localhost:27017/"  # 本地MongoDB
DATABASE_NAME = "resource_share"

# 连接MongoDB（添加错误处理）
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # 测试连接
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    users_collection = db.users
    resources_collection = db.resources
    print("MongoDB连接成功！")
except Exception as e:
    print(f"MongoDB连接失败: {e}")
    print("将使用内存模拟数据库（仅用于演示）")
    # 创建模拟集合类
    class MockCollection:
        def __init__(self):
            self.data = []
            self.counter = 1
        
        def find_one(self, query=None, projection=None):
            if query is None:
                return self.data[0] if self.data else None
            # 简单的查询模拟
            for item in self.data:
                # 处理username查询
                if 'username' in query and item.get('username') == query['username']:
                    return item
                # 处理ObjectId查询
                if '_id' in query and item.get('_id') == query['_id']:
                    return item
                # 处理$or查询
                if '$or' in query:
                    for condition in query['$or']:
                        for key, value in condition.items():
                            if item.get(key) == value:
                                return item
            return None
        
        def find(self, query=None, projection=None):
            if query is None:
                return self.data
            
            result = []
            for item in self.data:
                match = True
                for key, value in query.items():
                    if key == '_id':
                        if item.get('_id') != value:
                            match = False
                            break
                    elif key == '$or':
                        or_match = False
                        for condition in value:
                            for or_key, or_value in condition.items():
                                if or_key in item and str(item[or_key]).lower().find(str(or_value).lower()) != -1:
                                    or_match = True
                                    break
                            if or_match:
                                break
                        if not or_match:
                            match = False
                            break
                    elif key in item and item[key] != value:
                        match = False
                        break
                if match:
                    result.append(item)
            return result
        
        def insert_one(self, document):
            document['_id'] = ObjectId()
            self.data.append(document)
            return type('Result', (), {'inserted_id': document['_id']})()
        
        def count_documents(self, query):
            return len(self.data)
        
        def create_index(self, *args, **kwargs):
            pass
        
        def update_one(self, query, update):
            return type('Result', (), {'matched_count': 1, 'modified_count': 1})()
        
        def delete_one(self, query):
            return type('Result', (), {'deleted_count': 1})()
        
        def delete_many(self, query):
            return type('Result', (), {'deleted_count': 0})()
        
        def aggregate(self, pipeline):
            import sys
            # 简单实现aggregate功能
            result = self.data.copy()
            print(f"🔍 开始aggregate，初始数据量: {len(result)}")
            sys.stdout.flush()
            
            for stage_index, stage in enumerate(pipeline):
                stage_name = list(stage.keys())[0]
                print(f"📋 处理第{stage_index + 1}个阶段: {stage_name}")
                sys.stdout.flush()
                
                if '$match' in stage:
                    # 处理匹配条件
                    match_conditions = stage['$match']
                    if match_conditions:
                        filtered_result = []
                        for item in result:
                            match = True
                            for key, value in match_conditions.items():
                                if key == '$or':
                                    # 处理$or条件
                                    or_match = False
                                    for condition in value:
                                        for or_key, or_value in condition.items():
                                            if or_key in item:
                                                if isinstance(or_value, dict) and '$regex' in or_value:
                                                    # 处理正则表达式
                                                    import re
                                                    pattern = or_value['$regex']
                                                    flags = re.IGNORECASE if or_value.get('$options') == 'i' else 0
                                                    if re.search(pattern, str(item[or_key]), flags):
                                                        or_match = True
                                                        break
                                                elif str(item[or_key]).lower().find(str(or_value).lower()) != -1:
                                                    or_match = True
                                                    break
                                        if or_match:
                                            break
                                    if not or_match:
                                        match = False
                                        break
                                elif key in item:
                                    if isinstance(value, dict) and '$regex' in value:
                                        # 处理正则表达式
                                        import re
                                        pattern = value['$regex']
                                        flags = re.IGNORECASE if value.get('$options') == 'i' else 0
                                        if not re.search(pattern, str(item[key]), flags):
                                            match = False
                                            break
                                    elif item[key] != value:
                                        match = False
                                        break
                                else:
                                    match = False
                                    break
                            if match:
                                filtered_result.append(item)
                        result = filtered_result
                    print(f"   ✅ $match处理后数据量: {len(result)}")
                    sys.stdout.flush()
                elif '$lookup' in stage:
                    # 简单处理lookup，为每个资源添加用户信息
                    lookup_config = stage['$lookup']
                    as_field = lookup_config.get('as', 'user_info')
                    print(f"   🔍 $lookup配置: {lookup_config}")
                    sys.stdout.flush()
                    
                    for item in result:
                        if 'user_id' in item:
                            # 查找对应的用户
                            try:
                                user_id = ObjectId(item['user_id']) if isinstance(item['user_id'], str) else item['user_id']
                                user = users_collection.find_one({'_id': user_id})
                                if user:
                                    # $lookup总是返回数组
                                    item[as_field] = [user]
                                else:
                                    # 如果找不到用户，返回空数组
                                    item[as_field] = []
                            except:
                                # 如果转换失败，返回空数组
                                item[as_field] = []
                        else:
                            # 如果没有user_id字段，返回空数组
                            item[as_field] = []
                        print(f"   👤 资源 {item.get('_id')} 关联用户: {len(item[as_field])} 个")
                        sys.stdout.flush()
                    print(f"   ✅ $lookup处理后数据量: {len(result)}")
                    sys.stdout.flush()
                    
                elif '$unwind' in stage:
                    # 展开user_info数组
                    unwind_field = stage['$unwind']
                    if isinstance(unwind_field, dict):
                        field_path = unwind_field['path']
                        preserve_null = unwind_field.get('preserveNullAndEmptyArrays', False)
                    else:
                        field_path = unwind_field
                        preserve_null = False
                    
                    field_name = field_path.replace('$', '') if field_path.startswith('$') else field_path
                    print(f"   🔍 $unwind字段: {field_name}, 保留空值: {preserve_null}")
                    sys.stdout.flush()
                    
                    new_result = []
                    for item in result:
                        field_value = item.get(field_name, [])
                        print(f"   📋 处理项 {item.get('_id')}，字段值: {field_value}")
                        sys.stdout.flush()
                        
                        if isinstance(field_value, list) and len(field_value) > 0:
                            # 如果是数组且不为空，展开每个元素
                            for array_item in field_value:
                                new_item = item.copy()
                                new_item[field_name] = array_item
                                new_result.append(new_item)
                                print(f"   ✅ 展开项: {new_item.get('_id')} -> {array_item}")
                                sys.stdout.flush()
                        elif isinstance(field_value, list) and len(field_value) == 0:
                            # 空数组的处理
                            print(f"   ⚠️ 空数组，preserve_null={preserve_null}")
                            sys.stdout.flush()
                            if preserve_null:
                                new_item = item.copy()
                                new_item[field_name] = None
                                new_result.append(new_item)
                                print(f"   ✅ 保留空值项: {new_item.get('_id')}")
                                sys.stdout.flush()
                            else:
                                print(f"   ❌ 跳过空数组项: {item.get('_id')}")
                                sys.stdout.flush()
                        elif not isinstance(field_value, list):
                            # 如果不是数组，直接保留
                            new_result.append(item)
                            print(f"   ✅ 保留非数组项: {item.get('_id')}")
                            sys.stdout.flush()
                        else:
                            print(f"   ❌ 其他情况，跳过项: {item.get('_id')}")
                            sys.stdout.flush()
                    
                    result = new_result
                    print(f"   ✅ $unwind处理后数据量: {len(result)}，字段: {field_name}")
                    sys.stdout.flush()
                elif '$project' in stage:
                    # 处理投影
                    projection = stage['$project']
                    print(f"   🔍 $project配置: {projection}")
                    sys.stdout.flush()
                    
                    new_result = []
                    for item in result:
                        new_item = {}
                        for key, value in projection.items():
                            if value == 1 and key in item:
                                new_item[key] = item[key]
                            elif isinstance(value, str) and value.startswith('$'):
                                # 处理字段引用，如 '$user_info.username'
                                field_path = value[1:].split('.')
                                field_value = item
                                for field in field_path:
                                    if isinstance(field_value, dict) and field in field_value:
                                        field_value = field_value[field]
                                    else:
                                        field_value = None
                                        break
                                new_item[key] = field_value
                        new_result.append(new_item)
                    result = new_result
                    print(f"   ✅ $project处理后数据量: {len(result)}")
                    sys.stdout.flush()
                    
                elif '$sort' in stage:
                    # 处理排序
                    sort_config = stage['$sort']
                    print(f"   🔍 $sort配置: {sort_config}")
                    sys.stdout.flush()
                    
                    def sort_key(item):
                        keys = []
                        for field, order in sort_config.items():
                            value = item.get(field, '')
                            if order == -1:
                                # 降序：对于字符串，使用负序；对于数字，取负值
                                if isinstance(value, (int, float)):
                                    keys.append(-value)
                                else:
                                    keys.append(str(value))
                            else:
                                # 升序
                                if isinstance(value, (int, float)):
                                    keys.append(value)
                                else:
                                    keys.append(str(value))
                        return keys
                    
                    result.sort(key=sort_key, reverse=any(order == -1 for order in sort_config.values()))
                    print(f"   ✅ $sort处理后数据量: {len(result)}")
                    sys.stdout.flush()
                    
                elif '$skip' in stage:
                    skip_count = stage['$skip']
                    print(f"   🔍 $skip跳过: {skip_count} 条")
                    sys.stdout.flush()
                    result = result[skip_count:]
                    print(f"   ✅ $skip处理后数据量: {len(result)}")
                    sys.stdout.flush()
                    
                elif '$limit' in stage:
                    limit_count = stage['$limit']
                    print(f"   🔍 $limit限制: {limit_count} 条")
                    sys.stdout.flush()
                    result = result[:limit_count]
                    print(f"   ✅ $limit处理后数据量: {len(result)}")
                    sys.stdout.flush()
            
            return result
    
    users_collection = MockCollection()
    resources_collection = MockCollection()
    
    # 添加默认管理员账户
    admin_user = {
        'username': 'admin',
        'email': 'admin@example.com',
        'password_hash': bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()),
        'created_at': datetime.now()
    }
    users_collection.data.append(admin_user)

# 静态文件路由
@app.route('/')
def index():
    return redirect('/static/index.html')

@app.route('/book')
def book_page():
    return send_from_directory('templates', 'book.html')

@app.route('/admin')
def admin_panel():
    # 检查是否已登录且为管理员
    if 'user_id' not in session:
        return redirect('/admin/login')
    
    # 使用MongoDB查询用户信息
    try:
        user_object_id = ObjectId(session['user_id'])
    except InvalidId:
        user_object_id = None
    
    user = users_collection.find_one({'_id': user_object_id}) if user_object_id else users_collection.find_one({'username': 'admin'})
    
    if not user or user['username'] != 'admin':
        return redirect('/admin/login')
    
    return send_from_directory('templates/admin', 'index.html')

@app.route('/admin/login')
def admin_login():
    return send_from_directory('templates/admin', 'login.html')

@app.route('/admin/<path:filename>')
def admin_static(filename):
    return send_from_directory('templates/admin', filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('templates', filename)

# 封面图片访问路由
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # 检查是否为小说文件（epub格式）
    if filename.endswith('.epub'):
        return send_from_directory('uploads', filename)
    # 其他文件使用原来的路径
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 小说文件下载路由
@app.route('/downloads/<filename>')
def download_novel_file(filename):
    """下载小说文件喵～"""
    return send_from_directory('uploads', filename)

# 数据库初始化
def init_db():
    try:
        # 创建用户集合索引
        users_collection.create_index("username", unique=True)
        users_collection.create_index("email", unique=True)
        
        # 创建资源集合索引
        resources_collection.create_index("user_id")
        resources_collection.create_index("category")
        resources_collection.create_index("created_at")
        
        # 检查是否存在管理员账户，如果不存在则创建
        admin_user = users_collection.find_one({"username": "admin"})
        if not admin_user:
            admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
            admin_data = {
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": admin_password,
                "nickname": "管理员",
                "role": "admin",
                "created_at": datetime.now()
            }
            users_collection.insert_one(admin_data)
            print("默认管理员账户已创建: admin/admin123")
        else:
            # 确保现有admin用户具有admin角色
            if admin_user.get('role') != 'admin':
                users_collection.update_one(
                    {"username": "admin"},
                    {"$set": {"role": "admin"}}
                )
                print("管理员账户角色已更新为admin")
        
        print("MongoDB数据库初始化完成喵~")
    except Exception as e:
        print(f"数据库初始化失败: {e}")

# 用户注册API
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'code': 'error', 'message': '所有字段都是必填的喵~ (>﹏<)'}), 400
        
        # 检查用户是否已存在
        existing_user = users_collection.find_one({
            "$or": [{"username": username}, {"email": email}]
        })
        if existing_user:
            return jsonify({'code': 'error', 'message': '用户名或邮箱已存在喵~'}), 400
        
        # 创建新用户
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "nickname": username,
            "created_at": datetime.now()
        }
        
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # 设置会话
        session.permanent = True  # 设置为持久session
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            'code': 'success',
            'message': '注册成功喵~ (◕ᴗ◕✿)',
            'user': {
                'id': user_id,
                'username': username,
                'email': email
            }
        })
        
    except Exception as e:
        return jsonify({'code': 'error', 'message': f'注册失败: {str(e)}'}), 500

# 用户登录API
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({'success': False, 'message': '用户名和密码不能为空喵~'}), 400
        
        # 验证用户
        user = users_collection.find_one({"username": username})
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            # 登录成功
            session.permanent = True  # 设置为持久session
            user_id = str(user['_id'])
            session['user_id'] = user_id
            session['username'] = user['username']
            session['nickname'] = user.get('nickname', user['username'])
            session['role'] = user.get('role', 'user')  # 保存角色信息到session
            return jsonify({
                'success': True, 
                'message': '登录成功喵~ ✨',
                'user': {
                    'user_id': user_id,
                    'username': user['username'],
                    'nickname': user.get('nickname', user['username']),
                    'role': user.get('role', 'user'),
                    'is_admin': user.get('role') == 'admin'
                }
            })
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误喵~ (>﹏<)'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500

# 用户登出API
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'code': 'success', 'message': '退出成功喵~ 再见~ (◕ᴗ◕✿)'})

# 临时修复admin角色的API
@app.route('/api/admin/fix-role', methods=['POST'])
def fix_admin_role():
    try:
        # 更新admin用户的role字段
        result = users_collection.update_one(
            {"username": "admin"},
            {"$set": {"role": "admin"}}
        )
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Admin role fixed successfully'})
        else:
            return jsonify({'success': False, 'message': 'No admin user found or already has admin role'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# 用户验证API
@app.route('/api/user/validate', methods=['GET'])
def validate_user():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    try:
        # 验证用户是否存在
        user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
        if not user:
            session.clear()  # 清除无效session
            return jsonify({'success': False, 'message': '用户不存在'}), 401
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': session['user_id'],
                'username': session['username'],
                'nickname': session.get('nickname', session['username']),
                'role': user.get('role', 'user'),
                'is_admin': user.get('role') == 'admin'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'}), 500

# 获取当前用户信息
@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    if 'user_id' not in session:
        return jsonify({'code': 'error', 'message': '请先登录喵~'}), 401
    
    return jsonify({
        'code': 'success',
        'data': {
            'user_id': session['user_id'],
            'username': session['username'],
            'nickname': session['nickname'],
            'role': session.get('role', 'user')  # 添加角色信息
        }
    })

# 发布资源API
@app.route('/api/resources', methods=['POST'])
def publish_resource():
    if 'user_id' not in session:
        return jsonify({'code': 'error', 'message': '请先登录喵~'}), 401
    
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        download_url = data.get('downloadUrl') or data.get('download_url')  # 兼容两种字段名
        category = data.get('category')
        tags = data.get('tags')
        
        if not title:
            return jsonify({'code': 'error', 'message': '标题不能为空喵~'}), 400
        
        # 保存资源到MongoDB数据库
        resource_data = {
            "title": title,
            "description": description,
            "download_url": download_url,
            "category": category,
            "tags": tags,
            "user_id": session['user_id'],
            "created_at": datetime.now()
        }
        
        result = resources_collection.insert_one(resource_data)
        resource_id = str(result.inserted_id)
        
        return jsonify({'code': 'success', 'message': '资源发布成功喵~ ✨', 'resource_id': resource_id})
    except Exception as e:
        return jsonify({'code': 'error', 'message': f'发布失败: {str(e)}'}), 500

# 调试API - 直接查看原始数据
@app.route('/api/resources/debug', methods=['GET'])
def debug_resources():
    import sys
    try:
        print("=== 调试API被调用 ===")
        sys.stdout.flush()
        
        # 直接查询所有资源
        raw_resources = list(resources_collection.find({}))
        print(f"原始资源数据量: {len(raw_resources)}")
        sys.stdout.flush()
        
        # 查询所有用户
        raw_users = list(users_collection.find({}))
        print(f"原始用户数据量: {len(raw_users)}")
        sys.stdout.flush()
        
        # 打印前3条资源数据的结构
        for i, resource in enumerate(raw_resources[:3]):
            print(f"资源 {i+1}: {resource}")
            sys.stdout.flush()
            
        # 打印前3条用户数据的结构
        for i, user in enumerate(raw_users[:3]):
            print(f"用户 {i+1}: {user}")
            sys.stdout.flush()
            
        # 手动转换ObjectId、datetime和bytes
        def clean_data(obj):
            if obj is None:
                return None
            result = {}
            for key, value in obj.items():
                if hasattr(value, '__class__') and 'ObjectId' in str(type(value)):
                    result[key] = str(value)
                elif hasattr(value, '__class__') and 'datetime' in str(type(value)):
                    result[key] = str(value)
                elif isinstance(value, bytes):
                    result[key] = "<bytes_data>"
                else:
                    result[key] = value
            return result
        
        sample_resource = clean_data(raw_resources[0]) if raw_resources else None
        sample_user = clean_data(raw_users[0]) if raw_users else None
        
        return jsonify({
            'resources_count': len(raw_resources),
            'users_count': len(raw_users),
            'sample_resource': sample_resource,
            'sample_user': sample_user
        })
    except Exception as e:
        print(f"调试API异常: {e}")
        sys.stdout.flush()
        return jsonify({'error': str(e)}), 500

# 获取资源列表API
@app.route('/api/resources', methods=['GET'])
def get_resources():
    import sys
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))  # 修复：使用limit而不是per_page
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        
        print(f"🔍 get_resources调用: page={page}, limit={limit}, category={category}, search={search}")
        sys.stdout.flush()
        
        # 构建查询条件
        match_conditions = {}
        
        if category:
            match_conditions['category'] = category
        
        if search:
            match_conditions['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}}
            ]
        
        print(f"🔍 查询条件: {match_conditions}")
        sys.stdout.flush()
        
        # 聚合管道
        pipeline = [
            {'$match': match_conditions},
            {
                '$addFields': {
                    'user_object_id': {'$toObjectId': '$user_id'}
                }
            },
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_object_id',
                    'foreignField': '_id',
                    'as': 'user_info'
                }
            },
            {'$unwind': '$user_info'},
            {
                '$project': {
                    '_id': 1,
                    'title': 1,
                    'description': 1,
                    'download_url': 1,
                    'category': 1,
                'tags': 1,
                'created_at': 1,
                'author': '$user_info.username',
                'cover': 1,
                'cover_image': 1
                }
            },
            {'$sort': {'created_at': -1}},
            {'$skip': (page - 1) * limit},
            {'$limit': limit}
        ]
        
        print(f"🔍 聚合管道: {pipeline}")
        sys.stdout.flush()
        
        # 执行聚合查询
        print(f"🔍 开始执行聚合查询...")
        print(f"🔍 resources_collection类型: {type(resources_collection)}")
        sys.stdout.flush()
        resources = list(resources_collection.aggregate(pipeline))
        print(f"🔍 聚合查询完成，结果数量: {len(resources)}")
        sys.stdout.flush()
        
        # 获取总数
        total = resources_collection.count_documents(match_conditions)
        print(f"🔍 总数查询完成: {total}")
        sys.stdout.flush()
        
        # 格式化结果
        result = []
        for resource in resources:
            # 生成封面图片URL - 统一处理cover和cover_image字段
            cover_url = None
            if resource.get('cover_image'):
                # 如果cover_image已经包含完整路径，直接使用
                if resource['cover_image'].startswith('/uploads/'):
                    cover_url = resource['cover_image']
                else:
                    cover_url = f"/uploads/{resource['cover_image']}"
            elif resource.get('cover'):
                cover_url = f"/uploads/{resource['cover']}"
            
            result.append({
                'id': str(resource['_id']),
                'title': resource.get('title', ''),
                'description': resource.get('description', ''),
                'download_url': resource.get('download_url', resource.get('downloadUrl', '')),
                'category': resource.get('category', ''),
                'tags': resource.get('tags', []),
                'created_at': resource['created_at'].isoformat() if resource.get('created_at') else None,
                'author': resource.get('author', ''),
                'cover': cover_url
            })
        
        print(f"🔍 最终结果数量: {len(result)}")
        sys.stdout.flush()
        
        return jsonify({
            'success': True,
            'data': result,
            'total': total,
            'page': page,
            'limit': limit
        })
        
    except Exception as e:
        print(f"❌ get_resources异常: {str(e)}")
        sys.stdout.flush()
        return jsonify({'code': 'error', 'message': f'获取资源失败: {str(e)}'}), 500

# 获取我的资源API
@app.route('/api/my-resources', methods=['GET'])
def get_my_resources():
    if 'user_id' not in session:
        return jsonify({'code': 'error', 'message': '请先登录喵~'}), 401
    
    try:
        # 查询用户的资源
        resources = resources_collection.find(
            {'user_id': session['user_id']}
        ).sort('created_at', -1)
        
        resource_list = []
        for resource in resources:
            resource_list.append({
                'id': str(resource['_id']),
                'title': resource['title'],
                'description': resource['description'],
                'download_url': resource['download_url'],
                'category': resource['category'],
                'tags': resource['tags'],
                'created_at': resource['created_at'].isoformat() if resource['created_at'] else None
            })
        
        return jsonify({
            'code': 'success',
            'data': resource_list
        })
    except Exception as e:
        return jsonify({'code': 'error', 'message': f'获取我的资源失败: {str(e)}'}), 500

# MongoDB连接已在上方配置，不再需要SQLite连接函数

# 管理员API接口
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        # 检查管理员权限
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        user_id = session['user_id']
        
        # 检查是否为管理员
        try:
            user_object_id = ObjectId(user_id)
        except InvalidId:
            user_object_id = None
        
        user = users_collection.find_one({'_id': user_object_id}) if user_object_id else users_collection.find_one({'username': 'admin'})
        if not user or user['username'] != 'admin':
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # 获取统计数据
        total_users = users_collection.count_documents({})
        total_resources = resources_collection.count_documents({})
        
        # 今日新增用户
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_users = users_collection.count_documents({
            'created_at': {'$gte': today_start}
        })
        
        # 今日新增资源
        today_resources = resources_collection.count_documents({
            'created_at': {'$gte': today_start}
        })
        
        stats = {
            'totalUsers': total_users,
            'totalResources': total_resources,
            'todayUsers': today_users,
            'todayResources': today_resources
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 小说搜索和下载API
@app.route('/api/novel/search', methods=['POST'])
def search_novels():
    """搜索小说API喵～"""
    try:
        data = request.get_json()
        if not data or 'keyword' not in data:
            return jsonify({'success': False, 'message': '请提供搜索关键词'}), 400
        
        keyword = data['keyword'].strip()
        if not keyword:
            return jsonify({'success': False, 'message': '搜索关键词不能为空'}), 400
        
        # 导入并使用爬虫
        from qishu_spider import QishuSpider
        from shucheng import LdzvNovelDownloader
        
        # 检查是否提供了代理配置
        # 移除代理配置，直接创建spider实例
        spider = QishuSpider()
        
        print(f"🔍 开始搜索小说: {keyword}")
        novels = spider.search_novels(keyword)
        
        if not novels:
            return jsonify({
                'success': False, 
                'message': '没有找到相关小说喵～',
                'data': []
            })
        
        # 格式化返回数据
        formatted_novels = []
        for novel in novels:
            formatted_novels.append({
                'title': novel.get('title', ''),
                'author': novel.get('author', ''),
                'status': novel.get('status', ''),
                'intro': novel.get('intro', ''),
                'url': novel.get('url', ''),
                'cover_url': novel.get('cover_url', '')
            })
        
        print(f"✅ 搜索完成，找到 {len(formatted_novels)} 本小说")
        return jsonify({
            'success': True,
            'message': f'找到 {len(formatted_novels)} 本小说',
            'data': formatted_novels
        })
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return jsonify({'success': False, 'message': f'搜索失败: {str(e)}'}), 500

@app.route('/api/novel/download', methods=['POST'])
def download_novel():
    """下载小说API喵～"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'message': '请提供小说URL'}), 400
        
        novel_url = data['url'].strip()
        if not novel_url:
            return jsonify({'success': False, 'message': '小说URL不能为空'}), 400
        
        if 'qishu.vip' not in novel_url:
            return jsonify({'success': False, 'message': '请提供奇书网的小说URL'}), 400
        
        # 导入并使用爬虫
        from qishu_spider import QishuSpider
        
        # 检查是否提供了代理配置
        # 移除代理配置，直接创建spider实例
        spider = QishuSpider()
        
        print(f"📚 开始下载小说: {novel_url}")
        
        # 获取小说信息
        novel_info = spider.get_novel_info(novel_url)
        if not novel_info:
            return jsonify({'success': False, 'message': '获取小说信息失败'}), 400
        
        # 获取章节列表
        chapters = spider.get_chapter_list(novel_url)
        if not chapters:
            return jsonify({'success': False, 'message': '获取章节列表失败'}), 400
        
        # 生成EPUB文件
        output_dir = 'uploads'
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{novel_info['title']}.epub"
        # 清理文件名中的非法字符
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        output_path = os.path.join(output_dir, filename)
        
        spider.create_epub(novel_info, chapters, output_path, use_multithread=False)
        
        print(f"✅ 小说下载完成: {output_path}")
        
        # 返回下载信息
        return jsonify({
            'success': True,
            'message': '小说下载完成',
            'data': {
                'title': novel_info['title'],
                'author': novel_info['author'],
                'status': novel_info['status'],
                'chapters': len(chapters),
                'filename': filename,
                'download_url': f'/uploads/{filename}'
            }
        })
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'}), 500

@app.route('/api/downloaded-novels', methods=['GET'])
def get_downloaded_novels():
    """获取已下载小说列表API喵～"""
    try:
        uploads_dir = 'uploads'
        novels = []
        
        if os.path.exists(uploads_dir):
            for filename in os.listdir(uploads_dir):
                if filename.endswith('.epub'):
                    # 从文件名提取小说标题（去掉.epub扩展名）
                    title = filename[:-5]  # 移除.epub
                    novels.append({
                        'title': title,
                        'filename': filename,
                        'format': 'EPUB'
                    })
        
        return jsonify({
            'success': True,
            'novels': novels,
            'count': len(novels)
        })
        
    except Exception as e:
        print(f"❌ 获取已下载小说列表失败: {e}")
        return jsonify({'success': False, 'message': f'获取列表失败: {str(e)}'}), 500

@app.route('/api/novel/info', methods=['POST'])
def get_novel_info():
    """获取小说详细信息API喵～"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'message': '请提供小说URL'}), 400
        
        novel_url = data['url'].strip()
        if not novel_url:
            return jsonify({'success': False, 'message': '小说URL不能为空'}), 400
        
        # 导入并使用爬虫
        from qishu_spider import QishuSpider
        
        # 检查是否提供了代理配置
        # 移除代理配置，直接创建spider实例
        spider = QishuSpider()
        
        print(f"📖 获取小说信息: {novel_url}")
        
        # 获取小说信息
        novel_info = spider.get_novel_info(novel_url)
        if not novel_info:
            return jsonify({'success': False, 'message': '获取小说信息失败'}), 400
        
        # 获取章节列表
        chapters = spider.get_chapter_list(novel_url)
        chapter_count = len(chapters) if chapters else 0
        
        print(f"✅ 获取小说信息成功: {novel_info['title']}")
        
        return jsonify({
            'success': True,
            'message': '获取小说信息成功',
            'data': {
                'title': novel_info.get('title', ''),
                'author': novel_info.get('author', ''),
                'status': novel_info.get('status', ''),
                'intro': novel_info.get('intro', ''),
                'cover_url': novel_info.get('cover_url', ''),
                'url': novel_url,
                'chapter_count': chapter_count
            }
        })
        
    except Exception as e:
        print(f"❌ 获取小说信息失败: {e}")
        return jsonify({'success': False, 'message': f'获取信息失败: {str(e)}'}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    try:
        # 检查管理员权限
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        user_id = session['user_id']
        
        # 检查是否为管理员
        try:
            user_object_id = ObjectId(user_id)
        except InvalidId:
            user_object_id = None
        
        user = users_collection.find_one({'_id': user_object_id}) if user_object_id else users_collection.find_one({'username': 'admin'})
        if not user or user['username'] != 'admin':
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # 获取搜索参数
        search = request.args.get('search', '')
        
        # 构建查询
        query = {}
        if search:
            query = {
                '$or': [
                    {'username': {'$regex': search, '$options': 'i'}},
                    {'email': {'$regex': search, '$options': 'i'}}
                ]
            }
        
        users = users_collection.find(query, {'password': 0}).sort('created_at', -1)
        
        user_list = []
        for user in users:
            user_list.append({
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'created_at': user['created_at'].isoformat() if user['created_at'] else None
            })
        
        return jsonify({'success': True, 'data': user_list})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/resources', methods=['GET', 'POST'])
def admin_resources():
    try:
        # 检查管理员权限
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        user_id = session['user_id']
        
        # 检查是否为管理员
        try:
            user_object_id = ObjectId(user_id)
        except InvalidId:
            user_object_id = None
        
        user = users_collection.find_one({'_id': user_object_id}) if user_object_id else users_collection.find_one({'username': 'admin'})
        if not user or user['username'] != 'admin':
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        if request.method == 'POST':
            # 添加新资源
            # 检查是否为multipart/form-data请求（包含文件上传）
            if request.content_type and request.content_type.startswith('multipart/form-data'):
                # 处理FormData请求
                title = request.form.get('title', '').strip()
                author = request.form.get('author', '').strip()
                category = request.form.get('category', '').strip()
                description = request.form.get('description', '').strip()
                url = request.form.get('url', '').strip()
                tags = request.form.get('tags', '').strip()
            else:
                # 处理JSON请求（向后兼容）
                data = request.get_json()
                if not data:
                    return jsonify({'success': False, 'message': '请求数据格式错误'}), 400
                
                title = data.get('title', '').strip()
                author = data.get('author', '').strip()
                category = data.get('category', '').strip()
                description = data.get('description', '').strip()
                url = data.get('url', '').strip()
                tags = data.get('tags', '').strip()
            
            if not title or not category:
                return jsonify({'success': False, 'message': '标题和分类为必填项'}), 400
            
            # 处理封面图片上传
            cover_filename = None
            if 'cover' in request.files:
                cover_file = request.files['cover']
                if cover_file and cover_file.filename != '' and allowed_file(cover_file.filename):
                    try:
                        # 生成唯一文件名
                        file_ext = cover_file.filename.rsplit('.', 1)[1].lower()
                        cover_filename = f"cover_{uuid.uuid4().hex}.jpg"  # 统一保存为jpg
                        
                        # 处理图片（压缩和优化）
                        processed_image = process_cover_image(cover_file)
                        if processed_image:
                            # 保存处理后的图片
                            cover_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
                            with open(cover_path, 'wb') as f:
                                f.write(processed_image.getvalue())
                        else:
                            return jsonify({'success': False, 'message': '图片处理失败'}), 400
                            
                    except Exception as e:
                        print(f"封面上传失败: {e}")
                        return jsonify({'success': False, 'message': '封面上传失败'}), 400
            
            # 创建新资源
            new_resource = {
                'title': title,
                'description': description,
                'category': category,
                'author': author,
                'url': url,
                'tags': tags.split(',') if tags else [],
                'cover': cover_filename,  # 添加封面字段
                'user_id': user_object_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = resources_collection.insert_one(new_resource)
            
            if result.inserted_id:
                return jsonify({
                    'success': True, 
                    'message': '资源添加成功',
                    'data': {'id': str(result.inserted_id), 'cover': cover_filename}
                })
            else:
                return jsonify({'success': False, 'message': '添加失败'}), 500
        
        # GET 请求 - 获取搜索和排序参数
        search = request.args.get('search', '')
        sort_param = request.args.get('sort', 'created_at_desc')
        
        # 解析排序参数
        sort_field = 'created_at'
        sort_order = -1  # 默认降序
        
        if sort_param == 'created_at_asc':
            sort_field = 'created_at'
            sort_order = 1
        elif sort_param == 'created_at_desc':
            sort_field = 'created_at'
            sort_order = -1
        elif sort_param == 'title_asc':
            sort_field = 'title'
            sort_order = 1
        elif sort_param == 'title_desc':
            sort_field = 'title'
            sort_order = -1
        elif sort_param == 'category_asc':
            sort_field = 'category'
            sort_order = 1
        
        # 构建聚合管道
        pipeline = [
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user_info'
                }
            },
            {
                '$unwind': {
                    'path': '$user_info',
                    'preserveNullAndEmptyArrays': True
                }
            }
        ]
        
        # 添加搜索条件
        if search:
            pipeline.insert(0, {
                '$match': {
                    '$or': [
                        {'title': {'$regex': search, '$options': 'i'}},
                        {'description': {'$regex': search, '$options': 'i'}},
                        {'category': {'$regex': search, '$options': 'i'}}
                    ]
                }
            })
        
        # 添加排序
        pipeline.append({
            '$sort': {sort_field: sort_order}
        })
        
        # 添加字段选择
        pipeline.append({
            '$project': {
                '_id': 1,
                'title': 1,
                'description': 1,
                'category': 1,
                'tags': 1,
                'cover_image': 1,  # 添加封面字段
                'created_at': 1,
                'author': '$user_info.username'
            }
        })
        
        resources = list(resources_collection.aggregate(pipeline))
        
        resource_list = []
        for resource in resources:
            # 生成封面URL
            cover_url = None
            if resource.get('cover_image'):
                cover_url = resource['cover_image']  # 直接使用存储的路径，已包含/uploads/前缀
            
            resource_list.append({
                'id': str(resource['_id']),
                'title': resource['title'],
                'description': resource['description'],
                'category': resource['category'],
                'tags': resource['tags'],
                'cover': cover_url,  # 添加封面URL
                'created_at': resource['created_at'].isoformat() if resource['created_at'] else None,
                'author': resource.get('author', '未知用户')
            })
        
        return jsonify({'success': True, 'data': resource_list})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/users/<user_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_user(user_id):
    try:
        # 检查管理员权限
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        admin_id = session['user_id']
        
        # 检查是否为管理员
        try:
            admin_object_id = ObjectId(admin_id)
        except InvalidId:
            admin_object_id = None
        
        admin_user = users_collection.find_one({'_id': admin_object_id}) if admin_object_id else users_collection.find_one({'username': 'admin'})
        if not admin_user or admin_user['username'] != 'admin':
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # 转换用户ID
        try:
            user_object_id = ObjectId(user_id)
        except InvalidId:
            return jsonify({'success': False, 'message': '无效的用户ID'}), 400
        
        if request.method == 'GET':
            user = users_collection.find_one({'_id': user_object_id}, {'password_hash': 0})
            if user:
                user_data = {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None
                }
                return jsonify({'success': True, 'data': user_data})
            else:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            
            if not username:
                return jsonify({'success': False, 'message': '用户名不能为空'}), 400
            
            # 检查用户名和邮箱是否已存在（排除当前用户）
            existing_user = users_collection.find_one({
                '$and': [
                    {'_id': {'$ne': user_object_id}},
                    {'$or': [{'username': username}, {'email': email}]}
                ]
            })
            
            if existing_user:
                return jsonify({'success': False, 'message': '用户名或邮箱已存在'}), 400
            
            result = users_collection.update_one(
                {'_id': user_object_id},
                {'$set': {'username': username, 'email': email}}
            )
            
            if result.matched_count == 0:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            return jsonify({'success': True, 'message': '用户更新成功'})
        
        elif request.method == 'DELETE':
            # 不能删除管理员自己
            if str(user_object_id) == admin_id:
                return jsonify({'success': False, 'message': '不能删除自己'}), 400
            
            result = users_collection.delete_one({'_id': user_object_id})
            
            if result.deleted_count == 0:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 删除用户的所有资源
            resources_collection.delete_many({'user_id': str(user_object_id)})
            
            return jsonify({'success': True, 'message': '用户删除成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/resources/<resource_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_resource(resource_id):
    try:
        # 检查管理员权限
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        
        admin_id = session['user_id']
        
        # 检查是否为管理员
        try:
            admin_object_id = ObjectId(admin_id)
        except InvalidId:
            admin_object_id = None
        
        admin_user = users_collection.find_one({'_id': admin_object_id}) if admin_object_id else users_collection.find_one({'username': 'admin'})
        if not admin_user or admin_user['username'] != 'admin':
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # 转换资源ID
        try:
            resource_object_id = ObjectId(resource_id)
        except InvalidId:
            return jsonify({'success': False, 'message': '无效的资源ID'}), 400
        
        if request.method == 'GET':
            # 获取资源详情（使用聚合查询获取作者信息）
            pipeline = [
                {'$match': {'_id': resource_object_id}},
                {
                    '$lookup': {
                        'from': 'users',
                        'localField': 'user_id',
                        'foreignField': '_id',
                        'as': 'user_info'
                    }
                },
                {
                    '$unwind': {
                        'path': '$user_info',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$project': {
                        '_id': 1,
                        'title': 1,
                        'description': 1,
                        'download_url': 1,
                        'category': 1,
                        'tags': 1,
                        'cover_image': 1,
                        'created_at': 1,
                        'author': '$user_info.username'
                    }
                }
            ]
            
            result = list(resources_collection.aggregate(pipeline))
            if not result:
                return jsonify({'success': False, 'message': '资源不存在'}), 404
            
            resource = result[0]
            resource_data = {
                'id': str(resource['_id']),
                'title': resource['title'],
                'description': resource['description'],
                'download_url': resource['download_url'],
                'category': resource['category'],
                'tags': resource['tags'],
                'cover_image': resource.get('cover_image', ''),
                'created_at': resource['created_at'].isoformat() if resource['created_at'] else None,
                'author': resource.get('author', '未知用户')
            }
            return jsonify({'success': True, 'data': resource_data})
        
        elif request.method == 'PUT':
            # 检查是否为multipart/form-data请求（包含文件上传）
            if request.content_type and 'multipart/form-data' in request.content_type:
                # 处理文件上传
                title = request.form.get('title', '').strip()
                author = request.form.get('author', '').strip()
                description = request.form.get('description', '').strip()
                category = request.form.get('category', '').strip()
                download_url = request.form.get('download_url', '').strip()
                tags = request.form.get('tags', '').strip()
                
                if not title or not category:
                    return jsonify({'success': False, 'message': '标题和分类不能为空'}), 400
                
                update_data = {
                    'title': title,
                    'author': author,
                    'description': description,
                    'category': category,
                    'download_url': download_url,
                    'tags': tags
                }
                
                # 处理封面图片
                if 'cover' in request.files:
                    cover_file = request.files['cover']
                    if cover_file and cover_file.filename != '' and allowed_file(cover_file.filename):
                        try:
                            # 处理图片
                            processed_image = process_cover_image(cover_file)
                            if processed_image:
                                # 生成唯一文件名
                                filename = f"cover_{resource_id}_{uuid.uuid4().hex[:8]}.jpg"
                                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                                
                                # 保存处理后的图片
                                with open(filepath, 'wb') as f:
                                    f.write(processed_image.getvalue())
                                
                                # 添加封面路径到更新数据
                                update_data['cover_image'] = f'/uploads/{filename}'
                        except Exception as e:
                            return jsonify({'success': False, 'message': f'封面上传失败: {str(e)}'}), 400
                
                # 处理直接设置封面URL的情况
                elif 'cover_image_url' in request.form:
                    cover_url = request.form.get('cover_image_url', '').strip()
                    if cover_url:
                        update_data['cover_image'] = cover_url
            else:
                # 处理JSON请求
                data = request.get_json()
                title = data.get('title', '').strip()
                author = data.get('author', '').strip()
                description = data.get('description', '').strip()
                category = data.get('category', '').strip()
                download_url = data.get('download_url', '').strip()
                tags = data.get('tags', '').strip()
                
                if not title or not category:
                    return jsonify({'success': False, 'message': '标题和分类不能为空'}), 400
                
                update_data = {
                    'title': title,
                    'author': author,
                    'description': description,
                    'category': category,
                    'download_url': download_url,
                    'tags': tags
                }
            
            result = resources_collection.update_one(
                {'_id': resource_object_id},
                {'$set': update_data}
            )
            
            if result.matched_count == 0:
                return jsonify({'success': False, 'message': '资源不存在'}), 404
            
            return jsonify({'success': True, 'message': '资源更新成功'})
        
        elif request.method == 'DELETE':
            result = resources_collection.delete_one({'_id': resource_object_id})
            
            if result.deleted_count == 0:
                return jsonify({'success': False, 'message': '资源不存在'}), 404
            
            return jsonify({'success': True, 'message': '资源删除成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 我的书城网爬虫测试页面 🐱
@app.route('/wodushu')
def wodushu_test():
    """我的书城网爬虫测试页面喵~"""
    return render_template('wodushu_test.html')

# 我的书城网爬虫API接口 🐱
@app.route('/api/wodushu/search', methods=['POST'])
def wodushu_search():
    """搜索我的书城网小说喵~"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        
        if not keyword:
            return jsonify({'success': False, 'message': '请输入搜索关键词喵~'})
        
        spider = LdzvNovelDownloader()
        results = spider.search_novels(keyword)
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f'找到 {len(results)} 本小说喵~ (◕ᴗ◕✿)'
        })
        
    except Exception as e:
        print(f"搜索错误: {e}")
        return jsonify({'success': False, 'message': f'搜索失败喵~ {str(e)}'})

@app.route('/api/wodushu/novel/<book_id>', methods=['GET'])
def get_wodushu_novel_info(book_id):
    """获取我的书城网小说详细信息喵~"""
    try:
        spider = LdzvNovelDownloader()
        novel_info = spider.get_novel_info(book_id)
        
        if novel_info:
            return jsonify({
                'success': True,
                'data': novel_info
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取小说信息失败喵~'
            })
            
    except Exception as e:
        print(f"获取小说信息错误: {e}")
        return jsonify({'success': False, 'message': f'获取失败喵~ {str(e)}'})

@app.route('/api/wodushu/download', methods=['POST'])
def download_wodushu_novel():
    """下载我的书城网小说喵~"""
    try:
        data = request.get_json()
        book_id = data.get('book_id')
        max_chapters = data.get('max_chapters', 50)  # 默认最多50章
        
        if not book_id:
            return jsonify({'success': False, 'message': '请提供小说ID喵~'})
        
        spider = LdzvNovelDownloader()
        
        # 下载小说
        result = spider.download_novel(book_id, max_chapters=max_chapters)
        
        if result:
            return jsonify({
                'success': True,
                'data': {
                    'novel_info': result['novel_info'],
                    'epub_path': result['epub_path'],
                    'cover_path': result['cover_path'],
                    'chapters_count': len(result['chapters'])
                },
                'message': '下载完成喵~ 🎉'
            })
        else:
            return jsonify({
                'success': False,
                'message': '下载失败喵~'
            })
            
    except Exception as e:
        print(f"下载错误: {e}")
        return jsonify({'success': False, 'message': f'下载失败喵~ {str(e)}'})

if __name__ == '__main__':
    init_db()  # 初始化数据库
    print("🐱 波奇酱后端服务启动中... (◕ᴗ◕✿)")
    app.run(debug=True, host='0.0.0.0', port=5000)