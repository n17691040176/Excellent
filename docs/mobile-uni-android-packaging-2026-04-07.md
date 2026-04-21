# mobile-uni Android 打包说明

当前 `mobile-uni/` 已完成：
- uni-app Vue 3 工程骨架
- 业务页面迁移
- H5 构建通过
- Docker 静态部署接入

当前 Android 打包前仍需你补齐：

## 1. 核心配置

文件：
- `mobile-uni/src/manifest.json`

需要确认的字段：
- `appid`
- `app-plus.distribute.android.packagename`
- `app-plus.distribute.android.schemes`
- `mp-weixin.appid`

当前预设值：
- `appid`: `__UNI__EXCELLENT_APP`
- Android 包名：`com.excellent.mall`
- App scheme：`excellent`
- 微信小程序 appid：`wxYOUR_APP_ID`

## 2. 签名证书

如果要云打包 Android 安装包，需要准备：
- keystore 文件
- 证书密码
- alias 名称

这些字段最终要补到：
- `mobile-uni/src/manifest.json`
  - `app-plus.distribute.android.keystore`
  - `app-plus.distribute.android.password`
  - `app-plus.distribute.android.aliasname`

当前已预留占位：
- `keystore`: `src/static/certs/android/release.keystore`
- `password`: `CHANGE_ME`
- `aliasname`: `excellent-release`

## 3. 图标和启动图

当前仓库还没有正式 App 图标和启动页素材。

建议至少准备：
- Android 应用图标
- 应用商店提交图标
- 启动页背景图
- 启动页中心 logo

素材准备建议见：
- `mobile-uni/src/static/README.md`
- `mobile-uni/src/static/icons/README.md`
- `mobile-uni/src/static/certs/README.md`

## 4. 构建与验证现状

已验证：
- `npm install`
- `npm run build:h5`
- Docker 中的 `mobile-uni` 静态部署

开发态 `npm run dev:h5` 在当前沙箱里无法监听本地端口，这属于当前执行环境限制，不是项目代码错误。

## 5. 当前访问地址

- 后端 API：`http://服务器IP:8000`
- 管理后台：`http://服务器IP:5173`
- 旧 H5：`http://服务器IP:5174`
- `mobile-uni` H5 构建版：`http://服务器IP:5175`

## 6. 建议的下一步

建议按这个顺序继续：
1. 替换 `mobile-uni/src/config/index.js` 中的服务器地址和邀请域名
2. 补齐 `manifest.json` 中的真实 `appid`、包名、scheme
3. 准备签名证书和图标素材
4. 在 HBuilderX 或 uni 官方打包链路中打 Android 包
