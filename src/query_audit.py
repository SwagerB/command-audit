import argparse
import boto3
from datetime import datetime, timedelta
from collections import Counter

ENDPOINT = 'http://localhost:4566'
REGION = 'us-east-1'
CREDS = dict(aws_access_key_id='test', aws_secret_access_key='test')
DDB_TABLE = 'AuditLogs'


def get_client():
    return boto3.client('dynamodb', endpoint_url=ENDPOINT,
                        region_name=REGION, **CREDS)


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
    }


def filter_by_time(records, mode):
    today = datetime.now().date()
    if mode == 'today':
        return [r for r in records if r['date'] == today.strftime('%Y-%m-%d')]
    if mode == 'week':
        start = today - timedelta(days=today.weekday())
        return [r for r in records
                if datetime.strptime(r['date'], '%Y-%m-%d').date() >= start]
    if mode == 'month':
        return [r for r in records
                if r['date'].startswith(today.strftime('%Y-%m'))]
    return records


def filter_by_type(records, keyword):
    if not keyword:
        return records
    return [r for r in records if keyword in r['reason']]


def filter_by_command(records, keyword):
    if not keyword:
        return records
    return [r for r in records if keyword in r['command']]


def print_records(records, title):
    print("=" * 70)
    print(f"查询结果: {title}")
    print("=" * 70)
    print(f"共 {len(records)} 条")
    print()

    if not records:
        print("没有匹配的记录。")
        return

    type_counter = Counter(r['reason'] for r in records)
    print("错误类型分布:")
    for reason, count in type_counter.most_common():
        print(f"  {count:>3} 次  -  {reason}")
    print()

    cmd_counter = Counter(r['command'] for r in records)
    print("最常报错的命令 Top 10:")
    for cmd, count in cmd_counter.most_common(10):
        print(f"  {count:>3} 次  -  {cmd}")
    print()

    print("明细:")
    print("-" * 70)
    for r in sorted(records, key=lambda x: x['timestamp'], reverse=True):
        print(f"[{r['timestamp']}]  退出码={r['exit_code']}")
        print(f"  命令: {r['command']}")
        print(f"  原因: {r['reason']}")
        print()


def main():
    parser = argparse.ArgumentParser(description='查询审计日志')
    parser.add_argument('--today', action='store_true', help='查今天')
    parser.add_argument('--week', action='store_true', help='查本周')
    parser.add_argument('--month', action='store_true', help='查本月')
    parser.add_argument('--all', action='store_true', help='查全部')
    parser.add_argument('--type', type=str, help='按错误类型过滤')
    parser.add_argument('--command', type=str, help='按命令关键词过滤')

    args = parser.parse_args()

    mode = 'all'
    title = '全部'
    if args.today:
        mode, title = 'today', '今天'
    elif args.week:
        mode, title = 'week', '本周'
    elif args.month:
        mode, title = 'month', '本月'

    records = [item_to_dict(i) for i in scan_all()]
    records = filter_by_time(records, mode)
    records = filter_by_type(records, args.type)
    records = filter_by_command(records, args.command)

    print_records(records, title)


if __name__ == '__main__':
    main()