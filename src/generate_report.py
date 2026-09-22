import os
import json
import time
import boto3
from pathlib import Path
from datetime import datetime

# ============ 路径 ============
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
REPORT_DIR = DATA_DIR / 'reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ============ AWS 配置 ============
ENDPOINT = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
DDB_TABLE = os.getenv('AUDIT_DDB_TABLE', 'AuditLogs')
S3_BUCKET = os.getenv('AUDIT_S3_BUCKET', 'audit-reports-2026')

CREDS = dict(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
)


# DynamoDB 跑在 LocalStack 上，容器重启会丢数据。
# 这里把扫描结果落到本地做备份，如果哪天表被清空就自动回灌。
BACKUP_FILE = DATA_DIR / 'records_backup.json'


def get_client():
    return boto3.client('dynamodb', endpoint_url=ENDPOINT,
                        region_name=REGION, **CREDS)


def load_backup():
    try:
        with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_backup(items):
    if not items:
        return
    tmp = BACKUP_FILE.with_name(BACKUP_FILE.name + '.tmp')
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)
        tmp.replace(BACKUP_FILE)
    except Exception as ex:
        print(f"本地备份写入失败: {ex}")


def restore_backup(backup):
    client = get_client()
    done = 0
    for item in backup:
        try:
            client.put_item(TableName=DDB_TABLE, Item=item)
            done += 1
        except Exception as ex:
            print(f"回灌失败: {ex}")
    return done


