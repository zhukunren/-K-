#!/bin/bash
# 项目清理脚本 - 减少项目体积用于迁移
# 保留：源代码、预测结果、模型、文档
# 删除：虚拟环境、node_modules、构建产物、缓存

echo "=========================================="
echo "项目清理脚本 - 用于设备迁移"
echo "=========================================="

cd "$(dirname "$0")"

# 显示清理前大小
echo ""
echo "清理前项目大小："
du -sh .

echo ""
echo "将要删除的内容："
echo "  - venv/ (Python虚拟环境, ~7.4GB)"
echo "  - frontend/node_modules/ (前端依赖)"
echo "  - frontend/dist/ (前端构建产物)"
echo "  - backend/__pycache__/ (Python缓存)"
echo "  - .git/ (Git历史, ~219MB)"
echo "  - *.log 日志文件"
echo "  - *.zip 备份文件"
echo ""
echo "将保留的内容："
echo "  - 所有源代码 (backend/*.py, frontend/src/)"
echo "  - 预训练模型 (backend/models/)"
echo "  - 模型缓存 (backend/model_cache/) - 含预测结果"
echo "  - 评估缓存 (backend/logs/evaluation_cache*.json)"
echo "  - 文档 (docs/)"
echo "  - 配置文件 (requirements.txt, package.json等)"
echo ""

read -p "确认删除? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "开始清理..."

# 删除 Python 虚拟环境
if [ -d "venv" ]; then
    echo "删除 venv/..."
    rm -rf venv
fi

# 删除前端依赖和构建产物
if [ -d "frontend/node_modules" ]; then
    echo "删除 frontend/node_modules/..."
    rm -rf frontend/node_modules
fi

if [ -d "frontend/dist" ]; then
    echo "删除 frontend/dist/..."
    rm -rf frontend/dist
fi

# 删除 Python 缓存
echo "删除 __pycache__/..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 删除 .git 历史（可选，取消注释以启用）
if [ -d ".git" ]; then
    echo "删除 .git/..."
    rm -rf .git
fi

# 删除日志文件
echo "删除日志文件..."
rm -f logs/*.log logs/*.pid 2>/dev/null
rm -f *.log 2>/dev/null

# 删除备份压缩包
echo "删除备份压缩包..."
rm -f *.zip 2>/dev/null

# 删除 IDE 缓存
rm -rf .vite 2>/dev/null
rm -rf frontend/.vite 2>/dev/null

echo ""
echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo ""
echo "清理后项目大小："
du -sh .

echo ""
echo "保留的重要文件："
echo "  - backend/models/transformer_autoencoder.pt (核心模型)"
echo "  - backend/model_cache/*.pkl (训练缓存)"
echo "  - backend/logs/evaluation_cache.json (评估结果)"
echo ""
echo "迁移后恢复步骤："
echo "  1. 创建虚拟环境: python3 -m venv venv"
echo "  2. 激活虚拟环境: source venv/bin/activate"
echo "  3. 安装后端依赖: pip install -r requirements.txt"
echo "  4. 安装前端依赖: cd frontend && npm install"
echo "  5. 构建前端: npm run build"
echo "  6. 启动服务: ./启动服务.sh"
