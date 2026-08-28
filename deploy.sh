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

read_env_value() {
    local env_file="$1"
    local key="$2"
    if [ ! -f "$env_file" ]; then
        return 0
    fi
    sed -n "s/^${key}=//p" "$env_file" | tail -n 1 | sed 's/\r$//'
}

root_env_value() {
    read_env_value ".env" "$1"
}

is_true() {
    case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
        1|true|yes|on) return 0 ;;
        *) return 1 ;;
    esac
}

PAYMENT_CONFIG_FILE="${PAYMENT_ENV_FILE:-$(root_env_value PAYMENT_ENV_FILE)}"
PAYMENT_CONFIG_FILE="${PAYMENT_CONFIG_FILE:-${ALIPAY_ENV_FILE:-$(root_env_value ALIPAY_ENV_FILE)}}"
PAYMENT_CONFIG_FILE="${PAYMENT_CONFIG_FILE:-/www/wwwroot/excellent/server/.env.alipay.local}"

if [ ! -f "$PAYMENT_CONFIG_FILE" ]; then
    echo "错误: 支付配置文件不存在: $PAYMENT_CONFIG_FILE"
    echo "请在根 .env 设置 PAYMENT_ENV_FILE（兼容旧变量 ALIPAY_ENV_FILE）"
    exit 1
fi

payment_mock="$(read_env_value "$PAYMENT_CONFIG_FILE" PAYMENT_MOCK_EXTERNAL_PAYMENT)"
alipay_enabled="$(read_env_value "$PAYMENT_CONFIG_FILE" ALIPAY_ENABLED)"
wechat_enabled="$(read_env_value "$PAYMENT_CONFIG_FILE" WECHAT_PAY_ENABLED)"

if [ "$(printf '%s' "$payment_mock" | tr '[:upper:]' '[:lower:]')" != "false" ]; then
    echo "错误: 生产部署必须在 $PAYMENT_CONFIG_FILE 中设置 PAYMENT_MOCK_EXTERNAL_PAYMENT=false"
    exit 1
fi

if ! is_true "$alipay_enabled" && ! is_true "$wechat_enabled"; then
    echo "错误: 至少启用一个支付渠道（ALIPAY_ENABLED=true 或 WECHAT_PAY_ENABLED=true）"
    exit 1
fi

