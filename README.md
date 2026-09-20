# Command Audit

用 Python + LocalStack（本地模拟 AWS）记录、分析和可视化 Linux 命令执行的审计工具。

基于 AWS 的 DynamoDB、S3、IAM，可无缝迁移到真实 AWS 环境。

## 克隆项目

从 GitHub 克隆到本地：

```bash
git clone git@github.com:SwagerB/command-audit.git
cd command-audit
```

> 如果没配置 SSH，也可以用 HTTPS：
> ```bash
> git clone https://github.com/SwagerB/command-audit.git
> ```

克隆后，按下方「快速开始」安装依赖并启动。

## 功能

- **自动记录**：时间、命令、退出码，全部落盘
- **云端存储**：写入 DynamoDB，报告上传 S3
- **可视化报告**：HTML 页面，含折线图、环形图、柱状图
- **多维统计**：今日 / 本周 / 全部，成功 vs 失败
- **命令简化**：`ls -la /root` 归类为 `ls`，避免参数不同被拆散
- **自动刷新**：后台每 60 秒更新一次
- **查询接口**：命令行按类型、命令、时间段查询

## 快速开始（LocalStack）

### 1. 启动 LocalStack

```bash
docker run -d --name localstack \
  -p 4566:4566 \
  -e SERVICES=s3,dynamodb,iam \
  localstack/localstack
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 创建 DynamoDB 表

```bash
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
  --table-name AuditLogs \
  --attribute-definitions \
    AttributeName=date,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=date,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

### 4. 创建 S3 桶

```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://audit-reports-2026
```

### 5. 一键启动

```bash
bash scripts/start_audit.sh
```

脚本会自动设置环境变量、启用命令记录、启动后台服务。

### 6. 打开报告

浏览器访问：

```
http://localhost:8000
```

## 项目结构

```
command-audit/
├── src/                        核心 Python 脚本
│   ├── audit.py                采集命令 + 写入 DynamoDB
│   ├── generate_report.py      生成 HTML 报告 + 上传 S3
│   ├── query_audit.py          命令行查询接口
│   └── app.py                  Flask 后端（提供报告 Web 服务）
├── scripts/                    shell 脚本
│   ├── audit_setup.sh          命令记录配置（写入 .bashrc）
│   ├── start_audit.sh          一键启动（含环境变量配置）
│   └── auto_refresh.sh         定时刷新任务
├── data/                       运行时生成（已 gitignore）
│   ├── commands.log
│   ├── reports/
│   └── *.log
├── requirements.txt            Python 依赖
├── config.example.yaml         配置模板
├── .gitignore                  Git 忽略规则
├── LICENSE                     MIT 协议
└── README.md                   本文件
```

## 配置（可选）

`start_audit.sh` 已内置 LocalStack 的默认配置，**开箱即用**。

如果要连接真实 AWS，或改桶名、表名，可以在执行脚本**之前**先 export 环境变量：

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `AWS_ENDPOINT_URL` | `http://localhost:4566` | 真实 AWS 设为空字符串 |
| `AWS_DEFAULT_REGION` | `us-east-1` | 区域 |
| `AWS_ACCESS_KEY_ID` | `test` | 访问密钥 |
| `AWS_SECRET_ACCESS_KEY` | `test` | 秘密密钥 |
| `AUDIT_DDB_TABLE` | `AuditLogs` | DynamoDB 表名 |
| `AUDIT_S3_BUCKET` | `audit-reports-2026` | S3 桶名 |

示例（连接真实 AWS）：

```bash
export AWS_ENDPOINT_URL=""
export AWS_DEFAULT_REGION="ap-northeast-1"
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AUDIT_S3_BUCKET="my-audit-bucket"
bash scripts/start_audit.sh
```

## 常用命令

```bash
# 手动刷新一次
python3 src/audit.py
python3 src/generate_report.py

# 查询
python3 src/query_audit.py --today
python3 src/query_audit.py --week
python3 src/query_audit.py --type 命令未找到
```

## License

MIT