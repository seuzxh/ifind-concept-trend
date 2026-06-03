#!/bin/bash
# 概念板块强势扫描 - 定时任务启动脚本
# 用法: 由 crontab 调用

PROJ_DIR="/root/Projects/ifind-concept-trend"
PYTHON="/root/Projects/5.test-autoresearch/qlib/miniconda3/envs/concept-trend/bin/python"

cd "$PROJ_DIR" || exit 1

# 加载 .env 环境变量
set -a
source "$PROJ_DIR/.env" 2>/dev/null
set +a

export PYTHONUNBUFFERED=1

exec "$PYTHON" -m scanner "$@"
