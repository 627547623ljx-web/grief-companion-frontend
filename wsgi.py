"""
WSGI entry point for Vercel deployment
"""
from api.index import app

# Vercel使用这个作为WSGI应用入口
application = app

if __name__ == '__main__':
    app.run()
