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
@import './styles/common.css';

page {
  padding-top: calc(env(safe-area-inset-top) + 24rpx);
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 184, 125, 0.18), transparent 24%),
    radial-gradient(circle at 100% 8%, rgba(255, 140, 94, 0.14), transparent 24%),
    linear-gradient(180deg, #fff9f3 0%, #fff3e8 42%, #fffaf7 100%);
  color: #191613;
}

@supports not (padding-top: env(safe-area-inset-top)) {
  page {
    padding-top: calc(var(--status-bar-height) + 24rpx);
  }
}
</style>
