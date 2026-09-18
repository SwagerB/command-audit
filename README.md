# Command Audit

用 Python + AWS 记录、分析和可视化 Linux 命令执行的审计工具。

## 功能

- 自动记录：时间、命令、退出码
- 云端存储：DynamoDB + S3
- 可视化报告：折线图、环形图、柱状图
- 多维统计：今日 / 本周 / 全部
- 命令简化：`ls -la /root` 归类为 `ls`
- 自动刷新：后台每 60 秒更新
- 查询接口：命令行按类型、命令、时间段查询

## 快速开始（LocalStack）

1. 启动 LocalStack
2. 安装依赖 `pip install -r requirements.txt`
3. 配置环境变量（AWS_ACCESS_KEY_ID / SECRET / REGION）
4. 创建 DynamoDB 表 AuditLogs
5. 创建 S3 桶 audit-reports-2026
6. 执行 `bash scripts/start_audit.sh`

浏览器打开 `http://localhost:8000`

## 项目结构

```
command-audit/
├── src/                        核心 Python 脚本
│   ├── audit.py                采集命令 + 写入 DynamoDB
│   ├── generate_report.py      生成 HTML 报告 + 上传 S3
│   ├── query_audit.py          命令行查询接口
│   └── app.py                  Flask 后端（拖拽上传 + 文件服务）
├── scripts/                    shell 启动脚本
│   ├── audit_setup.sh          命令记录配置（写入 .bashrc）
│   ├── start_audit.sh          一键启动 HTTP + 自动刷新
│   └── auto_refresh.sh         定时刷新任务
├── templates/                  HTML 模板
│   └── upload.html             拖拽上传页面
├── docs/                       文档与截图
│   └── screenshots/
├── requirements.txt            Python 依赖
├── config.example.yaml         配置模板
├── .gitignore                  Git 忽略规则
├── LICENSE                     MIT 协议
└── README.md                   本文件
```


## License

MIT