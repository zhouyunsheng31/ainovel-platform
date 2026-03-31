#!/bin/bash
# AI小说拆书系统 - 后端启动脚本

echo "==================================="
echo "AI小说拆书系统 - 后端服务启动"
echo "==================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

# 检查依赖
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装/更新依赖..."
pip install -r requirements.txt

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "警告: 未找到.env文件，使用默认配置"
    cp .env.example .env
    echo "请编辑.env文件配置API密钥"
fi

# 创建数据目录
mkdir -p data/uploads

echo "启动FastAPI服务..."
python main.py
