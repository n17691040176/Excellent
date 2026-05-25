<template>
  <view class="login-page">
    <view class="login-shell">
      <view class="login-hero card">
        <view class="hero-top">
          <view>
            <view class="login-brand">Excellent Mall</view>
            <view class="login-title">欢迎回来</view>
            <view class="login-desc">一键登录后即可浏览热卖商品、同城服务与个人资产。</view>
          </view>
          <view class="login-mark">E</view>
        </view>

        <view class="hero-banner">
          <view class="banner-chip">限时补贴</view>
          <view class="banner-stat">安全登录 · 极速进入</view>
        </view>
      </view>

      <view class="card login-card mt-16">
        <view class="form-title">手机号登录</view>
        <view class="form">
          <input v-model="form.phone" class="input" type="number" maxlength="11" placeholder="请输入手机号" />
          <input v-model="form.code" class="input mt-16" type="number" maxlength="6" placeholder="请输入验证码" />

          <view class="code-row mt-16">
            <text class="code-btn interactive" :class="{ disabled: sendingCode || cooldown > 0 }" @click="sendCode">
              {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
            </text>
            <text class="code-hint">验证码将发送到当前手机号</text>
          </view>

          <button class="btn btn-primary login-btn mt-24 interactive" :disabled="submitting" @click="submit">
            {{ submitting ? '登录中...' : '一键登录' }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onUnmounted, reactive, ref } from 'vue';
import { authApi } from '@/api/modules';
import { setToken, setUserCache } from '@/utils/auth';

const submitting = ref(false);
const sendingCode = ref(false);
const cooldown = ref(0);
const form = reactive({
  phone: '',
  code: ''
});

let countdownTimer = null;

const stopCountdown = () => {
  if (!countdownTimer) return;
  clearInterval(countdownTimer);
  countdownTimer = null;
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

const sendCode = async () => {
  if (sendingCode.value || cooldown.value > 0) return;
  if (!form.phone) {
    uni.showToast({ title: '请先输入手机号', icon: 'none' });
    return;
  }

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
    // 请求层统一提示
  } finally {
    sendingCode.value = false;
  }
};

const submit = async () => {
  if (submitting.value) return;
  if (!form.phone || !form.code) {
    uni.showToast({ title: '请填写完整信息', icon: 'none' });
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
    // 请求层统一提示
  } finally {
    submitting.value = false;
  }
};

onUnmounted(() => {
  stopCountdown();
});
</script>

<style scoped>
@import '@/styles/common.css';

.login-page {
  padding: 24rpx 0 44rpx;
}

.login-shell {
  padding: 0 24rpx;
}

.login-hero {
  padding: 28rpx;
  background: linear-gradient(135deg, #fff6ec 0%, #ffe4ce 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.16);
  overflow: hidden;
  position: relative;
}

.login-hero::after {
  content: '';
  position: absolute;
  right: -40rpx;
  top: -30rpx;
  width: 180rpx;
  height: 180rpx;
  border-radius: 50%;
  background: rgba(255, 122, 0, 0.08);
}

.hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
}

.login-brand {
  font-size: 22rpx;
  font-weight: 800;
  color: #ff6a00;
  letter-spacing: 0.6rpx;
}

.login-title {
  margin-top: 10rpx;
  font-size: 46rpx;
  line-height: 1.2;
  font-weight: 900;
  color: #4a2410;
}

.login-desc {
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: #81604a;
}

.login-mark {
  width: 90rpx;
  height: 90rpx;
  border-radius: 26rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff7a00, #ff4f3a);
  color: #fff;
  font-size: 38rpx;
  font-weight: 900;
  box-shadow: 0 16rpx 26rpx rgba(255, 89, 44, 0.2);
}

.hero-banner {
  margin-top: 22rpx;
  border-radius: 24rpx;
  padding: 18rpx 20rpx;
  background: linear-gradient(135deg, #ff7a00, #ff5f3d);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.banner-chip {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 20rpx;
  font-weight: 700;
}

.banner-stat {
  color: rgba(255, 255, 255, 0.92);
  font-size: 22rpx;
  font-weight: 700;
}

.login-card {
  padding: 26rpx;
  border-radius: 28rpx;
  border: 1rpx solid rgba(255, 154, 106, 0.16);
}

.form-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #4a2410;
  margin-bottom: 18rpx;
}

.input {
  height: 88rpx;
  border-radius: 18rpx;
  background: #fff7f1;
  padding: 0 22rpx;
  font-size: 26rpx;
  box-sizing: border-box;
  border: 1rpx solid rgba(255, 154, 106, 0.14);
}

.code-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.code-btn {
  color: #d96a00;
  font-size: 24rpx;
  font-weight: 700;
  padding: 6rpx 0;
}

.code-btn.disabled {
  color: #b6a08e;
}

.code-hint {
  font-size: 20rpx;
  color: #9b8268;
}

.login-btn {
  height: 78rpx;
  line-height: 78rpx;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
