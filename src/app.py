from flask import Flask, request, send_from_directory, jsonify, Response
import subprocess

app = Flask(__name__)

REPORT_DIR = '/root/audit_logs/reports'
UPLOAD_PAGE = '/root/upload.html'

FILE_2025 = '/root/23级2025年秋季学期综测成绩.xlsx'
FILE_2026 = '/root/23级2026年春季学期综测成绩.xlsx'


@app.route('/')
def index():
    with open(UPLOAD_PAGE, 'r', encoding='utf-8') as f:
        return Response(f.read(), mimetype='text/html')


@app.route('/upload', methods=['POST'])
def upload():
    f2025 = request.files.get('file2025')
    f2026 = request.files.get('file2026')
    if not f2025 or not f2026:
        return jsonify({'ok': False, 'msg': '请上传两个文件'}), 400

    f2025.save(FILE_2025)
    f2026.save(FILE_2026)

    r1 = subprocess.run(['python3', '/root/award_filter.py'],
                        capture_output=True, text=True)
    if r1.returncode != 0:
        return jsonify({
            'ok': False,
            'msg': 'award_filter.py 执行失败',
            'log': r1.stdout + '\n' + r1.stderr
        }), 500

    r2 = subprocess.run(['python3', '/root/awards_report.py'],
                        capture_output=True, text=True)
    if r2.returncode != 0:
        return jsonify({
            'ok': False,
            'msg': 'awards_report.py 执行失败',
            'log': r2.stdout + '\n' + r2.stderr
        }), 500

    return jsonify({
        'ok': True,
        'log': r1.stdout + '\n' + r2.stdout
    })


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(REPORT_DIR, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)