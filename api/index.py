"""
Vercel Serverless Function - 情感支持聊天机器人后端
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sys
import os
from datetime import datetime
import io

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, '..'))

try:
    from grief_chatbot.chatbot import GriefSupportChatbot
    from user_state_manager import UserStateManager
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False
    print("警告：后端模块未找到，将使用模拟响应")

app = Flask(__name__)
CORS(app)

# 创建全局实例
if HAS_BACKEND:
    state_manager = UserStateManager()
    user_bots = {}
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


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat_api():
    """聊天API接口 - 核心接口"""
    if request.method == 'OPTIONS':
        return '', 204
    
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
