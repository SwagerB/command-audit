import os
import boto3
from pathlib import Path
from datetime import datetime
from collections import Counter

# ============ 路径（自动定位到项目根目录） ============
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
REPORT_DIR = DATA_DIR / 'reports'
LOG_FILE = DATA_DIR / 'commands.log'

DATA_DIR.mkdir(parents=True, exist_ok=True)
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

EXIT_CODE_MAP = {
    1: '通用错误',
    2: '参数或路径错误',
    126: '无执行权限',
    127: '命令未找到',
    130: '用户中断 (Ctrl+C)',
    137: '进程被杀死 (OOM等)',
    139: '段错误',
    254: 'AWS API 错误',
}


def classify_error(exit_code, command):
    if command.strip().startswith('aws ') or ' aws ' in command:
        if exit_code == 254:
            return 'AWS API 错误'
        if exit_code == 2:
            return 'AWS 参数错误'
        if exit_code == 255:
            return 'AWS CLI 错误'
    return EXIT_CODE_MAP.get(exit_code, f'未知错误 (退出码 {exit_code})')


def parse_log(path):
    records = []
    if not os.path.exists(path):
        print(f"日志文件不存在: {path}")
        return records
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|', 2)
            if len(parts) != 3:
                continue
            ts, ec, cmd = parts
            try:
                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                ec = int(ec)
            except ValueError:
                continue
            records.append({
                'timestamp': dt,
                'exit_code': ec,
                'command': cmd.strip(),
            })
    return records


def get_week_key(dt):
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def build_report_text(records):
    now = datetime.now()
    errors = [r for r in records if r['exit_code'] != 0]
    success = [r for r in records if r['exit_code'] == 0]

    lines = []
    lines.append("=" * 70)
    lines.append("命令审计报告")
    lines.append(f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append(f"总命令数  : {len(records)}")
    lines.append(f"成功命令数: {len(success)}")
    lines.append(f"报错命令数: {len(errors)}")
    if records:
        rate = len(success) / len(records) * 100
        lines.append(f"成功率    : {rate:.1f}%")
    lines.append("")

    if not errors:
        lines.append("没有错误记录。")
        return "\n".join(lines)

    day_counter = Counter(e['timestamp'].date() for e in errors)
    today = now.date()
    this_week = get_week_key(now)
    week_errors = sum(
        c for d, c in day_counter.items()
        if get_week_key(datetime.combine(d, datetime.min.time())) == this_week
    )

    lines.append("错误次数统计:")
    lines.append(f"  今天:  {day_counter.get(today, 0)} 次")
    lines.append(f"  本周:  {week_errors} 次")
    lines.append(f"  总计:  {len(errors)} 次")
    lines.append("")

    lines.append("按天统计:")
    for d in sorted(day_counter.keys(), reverse=True):
        lines.append(f"  {d}  {day_counter[d]} 次")
    lines.append("")

    week_counter = Counter(get_week_key(e['timestamp']) for e in errors)
    lines.append("按周统计:")
    for w in sorted(week_counter.keys(), reverse=True):
        lines.append(f"  {w}  {week_counter[w]} 次")
    lines.append("")

    type_counter = Counter(e['reason'] for e in errors)
    lines.append("错误类型分布:")
    for reason, count in type_counter.most_common():
        lines.append(f"  {count:>3} 次  -  {reason}")
    lines.append("")

    cmd_counter = Counter(e['command'] for e in errors)
    lines.append("最常报错的命令 Top 10:")
    for cmd, count in cmd_counter.most_common(10):
        lines.append(f"  {count:>3} 次  -  {cmd}")
    lines.append("")

    lines.append("错误明细:")
    lines.append("-" * 70)
    for e in errors:
        lines.append(f"[{e['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}]")
        lines.append(f"  命令:   {e['command']}")
        lines.append(f"  退出码: {e['exit_code']}")
        lines.append(f"  原因:   {e['reason']}")
        lines.append("")

    return "\n".join(lines)


def save_to_dynamodb(records):
    if not records:
        print("没有命令需要写入 DynamoDB。")
        return
    client = boto3.client('dynamodb', endpoint_url=ENDPOINT,
                          region_name=REGION, **CREDS)
    written = 0
    for r in records:
        date_str = r['timestamp'].strftime('%Y-%m-%d')
        ts_str = r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        status = 'success' if r['exit_code'] == 0 else 'error'
        try:
            client.put_item(
                TableName=DDB_TABLE,
                Item={
                    'date': {'S': date_str},
                    'timestamp': {'S': ts_str},
                    'command': {'S': r['command']},
                    'exit_code': {'N': str(r['exit_code'])},
                    'reason': {'S': r['reason']},
                    'status': {'S': status},
                }
            )
            written += 1
        except Exception as ex:
            print(f"写入失败 [{ts_str}]: {ex}")
    print(f"已写入 DynamoDB: {written} 条（成功+错误）")


def upload_report_to_s3(report_text):
    local_path = REPORT_DIR / 'audit_report.txt'
    with open(local_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    client = boto3.client('s3', endpoint_url=ENDPOINT,
                          region_name=REGION, **CREDS)
    key = 'reports/audit_report.txt'
    try:
        client.upload_file(str(local_path), S3_BUCKET, key)
        print(f"报告已上传 S3: s3://{S3_BUCKET}/{key}")
    except Exception as ex:
        print(f"S3 上传失败: {ex}")
    print(f"本地报告: {local_path}")


if __name__ == '__main__':
    records = parse_log(str(LOG_FILE))
    for r in records:
        if r['exit_code'] == 0:
            r['reason'] = '成功'
        else:
            r['reason'] = classify_error(r['exit_code'], r['command'])

    report_text = build_report_text(records)
    print(report_text)

    print("=" * 70)
    print("持久化")
    print("=" * 70)
    save_to_dynamodb(records)
    upload_report_to_s3(report_text)