"""
Vercel Serverless Function - 陪伴机器人后端
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, '..'))

try:
    from grief_chatbot.chatbot import GriefSupportChatbot
    from user_state_manager import UserStateManager
    HAS_BACKEND = True
except:
    HAS_BACKEND = False

app = Flask(__name__)
CORS(app)

if HAS_BACKEND:
    try:
        state_manager = UserStateManager()
        user_bots = {}
    except:
        HAS_BACKEND = False
        state_manager = None
        user_bots = {}
else:
    state_manager = None
    user_bots = {}


def get_index_html():
    """读取index.html"""
    try:
        index_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    except:
        return '<html><body>Loading...</body></html>', 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/', methods=['GET'])
@app.route('/index.html', methods=['GET'])
def index():
    """返回主页"""
    return get_index_html()


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """聊天接口"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json() or {}
        msg = data.get('message', '').strip()
        user_id = data.get('userId', 'default')
        user_type = data.get('userType', 'partner')
        
        if not msg:
            return jsonify({'error': '消息为空'}), 400
        
        if not HAS_BACKEND:
            return jsonify({
                'response': '离线模式',
                'stageInfo': '未知',
                'moodIndex': '50',
                'confidence': '0',
                'emotionAnalysis': '离线',
                'alertFlag': '',
                'userType': user_type
            })
        
        if user_id not in user_bots:
            try:
                user_bots[user_id] = GriefSupportChatbot()
            except:
                return jsonify({'error': '初始化失败'}), 500
        
        bot = user_bots[user_id]
        bot.user_type = user_type
        
        response, stage_info = bot.generate_response(msg)
        stage, confidence = bot.stage_detector.get_current_stage(msg, bot.emotion_calc.M_t)
        stage_chinese = bot.stage_detector.get_stage_name_chinese(stage)
        
        return jsonify({
            'response': response,
            'stageInfo': stage_chinese,
            'moodIndex': f"{bot.emotion_calc.M_t:.1f}",
            'confidence': f"{confidence:.2f}",
            'emotionAnalysis': stage_info,
            'alertFlag': '',
            'userType': user_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """状态检查"""
    return jsonify({'status': 'ok', 'backend': HAS_BACKEND})


@app.route('/<path:path>', methods=['GET'])
def catch_all(path):
    """SPA回退路由"""
    if '.' in path:
        try:
            filepath = os.path.join(os.path.dirname(__file__), '..', 'public', path)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return f.read(), 200
        except:
            pass
        return jsonify({'error': 'Not found'}), 404
    
    return get_index_html()


@app.errorhandler(404)
def not_found(e):
    return get_index_html()
