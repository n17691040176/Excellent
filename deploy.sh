#!/bin/bash
# =============================================
# 生产环境部署脚本
# 使用方法:
#   1. cp .env.prod .env
#   2. 编辑 .env 填入真实密钥
#   3. ./deploy.sh
# =============================================

set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

echo "=========================================="
echo "Excellent App 部署脚本"
echo "=========================================="

# 检查 .env 文件是否存在
if [ ! -f ".env" ]; then
    echo "错误: .env 文件不存在!"
    echo "请先复制模板: cp server/.env.prod server/.env"
    exit 1
fi

if [ ! -f "server/.env.alipay.local" ]; then
    echo "错误: server/.env.alipay.local 不存在!"
    echo "请先填写支付宝配置模板: server/.env.alipay.example"
    exit 1
fi

if ! grep -q '^PAYMENT_MOCK_EXTERNAL_PAYMENT=false' server/.env.alipay.local || \
   ! grep -q '^ALIPAY_ENABLED=true' server/.env.alipay.local; then
    echo "错误: 请在 server/.env.alipay.local 中启用真实支付宝支付"
    exit 1
fi

PAYMENT_SECRETS_DIR="${PAYMENT_SECRETS_DIR:-/www/wwwroot/excellent/secrets}"
for key_file in alipay-merchant-private-key.pem alipay-public-key.pem; do
    if [ ! -f "$PAYMENT_SECRETS_DIR/$key_file" ]; then
        echo "错误: 缺少支付宝密钥文件 $PAYMENT_SECRETS_DIR/$key_file"
        exit 1
    fi
done

# 检查 SECRET_KEY 是否为默认值
if grep -q "YOUR_SECRET_KEY_HERE\|change-me" .env; then
    echo "警告: 检测到默认 SECRET_KEY，请使用强密钥!"
    echo "生成新密钥: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    read -p "是否继续部署? (输入 'yes' 继续): " confirm
    if [ "$confirm" != "yes" ]; then
        exit 1
    fi
fi

echo ""
echo "步骤 1: 拉取阿里云最新镜像..."
"${COMPOSE[@]}" pull server admin-web mobile-app

echo ""
echo "步骤 2: 重建并启动服务..."
"${COMPOSE[@]}" up -d --force-recreate

echo ""
echo "步骤 3: 等待服务就绪..."
sleep 10

echo ""
echo "步骤 4: 检查服务状态..."
"${COMPOSE[@]}" ps

echo ""
echo "步骤 5: 健康检查..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ 后端服务健康"
        break
    fi
    echo "等待服务启动... ($i/30)"
    sleep 2
done

echo ""
echo "=========================================="
echo "部署完成!"
echo ""
echo "访问地址:"
echo "  - 管理后台: http://175.27.228.166"
echo "  - 移动端:   http://175.27.228.166:8080"
echo "  - API:      http://175.27.228.166:8000"
echo ""
echo "查看日志: ${COMPOSE[*]} logs -f"
echo "停止服务: ${COMPOSE[*]} down"
echo "=========================================="
