# Excellent Mobile Uni

This directory is a migration scaffold for moving the current H5 app to a uni-app client.

Current goal:
- Keep the existing backend contract unchanged
- Reuse API grouping and auth flow from `mobile-h5`
- Rebuild the page shell with uni-app page routing and storage APIs

Recommended migration order:
1. Login
2. Home
3. Package list and detail
4. Order list and detail
5. Profile and settings
6. Life, team, assets, commission, invite

What is already scaffolded here:
- `pages.json`: page and subpackage plan
- `config/index.js`: runtime API base URL config
- `api/request.js`: uni.request-based request wrapper
- `api/modules.js`: business API groups aligned with the current H5 app
- `utils/auth.js`: token and user cache helpers for uni storage
- `styles/common.css`: shared page, card, form, button, metric, list styles
- `package.json`, `vite.config.js`, `index.html`, `jsconfig.json`, `manifest.json`, `uni.scss`: formal project scaffold files
- `src/static/README.md`: app icon, splash, signing asset checklist
- `pages/login`, `pages/home`, `pages/packages`, `pages/orders`, `pages/profile`: implemented core business pages
- `subpackages/package/detail`, `subpackages/order/detail`, `subpackages/profile/settings`: implemented detail and settings pages
- `subpackages/life`, `subpackages/team`, `subpackages/assets`, `subpackages/commission`, `subpackages/invite`: implemented business pages
- `subpackages/life/orders`, `subpackages/life/service-detail`: implemented local life order and service pages

What is intentionally not added yet:
- Verified dependency lockfile and install result
- Third-party UI library choice
- Global state library selection

Recommended next step:
- Prefer initializing an official uni-app Vue 3 template first, or run `npm install` and then `npm run sync:uni`
- The current `package.json` already follows the official Vue3 CLI version line instead of unpinned `latest`
- Reconcile generated template files with this scaffold if the official template differs
- Replace `http://YOUR_SERVER_IP:8001` in `config/index.js`, or set `excellent_api_base_url` at runtime
- Replace `http://YOUR_H5_DOMAIN` in `config/index.js`, or set `excellent_invite_web_base_url` at runtime
- Start integrating an actual uni-app UI library or your own shared components
- For Android packaging, see `docs/mobile-uni-android-packaging-2026-04-07.md`
