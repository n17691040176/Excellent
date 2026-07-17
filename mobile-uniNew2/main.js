import App from './App.vue'

// #ifndef VUE3
import Vue from 'vue'
import './uni.promisify.adaptor'
Vue.config.productionTip = false
App.mpType = 'app'
const app = new Vue({
  ...App
})
app.$mount()
// #endif

// #ifdef VUE3
import { createSSRApp } from 'vue'
import { authApi } from './api/modules.js'
import { clearRuntimeConfig } from './config/index.js'

// 注册自定义 tabBar 组件
import CustomTabBar from './custom-tab-bar/index.vue'

// ===========================================
// App传手机号免注册登录处理
// ===========================================
async function handleAppLogin() {
  // #ifdef H5
  if (typeof window === 'undefined') return;

  const urlParams = new URLSearchParams(window.location.search);
  const appPhone = urlParams.get('phone');
  const appInviteCode = urlParams.get('invite_code');

  if (appPhone) {
    try {
      const res = await authApi.appLogin({
        phone: appPhone,
        invite_code: appInviteCode || undefined
      });

      if (res.access_token) {
        // 登录成功，存储token
        uni.setStorageSync('token', res.access_token);
        uni.setStorageSync('userInfo', res.user);

        // 清理URL参数
        const cleanUrl = window.location.origin + window.location.pathname;
        window.history.replaceState({}, '', cleanUrl);

        // 跳转到首页
        uni.switchTab({ url: '/pages/index/index' });
        return true;
      }
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
  if (typeof window === 'undefined') return;

  window.addEventListener('message', async (event) => {
    const data = event.data;
    if (!data) return;

    // 处理App传递的手机号登录
    if (data.type === 'APP_LOGIN' && data.phone) {
      try {
        const res = await authApi.appLogin({
          phone: data.phone,
          invite_code: data.invite_code || undefined
        });

        if (res.access_token) {
          uni.setStorageSync('token', res.access_token);
          uni.setStorageSync('userInfo', res.user);

          // 通知App登录成功
          if (event.source) {
            event.source.postMessage({ type: 'LOGIN_SUCCESS', user: res.user }, event.origin);
          }

          // 跳转到首页
          uni.switchTab({ url: '/pages/index/index' });
        }
      } catch (error) {
        console.error('App免登录失败:', error);
        if (event.source) {
          event.source.postMessage({ type: 'LOGIN_FAILED', error: error.message }, event.origin);
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

  // 尝试处理App传手机号登录（异步，不阻塞）
  handleAppLogin().catch(console.error);
  setupAppMessageListener();

  // 重置可能存在的不一致配置
  clearRuntimeConfig();

  return {
    app
  }
}
// #endif
