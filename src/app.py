from flask import Flask, send_from_directory, jsonify, Response
from pathlib import Path
import subprocess
import sys

app = Flask(__name__)

# ============ 路径 ============
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
REPORT_DIR = DATA_DIR / 'reports'
SRC_DIR = PROJECT_ROOT / 'src'

REPORT_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/')
def index():
    """首页：直接显示审计报告"""
    return send_from_directory(str(REPORT_DIR), 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    """提供 data/reports/ 下的静态文件"""
    return send_from_directory(str(REPORT_DIR), filename)


@app.route('/refresh', methods=['POST', 'GET'])
def refresh():
    """手动触发一次刷新：跑 audit.py + generate_report.py"""
    try:
        r1 = subprocess.run(
            [sys.executable, str(SRC_DIR / 'audit.py')],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        r2 = subprocess.run(
            [sys.executable, str(SRC_DIR / 'generate_report.py')],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        return jsonify({
            'ok': r1.returncode == 0 and r2.returncode == 0,
            'audit_output': r1.stdout[-1000:],
            'report_output': r2.stdout[-1000:],
            'errors': (r1.stderr + r2.stderr)[-1000:],
        })
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500


if __name__ == '__main__':
    import os
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '8000'))
    print(f"服务启动: http://localhost:{port}")
    print(f"报告目录: {REPORT_DIR}")
    app.run(host=host, port=port, debug=False)