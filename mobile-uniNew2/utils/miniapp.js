import {
  POWER_BANK_MINIAPP_CONFIG,
  buildPowerBankMiniProgramPath,
  buildPowerBankWebViewUrl
} from '@/config/power-bank-miniapp';

function getLaunchOptions(config, context = {}) {
  const path = buildPowerBankMiniProgramPath(context);
  return {
    appId: config.miniProgram.appId,
    ...(path ? { path } : {}),
    extraData: {
      ...config.miniProgram.extraData,
      source: 'excellent_app'
    },
    envVersion: config.miniProgram.envVersion || 'release'
  };
}

function canUseEmbeddedMiniProgram() {
  return typeof uni.openEmbeddedMiniProgram === 'function';
}

function canUseNavigateMiniProgram() {
  return typeof uni.navigateToMiniProgram === 'function';
}

function openByEmbeddedMiniProgram(options) {
  return new Promise((resolve, reject) => {
    uni.openEmbeddedMiniProgram({
      ...options,
      success: resolve,
      fail: reject
    });
  });
}

function openByNavigateMiniProgram(options) {
  return new Promise((resolve, reject) => {
    uni.navigateToMiniProgram({
      ...options,
      success: resolve,
      fail: reject
    });
  });
}

function openAppWeixinMiniProgram(options) {
  return new Promise((resolve, reject) => {
    // #ifdef APP-PLUS
    const plusApi = globalThis.plus;
    if (!plusApi || !plusApi.share) {
      reject(new Error('Weixin share SDK is not enabled'));
      return;
    }
    plusApi.share.getServices((services) => {
      const weixin = services.find((item) => item.id === 'weixin');
      if (!weixin || typeof weixin.launchMiniProgram !== 'function') {
        reject(new Error('Weixin mini program launcher is unavailable'));
        return;
      }
      weixin.launchMiniProgram({
        id: options.appId,
        ...(options.path ? { path: options.path } : {}),
        type: options.envVersion === 'develop' ? 1 : (options.envVersion === 'trial' ? 2 : 0),
        extraData: options.extraData || {}
      });
      resolve({ provider: 'weixin', mode: 'app-plus' });
    }, reject);
    // #endif

    // #ifndef APP-PLUS
    reject(new Error('Current platform does not support App mini program launch'));
    // #endif
  });
}

function openFallback(config, context = {}) {
  const webViewUrl = buildPowerBankWebViewUrl(context);
  if (config.webView.enabled && webViewUrl) {
    uni.navigateTo({
      url: `/subpackages/profile/mini-webview?url=${encodeURIComponent(webViewUrl)}`
    });
    return Promise.resolve({ mode: 'webview' });
  }

  uni.navigateTo({ url: config.fallbackPath });
  return Promise.resolve({ mode: 'fallback' });
}

export async function openPowerBankMiniApp(context = {}) {
  const config = POWER_BANK_MINIAPP_CONFIG;
  if (!config.miniProgram.enabled || !config.miniProgram.appId) {
    return openFallback(config, context);
  }

  const options = getLaunchOptions(config, context);
  const openMode = config.miniProgram.openMode || 'auto';
  try {
    if (['auto', 'embedded'].includes(openMode) && canUseEmbeddedMiniProgram()) {
      return await openByEmbeddedMiniProgram(options);
    }
    if (['auto', 'navigate'].includes(openMode) && canUseNavigateMiniProgram()) {
      return await openByNavigateMiniProgram(options);
    }
    if (['auto', 'app'].includes(openMode)) {
      return await openAppWeixinMiniProgram(options);
    }
    return openFallback(config, context);
  } catch (error) {
    return openFallback(config, context);
  }
}
