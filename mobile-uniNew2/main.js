import App from './App.vue'
import AppBackButton from './components/AppBackButton.vue'

// #ifndef VUE3
import Vue from 'vue'
import './uni.promisify.adaptor'
Vue.config.productionTip = false
Vue.component('AppBackButton', AppBackButton)
App.mpType = 'app'
const app = new Vue({
  ...App
})
app.$mount()
// #endif

// #ifdef VUE3
import { createSSRApp } from 'vue'
import { authApi } from './api/modules.js'
import { syncRuntimeConfigFromBuild } from './config/index.js'
import { setToken, setUserCache } from './utils/auth.js'

// 注册自定义 tabBar 组件
import CustomTabBar from './custom-tab-bar/index.vue'

// ===========================================
// App传手机号免注册登录处理
// ===========================================
const APP_HOME_PATH = '/pages/home/index';
let appLoginPromise = null;
let appMessageListenerBound = false;

function normalizeAppPhone(phone) {
  return String(phone || '').trim();
}

function removeAppLoginParamsFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete('phone');
  url.searchParams.delete('invite_code');
  url.searchParams.delete('nickname');
  window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
}

async function loginWithAppPhone({ phone, inviteCode, nickname } = {}) {
  const normalizedPhone = normalizeAppPhone(phone);
  if (!/^1[3-9]\d{9}$/.test(normalizedPhone)) {
    throw new Error('App传入的手机号格式不正确');
  }

  if (appLoginPromise) return appLoginPromise;

  appLoginPromise = (async () => {
    const res = await authApi.appLogin({
      phone: normalizedPhone,
      invite_code: inviteCode || undefined,
      nickname: nickname || undefined
    });
    const token = res?.access_token || res?.token || '';
    if (!token) throw new Error('App免登录响应中缺少 token');

    setToken(token);
    setUserCache(res?.user || null);
    uni.switchTab({ url: APP_HOME_PATH });
    return res;
  })();

  try {
    return await appLoginPromise;
  } finally {
    appLoginPromise = null;
  }
}

async function handleAppLogin() {
  // #ifdef H5
  if (typeof window === 'undefined') return;

  const urlParams = new URLSearchParams(window.location.search);
  const appPhone = urlParams.get('phone');
  const appInviteCode = urlParams.get('invite_code');
  const appNickname = urlParams.get('nickname');

  if (appPhone) {
    try {
      await loginWithAppPhone({
        phone: appPhone,
        inviteCode: appInviteCode,
        nickname: appNickname
      });
      removeAppLoginParamsFromUrl();
      return true;
    } catch (error) {
      console.error('App免登录失败:', error);
    }
  }
  // #endif
  return false;
}

// 处理postMessage消息（App端通过postMessage传递数据）
function setupAppMessageListener() {
  // #ifdef H5
  if (typeof window === 'undefined' || appMessageListenerBound) return;
  appMessageListenerBound = true;

  window.addEventListener('message', async (event) => {
    const data = event.data;
    if (!data) return;

    // 处理App传递的手机号登录
    if (data.type === 'APP_LOGIN' && data.phone) {
      try {
        await loginWithAppPhone({
          phone: data.phone,
          inviteCode: data.invite_code,
          nickname: data.nickname
        });

        // 通知App登录成功
        if (event.source) {
          const targetOrigin = event.origin && event.origin !== 'null' ? event.origin : '*';
          event.source.postMessage({ type: 'LOGIN_SUCCESS' }, targetOrigin);
        }
      } catch (error) {
        console.error('App免登录失败:', error);
        if (event.source) {
          const targetOrigin = event.origin && event.origin !== 'null' ? event.origin : '*';
          event.source.postMessage({ type: 'LOGIN_FAILED', error: error.message }, targetOrigin);
        }
      }
    }
  });
  // #endif
}

export function createApp() {
  const app = createSSRApp(App)

  // 全局注册自定义 tabBar 组件
  app.component('CustomTabBar', CustomTabBar)
  app.component('AppBackButton', AppBackButton)

  syncRuntimeConfigFromBuild();

  // 尝试处理App传手机号登录（异步，不阻塞）
  handleAppLogin().catch(console.error);
  setupAppMessageListener();

  return {
    app
  }
}
// #endif
