"""
Flask后端服务
为情感支持聊天机器人提供完整的API接口
集成千问API、心情指数、五阶段模型、用户管理等功能
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from grief_chatbot.chatbot import GriefSupportChatbot
    from user_state_manager import UserStateManager
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False
    print("警告：后端模块未找到，将使用模拟响应")


app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # 允许跨域请求

# 创建全局实例
if HAS_BACKEND:
    state_manager = UserStateManager()
    user_bots = {}  # 为每个用户维护独立的聊天机器人实例
else:
    state_manager = None
    user_bots = {}


def get_or_create_chatbot(user_id):
    """获取或创建用户的聊天机器人实例"""
    if not HAS_BACKEND:
        return None
    if user_id not in user_bots:
        user_bots[user_id] = GriefSupportChatbot()
        user_bots[user_id].user_id = user_id
    return user_bots[user_id]


@app.route('/')
def index():
    """主页路由 - 返回index.html"""
    try:
        return send_from_directory('.', 'index.html')
    except:
        # 如果find不到，返回简单的HTML
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>陪伴机器人 - 加载中...</title>
            <script>
                window.location.href = '/';
            </script>
        </head>
        <body>
            <p>正在重新定向...</p>
        </body>
        </html>
        '''


@app.route('/index.html')
def serve_index():
    """明确路由到index.html"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """静态文件路由"""
    # 防止递归循环
    if path in ['', 'index.html', '/']:
        return index()
    
    try:
        if os.path.isfile(path):
            return send_from_directory('.', path)
    except:
        pass
    
    # 如果文件不存在，返回index.html（用于SPA路由）
    try:
        return send_from_directory('.', 'index.html')
    except:
        return index()


@app.route('/api/chat', methods=['POST'])
def chat_api():
    """
    聊天API接口 - 核心接口
    请求体：
    {
        'message': 用户消息,
        'userId': 用户ID,
        'userType': 用户场景 (partner/family/pet)
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        user_id = data.get('userId', 'default_user')
        user_type = data.get('userType', 'partner')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400
        
        if not HAS_BACKEND:
            # 模拟响应（后端未部署时）
            return jsonify({
                'response': '亲爱的，我感受到了你的情感。现在你可能需要连接真实的后端服务来获得完整的支持。请检查后端是否已正确部署。',
                'stageInfo': '未知',
                'moodIndex': '--',
                'confidence': '0.00',
                'emotionAnalysis': '离线模式 - 请部署完整的后端',
                'alertFlag': '',
                'userType': user_type
            })
        
        # 获取或创建用户的机器人实例
        bot = get_or_create_chatbot(user_id)
        bot.user_type = user_type
        
        # 生成机器人回复
        response, stage_info = bot.generate_response(user_message)
        
        # 提取阶段信息
        stage, confidence = bot.stage_detector.get_current_stage(user_message, bot.emotion_calc.M_t)
        stage_chinese = bot.stage_detector.get_stage_name_chinese(stage)
        
        # 检查是否需要安全警告
        alert_flag = ''
        if bot.emotion_calc.M_t > bot.emotion_calc.crisis_threshold:
            alert_flag = 'crisis'
            state_manager.record_alert(user_id, 'crisis')
        elif bot.emotion_calc.M_t > bot.emotion_calc.warning_threshold:
            alert_flag = 'warning'
            state_manager.record_alert(user_id, 'warning')
        
        # 记录用户交互
        state_manager.record_interaction(user_id, user_message, response, stage, bot.emotion_calc.M_t)
        state_manager.record_emotion_update(user_id, bot.emotion_calc.M_t, bot.emotion_calc.b_t)
        state_manager.record_stage_detection(user_id, stage, confidence)
        
        # 记录关键词密度
        keyword_densities = bot.stage_detector.get_all_keyword_densities(user_message)
        state_manager.record_keyword_density(user_id, keyword_densities)
        
        # 构建响应
        return jsonify({
            'response': response,
            'stageInfo': stage_chinese,
            'moodIndex': f"{bot.emotion_calc.M_t:.1f}",
            'confidence': f"{confidence:.2f}",
            'emotionAnalysis': stage_info,
            'alertFlag': alert_flag,
            'userType': user_type
        })
        
    except Exception as e:
        app.logger.error(f"Chat API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '处理消息时发生错误: ' + str(e)}), 500


@app.route('/api/user/statistics/<user_id>', methods=['GET'])
def user_statistics_api(user_id):
    """获取用户统计信息"""
    if not HAS_BACKEND or not state_manager:
        return jsonify({'error': '后端未部署'}), 503
    
    try:
        stats = state_manager.get_user_statistics(user_id)
        return jsonify({
            'userId': user_id,
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/emotion-history/<user_id>', methods=['GET'])
def emotion_history_api(user_id):
    """获取用户的心情指数历史"""
    if not HAS_BACKEND or not state_manager:
        return jsonify({'error': '后端未部署'}), 503
    
    try:
        days = request.args.get('days', 7, type=int)
        history = state_manager.get_user_emotion_history(user_id, days)
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/stage-trajectory/<user_id>', methods=['GET'])
def stage_trajectory_api(user_id):
    """获取用户的阶段变化轨迹"""
    if not HAS_BACKEND or not state_manager:
        return jsonify({'error': '后端未部署'}), 503
    
    try:
        limit = request.args.get('limit', 50, type=int)
        trajectory = state_manager.get_user_stage_trajectory(user_id, limit)
        return jsonify(trajectory)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/interaction-summary/<user_id>', methods=['GET'])
def interaction_summary_api(user_id):
    """获取用户最近的交互摘要"""
    if not HAS_BACKEND or not state_manager:
        return jsonify({'error': '后端未部署'}), 503
    
    try:
        limit = request.args.get('limit', 20, type=int)
        summary = state_manager.get_user_interaction_summary(user_id, limit)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/stage-analysis/<user_id>', methods=['GET'])
def stage_analysis_api(user_id):
    """获取用户的阶段分析"""
    if not HAS_BACKEND or not state_manager:
        return jsonify({'error': '后端未部署'}), 503
    
    try:
        state_data = state_manager.load_user_state(user_id)
        
        # 获取最近的阶段序列
        recent_stages = [s for _, s, _ in state_data['stage_history'][-30:]]
        
        # 计算阶段分布
        stage_counts = {}
        for stage in ['denial', 'anger', 'bargaining', 'depression', 'acceptance']:
            stage_counts[stage] = recent_stages.count(stage)
        
        # 计算接受阶段的趋势
        acceptance_ratio = stage_counts['acceptance'] / len(recent_stages) if recent_stages else 0
        
        return jsonify({
            'userId': user_id,
            'stageDistribution': stage_counts,
            'acceptanceRatio': f"{acceptance_ratio:.2%}",
            'recentStages': recent_stages,
            'currentStage': state_data['statistics'].get('current_stage', 'unknown'),
            'stageTransitionCount': state_data['statistics'].get('stage_transition_counts', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status_api():
    """系统状态API"""
    try:
        return jsonify({
            'status': 'running' if HAS_BACKEND else 'limited',
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'activeUsers': len(user_bots),
            'backendAvailable': HAS_BACKEND,
            'message': '情感支持聊天机器人服务正常运行' if HAS_BACKEND else '前端已部署，等待后端连接'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """404处理 - 返回index.html用于SPA路由"""
    try:
        return send_from_directory('.', 'index.html'), 200
    except:
        return index()


@app.errorhandler(500)
def server_error(error):
    """500错误处理"""
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    # 确保在正确的目录下运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("🕊️  情感支持聊天机器人 Web 服务")
    print("=" * 60)
    if HAS_BACKEND:
        print("✓ 已集成千问AI大模型")
        print("✓ 已启用渐进式衰减机制")
        print("✓ 已支持五阶段悲伤模型")
        print("✓ 已启用用户状态持久化")
    else:
        print("⚠ 后端模块未找到（离线模式）")
        print("✓ 前端已部署，接受API调用")
    print("=" * 60)
    print("请在浏览器中访问: http://localhost:5000")
    print("API状态: http://localhost:5000/api/status")
    print("=" * 60)
    
    # 启动Flask应用
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )



app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 创建全局实例
chatbot = GriefSupportChatbot()
state_manager = UserStateManager()
user_bots = {}  # 为每个用户维护独立的聊天机器人实例


def get_or_create_chatbot(user_id):
    """获取或创建用户的聊天机器人实例"""
    if user_id not in user_bots:
        user_bots[user_id] = GriefSupportChatbot()
        user_bots[user_id].user_id = user_id
    return user_bots[user_id]


@app.route('/')
def index():
    """主页路由"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """静态文件路由"""
    try:
        return send_from_directory('.', path)
    except:
        return index()


@app.route('/api/chat', methods=['POST'])
def chat_api():
    """
    聊天API接口 - 核心接口
    请求体：
    {
        'message': 用户消息,
        'userId': 用户ID,
        'userType': 用户场景 (partner/family/pet)
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        user_id = data.get('userId', 'default_user')
        user_type = data.get('userType', 'partner')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 获取或创建用户的机器人实例
        bot = get_or_create_chatbot(user_id)
        bot.user_type = user_type
        
        # 生成机器人回复
        response, stage_info = bot.generate_response(user_message)
        
        # 提取阶段信息
        stage, confidence = bot.stage_detector.get_current_stage(user_message, bot.emotion_calc.M_t)
        stage_chinese = bot.stage_detector.get_stage_name_chinese(stage)
        
        # 检查是否需要安全警告
        alert_flag = ''
        if bot.emotion_calc.M_t > bot.emotion_calc.crisis_threshold:
            alert_flag = 'crisis'
            state_manager.record_alert(user_id, 'crisis')
        elif bot.emotion_calc.M_t > bot.emotion_calc.warning_threshold:
            alert_flag = 'warning'
            state_manager.record_alert(user_id, 'warning')
        
        # 记录用户交互
        state_manager.record_interaction(user_id, user_message, response, stage, bot.emotion_calc.M_t)
        state_manager.record_emotion_update(user_id, bot.emotion_calc.M_t, bot.emotion_calc.b_t)
        state_manager.record_stage_detection(user_id, stage, confidence)
        
        # 记录关键词密度
        keyword_densities = bot.stage_detector.get_all_keyword_densities(user_message)
        state_manager.record_keyword_density(user_id, keyword_densities)
        
        # 构建响应
        return jsonify({
            'response': response,
            'stageInfo': stage_chinese,
            'moodIndex': f"{bot.emotion_calc.M_t:.1f}",
            'confidence': f"{confidence:.2f}",
            'emotionAnalysis': stage_info,
            'alertFlag': alert_flag,
            'userType': user_type
        })
        
    except Exception as e:
        app.logger.error(f"Chat API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '处理消息时发生错误: ' + str(e)}), 500


@app.route('/api/user/statistics/<user_id>', methods=['GET'])
def user_statistics_api(user_id):
    """
    获取用户统计信息
    """
    try:
        stats = state_manager.get_user_statistics(user_id)
        return jsonify({
            'userId': user_id,
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/emotion-history/<user_id>', methods=['GET'])
def emotion_history_api(user_id):
    """
    获取用户的心情指数历史
    查询参数：days (默认7)
    """
    try:
        days = request.args.get('days', 7, type=int)
        history = state_manager.get_user_emotion_history(user_id, days)
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/stage-trajectory/<user_id>', methods=['GET'])
def stage_trajectory_api(user_id):
    """
    获取用户的阶段变化轨迹
    查询参数：limit (默认50)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        trajectory = state_manager.get_user_stage_trajectory(user_id, limit)
        return jsonify(trajectory)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/interaction-summary/<user_id>', methods=['GET'])
def interaction_summary_api(user_id):
    """
    获取用户最近的交互摘要
    查询参数：limit (默认20)
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        summary = state_manager.get_user_interaction_summary(user_id, limit)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/stage-analysis/<user_id>', methods=['GET'])
def stage_analysis_api(user_id):
    """
    获取用户的阶段分析（趋势、转移等）
    """
    try:
        bot = get_or_create_chatbot(user_id)
        state_data = state_manager.load_user_state(user_id)
        
        # 获取最近的阶段序列
        recent_stages = [s for _, s, _ in state_data['stage_history'][-30:]]
        
        # 计算阶段分布
        stage_counts = {}
        for stage in ['denial', 'anger', 'bargaining', 'depression', 'acceptance']:
            stage_counts[stage] = recent_stages.count(stage)
        
        # 计算接受阶段的趋势
        acceptance_ratio = stage_counts['acceptance'] / len(recent_stages) if recent_stages else 0
        
        return jsonify({
            'userId': user_id,
            'stageDistribution': stage_counts,
            'acceptanceRatio': f"{acceptance_ratio:.2%}",
            'recentStages': recent_stages,
            'currentStage': state_data['statistics'].get('current_stage', 'unknown'),
            'stageTransitionCount': state_data['statistics'].get('stage_transition_counts', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/reset/<user_id>', methods=['POST'])
def reset_user_api(user_id):
    """
    重置用户的聊天机器人（开始新的对话）
    """
    try:
        if user_id in user_bots:
            user_bots[user_id].emotion_calc.reset_for_new_conversation()
            user_bots[user_id].stage_detector.stage_history = []
        return jsonify({'status': 'success', 'message': '已重置对话'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status_api():
    """
    系统状态API
    """
    try:
        return jsonify({
            'status': 'running',
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'activeUsers': len(user_bots),
            'message': '情感支持聊天机器人服务正常运行'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """404处理"""
    return index()


if __name__ == '__main__':
    # 确保在正确的目录下运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("🕊️  情感支持聊天机器人 Web 服务")
    print("=" * 60)
    print("✓ 已集成千问AI大模型")
    print("✓ 已启用渐进式衰减机制")
    print("✓ 已支持五阶段悲伤模型")
    print("✓ 已启用用户状态持久化")
    print("=" * 60)
    print("请在浏览器中访问: http://localhost:5000")
    print("API文档: http://localhost:5000/api/status")
    print("=" * 60)
    
    # 启动Flask应用
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )