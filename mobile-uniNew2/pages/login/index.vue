<template>
  <view class="login-page">
    <!-- Background -->
    <view class="login-bg">
      <view class="bg-circle bg-circle-1" />
      <view class="bg-circle bg-circle-2" />
    </view>

    <!-- Content -->
    <view class="login-content">
      <!-- Logo Section -->
      <view class="logo-section">
        <view class="logo-mark">
          <svg width="64" height="64" viewBox="0 0 28 28" fill="none">
            <path d="M14 3L3 9V19L14 25L25 19V9L14 3Z" stroke="white" stroke-width="2" stroke-linejoin="round"/>
            <path d="M14 3V25M3 9L25 19M25 9L3 19" stroke="white" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </view>
        <text class="brand-name">卓越商城</text>
        <text class="brand-slogan">品质好物 优享生活</text>
      </view>

      <!-- Form Card -->
      <view class="form-card">
        <view class="form-header">
          <text class="form-title">手机号登录</text>
          <text class="form-subtitle">未注册的手机号将自动创建账号</text>
        </view>

        <view class="form-body">
          <!-- Phone Input -->
          <view class="input-group">
            <view class="input-label">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <rect x="5" y="2" width="14" height="20" rx="2" stroke="currentColor" stroke-width="2"/>
                <path d="M12 18H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <text class="label-text">手机号</text>
            </view>
            <view class="input-wrap" :class="{ 'input-error': phoneError }">
              <input
                v-model="form.phone"
                class="form-input"
                type="number"
                maxlength="11"
                placeholder="请输入手机号"
                @input="validatePhone"
              />
            </view>
            <text v-if="phoneError" class="error-text">{{ phoneError }}</text>
          </view>

          <!-- Code Input -->
          <view class="input-group">
            <view class="input-label">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" stroke-width="2"/>
                <path d="M7 12H7.01M12 12H12.01M17 12H17.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <text class="label-text">验证码</text>
            </view>
            <view class="input-wrap" :class="{ 'input-error': codeError }">
              <input
                v-model="form.code"
                class="form-input"
                type="number"
                maxlength="6"
                placeholder="请输入验证码"
              />
              <view
                class="code-btn"
                :class="{ disabled: cooldown > 0 }"
                @click="sendCode"
              >
                {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
              </view>
            </view>
            <text v-if="codeError" class="error-text">{{ codeError }}</text>
          </view>

          <!-- Login Button -->
          <button
            class="login-btn"
            :class="{ loading: submitting }"
            :disabled="submitting"
            @click="handleLogin"
          >
            <svg v-if="submitting" class="btn-spinner" width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="31.4 31.4" stroke-dashoffset="0"/>
            </svg>
            <text v-if="!submitting">立即登录</text>
            <text v-else>登录中...</text>
          </button>

          <!-- Agreement -->
          <view class="agreement">
            <view
              class="agreement-check"
              :class="{ checked: agreed }"
              @click="agreed = !agreed"
            >
              <svg v-if="agreed" width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M20 6L9 17L4 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </view>
            <text class="agreement-text">
              登录即表示同意
              <text class="link" @click.stop="openAgreement('user')">《用户协议》</text>
              和
              <text class="link" @click.stop="openAgreement('privacy')">《隐私政策》</text>
            </text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue';
import { authApi } from '@/api/modules';
import { setToken, setUserCache } from '@/utils/auth';

const submitting = ref(false);
const sendingCode = ref(false);
const cooldown = ref(0);
const agreed = ref(true);

const form = reactive({
  phone: '',
  code: ''
});

const phoneError = ref('');
const codeError = ref('');

let countdownTimer = null;

const stopCountdown = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
};

const startCountdown = (seconds = 60) => {
  stopCountdown();
  cooldown.value = seconds;
  countdownTimer = setInterval(() => {
    if (cooldown.value <= 1) {
      cooldown.value = 0;
      stopCountdown();
      return;
    }
    cooldown.value -= 1;
  }, 1000);
};

const validatePhone = () => {
  const phone = form.phone;
  if (!phone) {
    phoneError.value = '';
    return true;
  }
  if (!/^1[3-9]\d{9}$/.test(phone)) {
    phoneError.value = '请输入正确的手机号';
    return false;
  }
  phoneError.value = '';
  return true;
};

const sendCode = async () => {
  if (sendingCode.value || cooldown.value > 0) return;

  if (!form.phone) {
    phoneError.value = '请先输入手机号';
    return;
  }

  if (!validatePhone()) return;

  sendingCode.value = true;
  try {
    const res = await authApi.sendLoginCode({ phone: form.phone });
    startCountdown(Number(res?.retry_in) || 60);

    if (res?.debug_code) {
      form.code = res.debug_code;
      uni.showToast({ title: `测试码：${res.debug_code}`, icon: 'none', duration: 2500 });
      return;
    }

    uni.showToast({ title: '验证码已发送', icon: 'none' });
  } catch (error) {
    // handled by request layer
  } finally {
    sendingCode.value = false;
  }
};

