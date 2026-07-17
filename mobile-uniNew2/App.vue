<script>
import {
  clearApiBaseUrl,
  clearInviteWebBaseUrl,
  getApiBaseUrlConfig,
  getInviteWebBaseUrlConfig,
  setApiBaseUrl,
  setInviteWebBaseUrl,
  syncRuntimeConfigFromBuild
} from './config/index';

// 导入自定义 tabBar 组件以确保其被编译

let isOfflineNotified = false;
let h5DebugEventsBound = false;

function bindH5DebugEvents() {
  // #ifdef H5
  if (h5DebugEventsBound || typeof window === 'undefined') {
    return;
  }
  h5DebugEventsBound = true;

  window.addEventListener(
    'error',
    (event) => {
      const target = event?.target;
      const isResourceError = target && target !== window;
      if (isResourceError) {
        const resourceUrl = target.src || target.href || '';
        console.error('[excellent-mobile] resource load error:', {
          tagName: target.tagName,
          resourceUrl,
        });
        return;
      }

      console.error('[excellent-mobile] window error:', {
        message: event?.message,
        filename: event?.filename,
        lineno: event?.lineno,
        colno: event?.colno,
        error: event?.error
      });
    },
    true
  );

  window.addEventListener('unhandledrejection', (event) => {
    console.error('[excellent-mobile] unhandled rejection:', event?.reason || event);
  });
  // #endif
}

function logRuntimeConfig() {
  const apiBaseUrl = getApiBaseUrlConfig();
  const inviteWebBaseUrl = getInviteWebBaseUrlConfig();

  console.info('[excellent-mobile] resolved apiBaseUrl:', {
    value: apiBaseUrl.value,
    source: apiBaseUrl.source,
    runtimeValue: apiBaseUrl.runtimeValue,
    envValue: apiBaseUrl.envValue,
    fallback: apiBaseUrl.fallback
  });
  console.info('[excellent-mobile] resolved inviteWebBaseUrl:', {
    value: inviteWebBaseUrl.value,
    source: inviteWebBaseUrl.source,
    runtimeValue: inviteWebBaseUrl.runtimeValue,
    envValue: inviteWebBaseUrl.envValue,
    fallback: inviteWebBaseUrl.fallback
  });

  if (apiBaseUrl.source === 'runtime') {
    console.warn('[excellent-mobile] excellent_api_base_url is coming from local storage.');
  }

  // #ifdef H5
  if (typeof window !== 'undefined') {
    window.__EXCELLENT_DEBUG__ = {
      getConfig() {
        return {
          apiBaseUrl: getApiBaseUrlConfig(),
          inviteWebBaseUrl: getInviteWebBaseUrlConfig()
        };
      },
      setApiBaseUrl(url) {
        setApiBaseUrl(url);
        return getApiBaseUrlConfig();
      },
      clearApiBaseUrl() {
        clearApiBaseUrl();
        return getApiBaseUrlConfig();
      },
      setInviteWebBaseUrl(url) {
        setInviteWebBaseUrl(url);
        return getInviteWebBaseUrlConfig();
      },
      clearInviteWebBaseUrl() {
        clearInviteWebBaseUrl();
        return getInviteWebBaseUrlConfig();
      },
      reload() {
        window.location.reload();
      }
    };
    console.info('[excellent-mobile] debug helper ready: window.__EXCELLENT_DEBUG__');
  }
  // #endif
}

function retryCurrentPage() {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  if (!current) return;

  const route = current.route;
  const options = current.options || {};
  const query = Object.keys(options)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(options[key])}`)
    .join('&');
  const url = `/${route}${query ? `?${query}` : ''}`;
  uni.reLaunch({ url });
}

export default {
  onLaunch() {
    syncRuntimeConfigFromBuild();

    logRuntimeConfig();
    bindH5DebugEvents();
    uni.onNetworkStatusChange((res) => {
      if (res.isConnected) {
        isOfflineNotified = false;
        return;
      }

      if (isOfflineNotified) return;
      isOfflineNotified = true;

      uni.showModal({
        title: '网络异常',
        content: '当前网络不可用，是否立即重试？',
        confirmText: '重试',
        cancelText: '稍后',
        success: ({ confirm }) => {
          if (confirm) {
            retryCurrentPage();
          }
        }
      });
    });
  },
  onShow() {},
  onHide() {}
};
</script>

<style>
/* Excellent 电商设计系统 v2.0 */
/* Refined Modern 风格 - 精致、现代、有辨识度 */
@import './styles/tokens.css';
@import './styles/common.css';

/* Google Fonts - Rubik + Nunito Sans */
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;500;600;700&family=Rubik:wght@300;400;500;600;700&display=swap');

/* 全局页面样式 */
page {
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: 'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-tap-highlight-color: transparent;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 安全区域适配 */
@supports not (padding-top: env(safe-area-inset-top)) {
  page {
    padding-top: calc(var(--status-bar-height) + 24rpx);
  }
}

/* 页面过渡动画 */
page {
  transition: background-color var(--duration-normal) var(--ease-out);
}

/* 统一的卡片悬浮效果 */
.card-hover {
  transition: all var(--duration-fast) var(--ease-out);
}

.card-hover:active {
  transform: scale(0.98);
  box-shadow: var(--shadow-sm);
}

/* 按钮默认样式 */
button::after {
  border: none;
}

button {
  background: transparent;
  padding: 0;
  margin: 0;
  line-height: inherit;
  -webkit-tap-highlight-color: transparent;
}

/* 图片自适应 */
image {
  width: 100%;
  height: 100%;
  display: block;
}

/* 滚动优化 */
scroll-view {
  -webkit-overflow-scrolling: touch;
}

/* 禁用选择 */
view, text {
  user-select: none;
  -webkit-user-select: none;
}

/* 统一的触控反馈 */
.touch-scale:active {
  transform: scale(0.97);
  opacity: 0.9;
}

.touch-opacity:active {
  opacity: 0.8;
}

/* 品牌色渐变按钮 */
.btn-gradient-primary {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  box-shadow: var(--shadow-primary);
}

.btn-gradient-primary:active {
  background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
  box-shadow: var(--shadow-sm);
  transform: scale(0.98);
}

/* 圆角徽章 */
.badge-rounded {
  padding: 6rpx 16rpx;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.badge-primary {
  background: var(--primary-bg);
  color: var(--primary);
}

.badge-accent {
  background: var(--accent-bg);
  color: var(--accent);
}

/* 折扣标签 */
.discount-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4rpx 10rpx;
  background: linear-gradient(135deg, var(--danger) 0%, #F87171 100%);
  color: white;
  font-size: 20rpx;
  font-weight: var(--font-bold);
  border-radius: var(--radius-sm);
  box-shadow: 0 2rpx 8rpx rgba(239, 68, 68, 0.25);
}

/* 价格显示 */
.price-highlight {
  display: flex;
  align-items: baseline;
  gap: 2rpx;
}

.price-highlight .symbol {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--primary);
}

.price-highlight .value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--primary);
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, sans-serif;
}

.price-highlight .original {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-decoration: line-through;
  margin-left: var(--space-2);
}

/* 分割线 */
.divider-soft {
  height: 1rpx;
  background: var(--border-light);
}

.divider-section {
  height: 16rpx;
  background: var(--bg);
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
