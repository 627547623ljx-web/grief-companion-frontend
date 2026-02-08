"""
Flask后端服务
为情感支持聊天机器人提供API接口
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grief_chatbot.chatbot import GriefSupportChatbot


app = Flask(__name__)

# 创建全局聊天机器人实例
chatbot = GriefSupportChatbot()


@app.route('/')
def index():
    """主页路由"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """静态文件路由"""
    return send_from_directory('.', path)


@app.route('/api/chat', methods=['POST'])
def chat_api():
    """
    聊天API接口
    接收用户消息并返回机器人回复
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        user_id = data.get('userId', 'default_user')
        
        if not user_message:
            return jsonify({
                'error': '消息不能为空'
            }), 400
        
        # 生成机器人回复
        response, stage_info = chatbot.generate_response(user_message)
        
        # 解析stage_info获取阶段名称
        stage_parts = stage_info.split(',')
        stage_name = stage_parts[0].split(':')[1].strip() if len(stage_parts) > 0 else "未知"
        
        # 返回响应数据
        return jsonify({
            'response': response,
            'stageInfo': stage_name,
            'moodIndex': f"{chatbot.emotion_calc.M_t:.1f}",
            'emotionAnalysis': f"当前心情指数: {chatbot.emotion_calc.M_t:.1f}, 阶段: {stage_name}"
        })
        
    except Exception as e:
        app.logger.error(f"Chat API error: {str(e)}")
        return jsonify({
            'error': '处理消息时发生错误'
        }), 500


@app.route('/api/status', methods=['GET'])
def status_api():
    """
    状态API接口
    返回当前系统状态
    """
    return jsonify({
        'status': 'running',
        'mood_index': chatbot.emotion_calc.M_t,
        'stage': chatbot.emotion_calc.get_current_stage(),
        'timestamp': chatbot.emotion_calc.last_update_time.isoformat()
    })


if __name__ == '__main__':
    # 确保在正确的目录下运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("正在启动情感支持聊天机器人Web服务...")
    print("请在浏览器中访问 http://localhost:5000")
    
    # 启动Flask应用
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # 生产环境中应关闭debug模式
        threaded=True
    )