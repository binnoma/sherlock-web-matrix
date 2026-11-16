#!/usr/bin/env bash
# Sherlock 一键运行脚本
# 用法: ./run.sh <用户名> [更多用户名...]
# 示例: ./run.sh zhangsan
set -euo pipefail
cd "$(dirname "$0")"

if [ $# -lt 1 ]; then
  echo "用法: ./run.sh <用户名> [更多用户名...]"
  exit 1
fi

mkdir -p results
# --local: 使用仓库内置站点库（远程数据源 data.sherlockproject.xyz 在当前网络环境下不可达）
# 默认排除 NSFW 站点；需要包含时加 --nsfw
.venv/bin/python -m sherlock_project \
  --local \
  --csv --xlsx \
  --output results/result \
  --no-color \
  --print-found \
  "$@"

echo
echo "结果已写入 results/ 目录（result.csv / result.xlsx）"
#（注：内容由AI生成）