def scan_all():
    client = get_client()
    items = []
    response = client.scan(TableName=DDB_TABLE)
    items.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = client.scan(
            TableName=DDB_TABLE,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    return items


def item_to_dict(item):
    return {
        'date': item['date']['S'],
        'timestamp': item['timestamp']['S'],
        'command': item['command']['S'],
        'exit_code': int(item['exit_code']['N']),
        'reason': item['reason']['S'],
        'status': item.get('status', {}).get('S', 'error'),
    }


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="60">
<title>命令审计报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "PingFang SC", sans-serif; background: #f5f7fa; margin: 0; padding: 24px; color: #1f2d3d; line-height: 1.5; }
  .container { max-width: 1280px; margin: 0 auto; }
  header { margin-bottom: 20px; }
  header h1 { font-size: 26px; margin: 0 0 4px; }
  header .meta { color: #7f8c8d; font-size: 13px; }

  .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #ecf0f1; }
  .tab { padding: 10px 22px; border: none; background: transparent; cursor: pointer; font-size: 15px; color: #7f8c8d; border-bottom: 2px solid transparent; margin-bottom: -2px; }
  .tab.active { color: #3498db; font-weight: 600; border-bottom-color: #3498db; }

  .cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 20px; }
  .card { background: #fff; padding: 18px 22px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
  .card .num { font-size: 30px; font-weight: 700; line-height: 1; }
  .card .num.danger { color: #e74c3c; }
  .card .num.success { color: #27ae60; }
  .card .num.accent { color: #3498db; }
  .card .label { color: #7f8c8d; font-size: 13px; margin-top: 8px; }

  .charts { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 20px; }
  .chart-box { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
  .chart-box h3 { margin: 0 0 14px; font-size: 15px; font-weight: 600; }
  .two-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }

  .table-wrap { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow: hidden; }
  .table-header { padding: 16px 20px; border-bottom: 1px solid #ecf0f1; display: flex; justify-content: space-between; align-items: center; }
  .table-header h3 { margin: 0; font-size: 15px; }
  .table-header .count { color: #7f8c8d; font-size: 13px; }

  .filter-btns { display: flex; gap: 6px; background: #f1f3f5; border-radius: 8px; padding: 3px; }
  .filter-btn { padding: 5px 14px; border: none; background: transparent; cursor: pointer; font-size: 13px; color: #7f8c8d; border-radius: 6px; }
  .filter-btn.active { background: #fff; color: #1f2d3d; font-weight: 600; }

  table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  th, td { padding: 12px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid #ecf0f1; }
  th:nth-child(1), td:nth-child(1) { width: 180px; }
  th:nth-child(3), td:nth-child(3) { width: 80px; }
  th:nth-child(4), td:nth-child(4) { width: 160px; }
  th { background: #fafbfc; color: #555; font-weight: 600; font-size: 12px; }
  tr:last-child td { border-bottom: none; }

  .cmd-cell { display: block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: monospace; font-size: 12px; background: #f4f6f8; padding: 4px 8px; border-radius: 4px; }

  .code-badge { display: inline-block; min-width: 36px; text-align: center; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; }
  .code-badge.error { background: #fdecea; color: #c0392b; }
  .code-badge.success { background: #eafaf1; color: #27ae60; }
  .reason-badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; }
  .reason-badge.error { background: #eaf3fb; color: #2980b9; }
  .reason-badge.success { background: #eafaf1; color: #27ae60; }
  .empty { padding: 60px 20px; text-align: center; color: #7f8c8d; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>命令审计报告</h1>
    <div class="meta">生成时间: __GENERATED_AT__ ｜ 命令日志最后写入: __LAST_LOG__</div>
  </header>

  <div class="tabs">
    <button class="tab active" data-mode="today">今日</button>
    <button class="tab" data-mode="week">本周</button>
    <button class="tab" data-mode="all">全部</button>
  </div>

  <div class="cards">
    <div class="card"><div class="num accent" id="card-total">0</div><div class="label">总命令数</div></div>
    <div class="card"><div class="num success" id="card-success">0</div><div class="label">成功</div></div>
    <div class="card"><div class="num danger" id="card-error">0</div><div class="label">失败</div></div>
    <div class="card"><div class="num success" id="card-rate">0%</div><div class="label">成功率</div></div>
    <div class="card"><div class="num danger" id="card-types">0</div><div class="label">错误类型</div></div>
  </div>

  <div class="charts">
    <div class="chart-box"><h3>报错趋势</h3><canvas id="dayChart"></canvas></div>
    <div class="chart-box"><h3>成功 vs 失败</h3><canvas id="statusChart"></canvas></div>
    <div class="chart-box"><h3>错误类型分布</h3><canvas id="typeChart"></canvas></div>
  </div>

  <div class="two-charts">
    <div class="chart-box"><h3>最常使用的命令 Top 10</h3><canvas id="usageChart"></canvas></div>
    <div class="chart-box"><h3>最常报错的命令 Top 10</h3><canvas id="cmdChart"></canvas></div>
  </div>

  <div class="table-wrap">
    <div class="table-header">
      <h3>命令明细</h3>
      <div style="display:flex; gap:12px; align-items:center;">
        <div class="filter-btns">
          <button class="filter-btn active" data-filter="all">全部</button>
          <button class="filter-btn" data-filter="error">仅错误</button>
          <button class="filter-btn" data-filter="success">仅成功</button>
        </div>
        <span class="count" id="table-count">0 条</span>
      </div>
    </div>
    <div id="table-container"></div>
  </div>
</div>

<script>
const ALL_RECORDS = __DATA__;
let dayChart, statusChart, typeChart, cmdChart, usageChart;
let currentMode = 'today';
let currentFilter = 'all';

function pad(n) { return String(n).padStart(2, '0'); }
function getTodayStr() { const d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
function getWeekStartStr() { const d = new Date(); const day = d.getDay() || 7; d.setDate(d.getDate() - day + 1); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }

function filterByTime(mode) {
  if (mode === 'today') { const t = getTodayStr(); return ALL_RECORDS.filter(r => r.date === t); }
  if (mode === 'week') { const ws = getWeekStartStr(); return ALL_RECORDS.filter(r => r.date >= ws); }
  return ALL_RECORDS;
}

function countBy(arr, keyFn) { const m = new Map(); arr.forEach(r => { const k = keyFn(r); m.set(k, (m.get(k) || 0) + 1); }); return m; }
function escapeHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

function simplifyCommand(cmd) {
  if (!cmd) return '';
  let parts = cmd.trim().split(/\\s+/);
  if (parts.length === 0) return cmd;
  if (parts[0] === 'sudo' && parts.length > 1) parts = parts.slice(1);
  const base = parts[0];
  const twoLevel = ['aws', 'docker', 'kubectl', 'git', 'npm', 'pip', 'pip3', 'conda'];
  if (twoLevel.includes(base) && parts.length > 1) {
    for (let i = 1; i < parts.length; i++) { if (!parts[i].startsWith('-')) return base + ' ' + parts[i]; }
    return base;
  }
  return base;
}

function renderCards(records) {
  const success = records.filter(r => r.exit_code === 0);
  const errors = records.filter(r => r.exit_code !== 0);
  const typeCounter = countBy(errors, r => r.reason);
  document.getElementById('card-total').textContent = records.length;
  document.getElementById('card-success').textContent = success.length;
  document.getElementById('card-error').textContent = errors.length;
  document.getElementById('card-rate').textContent = records.length ? (success.length / records.length * 100).toFixed(1) + '%' : '0%';
  document.getElementById('card-types').textContent = typeCounter.size;
}

function renderCharts(records) {
  if (dayChart) dayChart.destroy();
  if (statusChart) statusChart.destroy();
  if (typeChart) typeChart.destroy();
  if (cmdChart) cmdChart.destroy();
  if (usageChart) usageChart.destroy();

  const errors = records.filter(r => r.exit_code !== 0);

  const dayCounter = countBy(errors, r => r.date);
  const days = Array.from(dayCounter.keys()).sort();
  const dayVals = days.map(d => dayCounter.get(d));
  dayChart = new Chart(document.getElementById('dayChart'), {
    type: 'line',
    data: { labels: days.length ? days : ['无数据'], datasets: [{ label: '报错次数', data: dayVals.length ? dayVals : [0], borderColor: '#e74c3c', backgroundColor: 'rgba(231,76,60,0.12)', fill: true, tension: 0.3, pointRadius: 4 }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
  });

  const sc = records.filter(r => r.exit_code === 0).length;
  const ec = records.length - sc;
  statusChart = new Chart(document.getElementById('statusChart'), {
    type: 'doughnut',
    data: { labels: ['成功', '失败'], datasets: [{ data: [sc, ec], backgroundColor: ['#27ae60', '#e74c3c'] }] },
    options: { plugins: { legend: { position: 'bottom' } } }
  });

  const typeCounter = countBy(errors, r => r.reason);
  const types = Array.from(typeCounter.entries()).sort((a, b) => b[1] - a[1]);
  typeChart = new Chart(document.getElementById('typeChart'), {
    type: 'doughnut',
    data: { labels: types.length ? types.map(t => t[0]) : ['无错误'], datasets: [{ data: types.length ? types.map(t => t[1]) : [1], backgroundColor: types.length ? ['#e74c3c','#e67e22','#f1c40f','#3498db','#9b59b6','#1abc9c','#34495e','#95a5a6'] : ['#ecf0f1'] }] },
    options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } } }
  });

  const usageCounter = countBy(records, r => simplifyCommand(r.command));
  const usages = Array.from(usageCounter.entries()).sort((a, b) => b[1] - a[1]).slice(0, 10);
  usageChart = new Chart(document.getElementById('usageChart'), {
    type: 'bar',
    data: { labels: usages.length ? usages.map(u => u[0]) : ['无数据'], datasets: [{ label: '使用次数', data: usages.length ? usages.map(u => u[1]) : [0], backgroundColor: '#3498db', borderRadius: 4 }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } }
  });

  const cmdCounter = countBy(errors, r => simplifyCommand(r.command));
  const cmds = Array.from(cmdCounter.entries()).sort((a, b) => b[1] - a[1]).slice(0, 10);
  cmdChart = new Chart(document.getElementById('cmdChart'), {
    type: 'bar',
    data: { labels: cmds.length ? cmds.map(c => c[0]) : ['无数据'], datasets: [{ label: '报错次数', data: cmds.length ? cmds.map(c => c[1]) : [0], backgroundColor: '#e74c3c', borderRadius: 4 }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } }
  });
}

function renderTable(records) {
  const container = document.getElementById('table-container');
  const count = document.getElementById('table-count');
  let filtered = records;
  if (currentFilter === 'error') filtered = records.filter(r => r.exit_code !== 0);
  else if (currentFilter === 'success') filtered = records.filter(r => r.exit_code === 0);
  count.textContent = filtered.length + ' 条';
  if (filtered.length === 0) { container.innerHTML = '<div class="empty">该范围内没有命令记录</div>'; return; }
  const rows = filtered.slice().sort((a, b) => b.timestamp.localeCompare(a.timestamp)).map(r => {
    const cmd = escapeHtml(r.command);
    const status = r.exit_code === 0 ? 'success' : 'error';
    return '<tr><td>' + r.timestamp + '</td><td><span class="cmd-cell" title="' + cmd + '">' + cmd + '</span></td><td><span class="code-badge ' + status + '">' + r.exit_code + '</span></td><td><span class="reason-badge ' + status + '">' + escapeHtml(r.reason) + '</span></td></tr>';
  }).join('');
  container.innerHTML = '<table><thead><tr><th>时间</th><th>命令</th><th>退出码</th><th>原因</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

function render() {
  const records = filterByTime(currentMode);
  renderCards(records);
  renderCharts(records);
  renderTable(records);
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    currentMode = tab.dataset.mode;
    render();
  });
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    render();
  });
});

render();
</script>
</body>
</html>
'''


def build_html(records):
    data_json = json.dumps(records, ensure_ascii=False)
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return (HTML_TEMPLATE
            .replace('__DATA__', data_json)
            .replace('__GENERATED_AT__', generated_at)
            .replace('__LAST_LOG__', last_log_html()))


def last_log_html():
    """命令日志最后写入时间 + 距今多久。页面上一眼分清是「没在记录」还是「页面没刷新」。"""
    log_file = DATA_DIR / 'commands.log'
    try:
        age_min = int((time.time() - log_file.stat().st_mtime) / 60)
        last = ''
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.strip():
                    last = line.strip()
        ts = last.split('|', 1)[0] if last else '（日志为空）'
        if age_min < 10:
            color = '#27ae60'
        elif age_min < 60:
            color = '#e67e22'
        else:
            color = '#e74c3c'
        return (f'<span style="color:{color};font-weight:600">{ts}'
                f'（{age_min} 分钟前）</span>')
    except OSError:
        return '<span style="color:#e74c3c">暂无命令日志</span>'


def main():
    backup = load_backup()

    try:
        items = scan_all()
    except Exception as ex:
        # DynamoDB 连不上时，退化成用本地备份出报告，页面不至于变空
        print(f"DynamoDB 不可用: {ex}")
        if not backup:
            print("没有本地备份，保留上一版报告不覆盖。")
            return
        items = backup

    # 表被重置（例如 LocalStack 重启）时自动回灌备份。
    # 只在“整表清空”或“丢了一大截(>20%)”时触发，
    # 免得手工删掉几条记录又被自动救回来。
    if backup:
        lost = len(backup) - len(items)
        if lost > 0 and (len(items) == 0 or lost >= max(1, int(len(backup) * 0.2))):
            print(f"DynamoDB 记录数 {len(items)} < 本地备份 {len(backup)}，判定为数据丢失，正在回灌…")
            restored = restore_backup(backup)
            print(f"已回灌 {restored} 条")
            try:
                items = scan_all()
            except Exception as ex:
                print(f"回灌后重扫失败，改用备份: {ex}")
                items = backup

    records = [item_to_dict(i) for i in items]
    save_backup(items)

    html = build_html(records)

    local_path = REPORT_DIR / 'index.html'
    with open(local_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML 报告已更新: {local_path}")
    print(f"记录数: {len(records)}")

    client = boto3.client('s3', endpoint_url=ENDPOINT, region_name=REGION, **CREDS)
    key = 'reports/index.html'
    try:
        client.upload_file(str(local_path), S3_BUCKET, key)
        print(f"已上传 S3: s3://{S3_BUCKET}/{key}")
    except Exception as ex:
        print(f"S3 上传失败: {ex}")


if __name__ == '__main__':
    main()