const handleLogin = async () => {
  if (submitting.value) return;

  if (!form.phone) {
    phoneError.value = '请输入手机号';
    return;
  }
  if (!validatePhone()) return;

  if (!form.code) {
    codeError.value = '请输入验证码';
    return;
  }
  if (!agreed.value) {
    uni.showToast({ title: '请先同意用户协议', icon: 'none' });
    return;
  }

  submitting.value = true;
  try {
    const loginRes = await authApi.loginByCode({
      phone: form.phone,
      code: form.code
    });

    const token = loginRes?.token || loginRes?.access_token || '';
    if (!token) {
      uni.showToast({ title: '登录失败，缺少 token', icon: 'none' });
      return;
    }

    setToken(token);

    try {
      const profile = await authApi.me();
      setUserCache(profile || null);
    } catch (error) {
      setUserCache(null);
    }

    uni.switchTab({ url: '/pages/home/index' });
  } catch (error) {
    // handled by request layer
  } finally {
    submitting.value = false;
  }
};

const openAgreement = (type) => {
  uni.showToast({ title: `${type === 'user' ? '用户协议' : '隐私政策'}页面开发中`, icon: 'none' });
};

onMounted(() => {
  // page ready
});

onUnmounted(() => {
  stopCountdown();
});
</script>

<style scoped>
@import '@/styles/common.css';

.login-page {
  min-height: 100vh;
  background: var(--bg);
  position: relative;
  overflow: hidden;
}

/* ===== Background ===== */
.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-bg), transparent);
  opacity: 0.6;
}

.bg-circle-1 {
  width: 600rpx;
  height: 600rpx;
  top: -200rpx;
  right: -200rpx;
}

.bg-circle-2 {
  width: 400rpx;
  height: 400rpx;
  bottom: -100rpx;
  left: -150rpx;
}

/* ===== Content ===== */
.login-content {
  position: relative;
  z-index: 1;
  padding: 64rpx 32rpx;
  padding-top: calc(env(safe-area-inset-top) + 64rpx);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ===== Logo Section ===== */
.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 64rpx;
}

.logo-mark {
  width: 140rpx;
  height: 140rpx;
  border-radius: var(--radius-xl);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 20rpx 60rpx rgba(16, 185, 129, 0.25);
  margin-bottom: 32rpx;
}

.brand-name {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text);
  margin-bottom: 8rpx;
}

.brand-slogan {
  font-size: var(--text-base);
  color: var(--text-muted);
}

/* ===== Form Card ===== */
.form-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  padding: 48rpx;
  box-shadow: var(--shadow-lg);
}

.form-header {
  text-align: center;
  margin-bottom: 48rpx;
}

.form-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
  display: block;
  margin-bottom: 8rpx;
}

.form-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* ===== Input Groups ===== */
.form-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

.input-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--primary);
}

.label-text {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 96rpx;
  width: 100%;
  box-sizing: border-box;
  padding: 0 var(--space-6);
  background: var(--bg);
  border: 2rpx solid var(--border);
  border-radius: var(--radius-md);
  transition: border-color var(--duration-fast) var(--ease-out);
}

.input-wrap:focus-within {
  border-color: var(--primary);
}

.input-wrap.input-error {
  border-color: var(--error);
}

.form-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  font-size: var(--text-lg);
  color: var(--text);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.code-btn {
  flex-shrink: 0;
  min-width: 168rpx;
  height: 64rpx;
  padding: 0 var(--space-4);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}

.code-btn:active {
  transform: scale(0.95);
}

.code-btn.disabled {
  background: var(--bg);
  color: var(--text-muted);
}

.error-text {
  font-size: var(--text-xs);
  color: var(--error);
  padding-left: var(--space-4);
}

/* ===== Login Button ===== */
.login-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  height: 100rpx;
  border-radius: 50rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  border: none;
  box-shadow: 0 12rpx 32rpx rgba(16, 185, 129, 0.25);
  transition: all var(--duration-fast) var(--ease-out);
}

.login-btn:active {
  transform: scale(0.98);
  box-shadow: 0 8rpx 24rpx rgba(16, 185, 129, 0.2);
}

.login-btn.loading {
  opacity: 0.8;
}

.login-btn[disabled] {
  opacity: 0.6;
}

.btn-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== Agreement ===== */
.agreement {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: 0 var(--space-3);
}

.agreement-check {
  width: 36rpx;
  height: 36rpx;
  border-radius: var(--radius-sm);
  border: 2rpx solid var(--border);
  background: var(--card);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 4rpx;
  transition: all var(--duration-fast) var(--ease-out);
}

.agreement-check.checked {
  background: var(--primary);
  border-color: var(--primary);
}

.agreement-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.6;
}

.link {
  color: var(--primary);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .code-btn,
  .login-btn,
  .agreement-check {
    transition: none;
  }

  .btn-spinner {
    animation: none;
  }
}
</style>
