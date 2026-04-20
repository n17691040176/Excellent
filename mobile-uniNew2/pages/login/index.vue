<template>
  <view class="login-page">
    <view class="container">
      <view class="card login-card">
        <view class="brand-wrap row gap-12">
          <view class="brand-mark">E</view>
          <view class="brand">Excellent Mall</view>
        </view>

        <view class="title">欢迎回来</view>
        <view class="subtitle">登录后即可使用商城、本地生活与团队能力</view>

        <view class="poster mt-24" />

        <view class="form mt-24">
          <input v-model="form.phone" class="input" type="number" maxlength="11" placeholder="请输入手机号" />
          <input v-model="form.code" class="input mt-16" type="number" maxlength="6" placeholder="请输入验证码" />

          <view class="row-between mt-16">
            <text class="muted">未注册手机号将自动创建账号</text>
            <text class="code-btn interactive" :class="{ disabled: sendingCode || cooldown > 0 }" @click="sendCode">
              {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
            </text>
          </view>

          <button class="btn btn-primary mt-24 interactive" :disabled="submitting" @click="submit">
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
  min-height: 100vh;
  background: linear-gradient(165deg, #ff7a00 0%, #ffa642 42%, #ffd4a7 100%);
  padding-top: 120rpx;
}

.login-card {
  padding: 36rpx;
  border-radius: 28rpx;
}

.brand-wrap { align-items: center; }
.brand-mark {
  width: 52rpx;
  height: 52rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 122, 0, 0.12);
  color: #ff7a00;
  font-size: 30rpx;
  font-weight: 800;
}

.brand {
  font-size: 24rpx;
  color: #cf6200;
  font-weight: 700;
}

.title {
  margin-top: 18rpx;
  font-size: 44rpx;
  font-weight: 800;
  color: #4a2b13;
}

.subtitle {
  margin-top: 10rpx;
  font-size: 24rpx;
  color: #826650;
}

.poster {
  height: 150rpx;
  border-radius: 18rpx;
  background: linear-gradient(120deg, #ffe8cf, #ffd9b4 50%, #ffc98f);
}

.input {
  height: 86rpx;
  border-radius: 16rpx;
  background: #f8f2ea;
  padding: 0 22rpx;
  font-size: 26rpx;
  box-sizing: border-box;
}

.code-btn {
  color: #d96a00;
  font-size: 24rpx;
  font-weight: 700;
}

.code-btn.disabled {
  color: #b6a08e;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
