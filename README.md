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
command-audit/
├── src/ 核心 Python 脚本
├── scripts/ shell 启动脚本
├── templates/ HTML 模板
├── requirements.txt
├── config.example.yaml
└── README.md


## License

MIT