PAYMENT_SECRETS_DIR="${PAYMENT_SECRETS_DIR:-$(root_env_value PAYMENT_SECRETS_DIR)}"
PAYMENT_SECRETS_DIR="${PAYMENT_SECRETS_DIR:-$(read_env_value "$PAYMENT_CONFIG_FILE" PAYMENT_SECRETS_DIR)}"
PAYMENT_SECRETS_DIR="${PAYMENT_SECRETS_DIR:-/www/wwwroot/excellent/secrets}"
# Keep the host-side bind-mount location unambiguous.  Relative paths would be
# resolved differently by the shell and by Compose (relative to different
# working directories), which can make the checks below inspect the wrong
# files.
case "$PAYMENT_SECRETS_DIR" in
    /*) ;;
    *)
        echo "错误: PAYMENT_SECRETS_DIR 必须是绝对路径: $PAYMENT_SECRETS_DIR"
        exit 1
        ;;
esac
# Compose interpolates volume and env_file paths from the parent process, not
# from the selected env_file itself. Export the resolved values so a payment
# config file can also own PAYMENT_SECRETS_DIR and legacy aliases resolve to
# the same paths checked below.
export PAYMENT_ENV_FILE="$PAYMENT_CONFIG_FILE"
export PAYMENT_SECRETS_DIR

resolve_secret_path() {
    local configured_path="$1"
    local secret_name
    case "$configured_path" in
        /run/secrets/*)
            secret_name="${configured_path#/run/secrets/}"
            # The container only mounts PAYMENT_SECRETS_DIR at /run/secrets.
            # Accept a single safe filename so a malformed config cannot make
            # the host-side preflight inspect an arbitrary path.
            if [[ ! "$secret_name" =~ ^[A-Za-z0-9._-]+$ || "$secret_name" == "." || "$secret_name" == ".." ]]; then
                return 1
            fi
            printf '%s/%s' "$PAYMENT_SECRETS_DIR" "$secret_name"
            ;;
        *)
            return 1
            ;;
    esac
}

if is_true "$alipay_enabled"; then
    alipay_files=(alipay-merchant-private-key.pem)
    alipay_files+=(alipay-app-cert.crt alipay-public-cert.crt alipay-root-cert.crt)
    for key_file in "${alipay_files[@]}"; do
        if [ ! -f "$PAYMENT_SECRETS_DIR/$key_file" ]; then
            echo "错误: 缺少支付宝密钥或证书文件 $PAYMENT_SECRETS_DIR/$key_file"
            exit 1
        fi
    done
fi

if is_true "$wechat_enabled"; then
    if [ ! -d "$PAYMENT_SECRETS_DIR" ]; then
        echo "错误: PAYMENT_SECRETS_DIR 目录不存在: $PAYMENT_SECRETS_DIR"
        exit 1
    fi
    wechat_required=(
        WECHAT_PAY_APP_ID
        WECHAT_PAY_MCHID
        WECHAT_PAY_API_V3_KEY
        WECHAT_PAY_MERCHANT_SERIAL_NO
        WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH
        WECHAT_PAY_PLATFORM_CERT_PATH
        WECHAT_PAY_NOTIFY_URL
        WECHAT_PAY_REFUND_NOTIFY_URL
    )
    wechat_missing=()
    for key in "${wechat_required[@]}"; do
        if [ -z "$(read_env_value "$PAYMENT_CONFIG_FILE" "$key")" ]; then
            wechat_missing+=("$key")
        fi
    done
    if [ "${#wechat_missing[@]}" -gt 0 ]; then
        echo "错误: WECHAT_PAY_ENABLED=true，但缺少以下配置: ${wechat_missing[*]}"
        echo "请在 $PAYMENT_CONFIG_FILE 中补齐微信支付参数；未启用时可保持 WECHAT_PAY_ENABLED=false 且参数留空。"
        exit 1
    fi

    wechat_api_v3_key="$(read_env_value "$PAYMENT_CONFIG_FILE" WECHAT_PAY_API_V3_KEY)"
    wechat_api_v3_key_length="$(printf '%s' "$wechat_api_v3_key" | wc -c | tr -d '[:space:]')"
    if [ "$wechat_api_v3_key_length" -ne 32 ]; then
        echo "错误: WECHAT_PAY_API_V3_KEY 必须是 32 字节（当前长度: $wechat_api_v3_key_length）"
        exit 1
    fi

    wechat_notify_url="$(read_env_value "$PAYMENT_CONFIG_FILE" WECHAT_PAY_NOTIFY_URL)"
    if [[ ! "$wechat_notify_url" =~ ^https://[^[:space:]]+$ ]]; then
        echo "错误: 生产环境 WECHAT_PAY_NOTIFY_URL 必须是公网 HTTPS URL"
        exit 1
    fi

    wechat_refund_notify_url="$(read_env_value "$PAYMENT_CONFIG_FILE" WECHAT_PAY_REFUND_NOTIFY_URL)"
    wechat_refund_notify_url_length="$(printf '%s' "$wechat_refund_notify_url" | wc -c | tr -d '[:space:]')"
    if [[ ! "$wechat_refund_notify_url" =~ ^https://[^[:space:]?#]+(/[^[:space:]?#]*)?$ ]] || \
       [ "$wechat_refund_notify_url_length" -gt 256 ]; then
        echo "错误: WECHAT_PAY_REFUND_NOTIFY_URL 必须是 256 字节以内、不带 query/fragment 的公网 HTTPS URL"
        exit 1
    fi

    for key in WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH WECHAT_PAY_PLATFORM_CERT_PATH; do
        configured_path="$(read_env_value "$PAYMENT_CONFIG_FILE" "$key")"
        if ! host_path="$(resolve_secret_path "$configured_path")"; then
            echo "错误: $key 必须使用 /run/secrets/<filename>，且只能是单层文件名"
            exit 1
        fi
        if [ ! -f "$host_path" ]; then
            echo "错误: $key 指向的文件不存在: $host_path"
            echo "请确认 PAYMENT_SECRETS_DIR 已挂载，并且配置路径使用 /run/secrets/<filename>。"
            exit 1
        fi
    done
fi

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
echo "  - 管理后台: http://175.27.228.166:8081"
echo "  - 移动端:   http://175.27.228.166:8082"
echo "  - API:      http://175.27.228.166:8000"
echo ""
echo "查看日志: ${COMPOSE[*]} logs -f"
echo "停止服务: ${COMPOSE[*]} down"
echo "=========================================="
