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

脚本会自动：设置环境变量 → 安装命令记录钩子（写入 `~/.zshrc` / `~/.bashrc`）→ 启动自动刷新 + Flask 服务。

> **新开一个终端**（或 `source ~/.zshrc`）后，命令记录才会在你日常用的终端里生效。

### 6. 打开报告

浏览器访问：

```
http://localhost:8000
```

页面每 60 秒自动刷新一次（与后台刷新节奏一致）。

### 7. （推荐）交给系统托管

`nohup` 启动的进程在关掉终端 / 重启后就没了，页面就会“不刷新”。用 macOS 自带的 launchd 托管即可开机自启、崩溃自动拉起：

```bash
bash scripts/install_daemons.sh     # 安装并启动（幂等，可重复执行）
bash scripts/uninstall_daemons.sh   # 卸载
launchctl list | grep commandaudit  # 查看状态
```

## 命令记录原理

`scripts/audit_setup.sh` 同时兼容两种 shell，被 source 后注册钩子：

| shell | 钩子 | 说明 |
|---|---|---|
| zsh | `preexec` + `precmd` | 分别取“命令原文”和“退出码”，放在钩子数组首位以免 `$?` 被其它插件覆盖 |
| bash | `PROMPT_COMMAND` | `history 1` 取上一条命令 + `$?` |

每条记录写成一行追加到 `data/commands.log`：

```
2026-09-22 11:26:14|0|uptime
```

格式为 `时间|退出码|命令`。重复 source 不会重复注册，且不会记录钩子自身的命令。

安装 / 更新钩子（幂等，会先删旧块再写新块）：

```bash
bash scripts/install_hooks.sh
```

## 数据可靠性

- DynamoDB 跑在 LocalStack 上，容器重启会丢数据；
- 每次刷新会把全量记录备份到 `data/records_backup.json`；
- 如果发现表里的记录数少于备份，会自动回灌，页面不会一夜之间被清空。

## 项目结构

```
command-audit/
├── src/                        核心 Python 脚本
│   ├── audit.py                采集命令 + 写入 DynamoDB
│   ├── generate_report.py      生成 HTML 报告 + 本地备份 + 上传 S3
│   ├── query_audit.py          命令行查询接口
│   └── app.py                  Flask 后端（提供报告 Web 服务）
├── scripts/                    shell 脚本
│   ├── audit_setup.sh          命令记录钩子（zsh / bash 双兼容）
│   ├── install_hooks.sh        把钩子幂等写入 ~/.zshrc、~/.bashrc
│   ├── start_audit.sh          一键启动（环境变量 + 钩子 + 服务）
│   ├── auto_refresh.sh         定时刷新任务
│   ├── install_daemons.sh      用 launchd 托管常驻服务
│   └── uninstall_daemons.sh    卸载 launchd 托管
├── data/                       运行时生成（已 gitignore）
│   ├── commands.log            命令原始记录（时间|退出码|命令）
│   ├── records_backup.json     全量记录本地备份（DynamoDB 的兜底）
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
# 安装 / 更新命令记录钩子（写入 ~/.zshrc、~/.bashrc）
bash scripts/install_hooks.sh

# 一键启动（或交给 launchd 常驻）
bash scripts/start_audit.sh
bash scripts/install_daemons.sh

# 手动刷新一次
python3 src/audit.py
python3 src/generate_report.py

# 查询
python3 src/query_audit.py --today
python3 src/query_audit.py --week
python3 src/query_audit.py --type 命令未找到
```

## 排障

| 现象 | 原因 / 处理 |
|---|---|
| 页面数字一直不变 | 先看 `data/commands.log` 有没有新行。没有 → 钩子没装，跑 `bash scripts/install_hooks.sh` 后**新开终端** |
| 命令没被记录 | 确认当前 shell 已加载钩子：zsh 下 `echo $precmd_functions` 应包含 `__audit_precmd` |
| 页面 404 / 打不开 | 服务没在跑：`bash scripts/start_audit.sh`，或 `launchctl list \| grep commandaudit` |
| 记录数突然变少 | LocalStack 被重启过，`generate_report.py` 会自动用 `data/records_backup.json` 回灌 |

## License

MIT