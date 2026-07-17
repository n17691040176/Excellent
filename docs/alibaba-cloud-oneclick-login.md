# 阿里云 H5 一键登录集成指南

## 概述

阿里云号码认证服务提供 H5 端的一键登录能力，成功率约 60-80%，适用于嵌入在 App 中的 H5 页面。

## 前置准备

### 1. 阿里云控制台配置

1. 登录 [阿里云号码认证服务控制台](https://dypns.console.aliyun.com/)
2. 创建一键登录应用，获取以下信息：
   - **AppKey**: 应用标识
   - **签名密钥**: 用于 API 签名
3. 开通 H5 一键登录功能

### 2. 配置信息

将获取的配置填入 `mobile-uniNew2/config/index.js`:

```javascript
export const DypnsConfig = {
  APP_KEY: '您的AppKey',        // 例如: '3098457689432654'
  SIGNATURE_SECRET: '您的签名密钥',  // 与后端保持一致
}
```

同时更新后端配置 `server/app/core/config.py`:
```python
DYNPN_ENABLED = True
DYNPN_ACCESS_KEY_ID = '您的AccessKeyId'
DYNPN_ACCESS_KEY_SECRET = '您的AccessKeySecret'
DYNPN_SIGNATURE_SECRET = '您的签名密钥'
DYNPN_APP_KEY = '您的AppKey'
```

## H5 SDK 集成

### 方案一: 使用阿里云官方 H5 SDK

阿里云提供 H5 JS SDK，但需要注意：

**官方 H5 SDK 主要支持：**
- Web 浏览器直接访问
- App 内嵌 H5（需要 App 端配合）

**对于 uni-app H5：**

1. 首先检查是否有 npm 包可用
2. 如果没有，需要使用 webview 通信方式

### 方案二: App 端透传方案（推荐）

由于 H5 嵌入式方案，最可靠的方式是让 App 原生层获取手机号，然后传递给 H5：

```
App原生 → 获取手机号 → 传递给H5页面 → H5调用后端登录
```

**App 端实现（伪代码）：**

```javascript
// App 端伪代码
const DyPns = uni.requireNativePlugin('AliDyPns');
DyPns.getPhoneNumber({
  appKey: '您的AppKey',
  timeout: 10000
}, (result) => {
  if (result.phoneNumber) {
    // 将手机号传递给 H5
    window.postMessage({
      type: 'ONE_CLICK_LOGIN_SUCCESS',
      phone: result.phoneNumber
    }, '*');
  }
});
```

**H5 端接收：**

```javascript
// main.js 中添加
window.addEventListener('message', (event) => {
  if (event.data?.type === 'ONE_CLICK_LOGIN_SUCCESS') {
    // 存储手机号
    uni.setStorageSync('one_click_phone', event.data.phone);
    // 跳转到登录页
    uni.navigateTo({ url: '/pages/login/index' });
  }
});
```

### 方案三: 后端 API 验证方案

如果 App 端获取了 access_token，可以通过 API 传递给后端：

**App 端：**
```javascript
// App 获取 token 后
my.navigateTo({
  url: 'https://your-domain.com/h5/#/pages/login/index?token=' + accessToken
});
```

**H5 端（main.js）：**
```javascript
// 从 URL 参数获取 token
const urlParams = new URLSearchParams(window.location.search);
const accessToken = urlParams.get('token');

if (accessToken) {
  // 调用一键登录 API
  authApi.oneClickLogin({ access_token: accessToken })
    .then(res => {
      // 登录成功
      uni.setStorageSync('token', res.access_token);
      uni.switchTab({ url: '/pages/index/index' });
    });
}
```

## 当前实现状态

后端已完整实现：
- ✅ `POST /api/v1/auth/one-click-login` - 一键登录
- ✅ `POST /api/v1/auth/one-click-register` - 新用户注册
- ✅ `DypnsService` 服务类

前端 UI 已完成：
- ✅ 登录页添加一键登录按钮
- ✅ 新用户注册弹窗
- ✅ API 接口调用

待完成：
- ⏳ App 端 SDK 集成（需要原生开发）
- ⏳ H5 与 App 的通信机制

## 测试建议

1. **开发阶段**：使用短信验证码登录测试其他功能
2. **集成阶段**：App 团队完成原生 SDK 集成
3. **联调阶段**：App 端与 H5 页面联调，传递 access_token

## 费用说明

- 阿里云一键登录按次计费
- H5 端成功率约 60-80%（受运营商限制）
- 相比短信验证码，一键登录用户体验更好（无需输入）

## 注意事项

1. 一键登录需要用户主动触发
2. 需要用户同意《号码认证服务条款》
3. 首次使用可能需要用户在手机上确认授权
4. 部分运营商可能不支持，导致回落到短信验证