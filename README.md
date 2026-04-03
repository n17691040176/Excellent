# Excellent APP 一体化商城

统一仓库包含：
- `server/` FastAPI 后端
- `admin-web/` Vue 3 后台管理端
- `mobile-h5/` Vue 3 + Vant 移动端 H5
- `docs/` 规划文档、校对文档、实现对齐文档

当前定位：
- 单人开发
- 单节点部署
- 1 万用户体量
- 轻量化、易维护

---

## 项目目录

```text
D:\Excellent
├─ server/                # FastAPI 后端服务
├─ admin-web/             # Vue3 后台管理系统
├─ mobile-h5/             # Vue3 移动端 H5 商城
├─ docs/                  # 业务、数据库、接口、部署文档
└─ README.md              # 仓库总说明
```

---

## 文档索引

### 核心规划文档
- `docs/开发文档-校对版.md`
- `docs/数据库设计-校对版.md`
- `docs/接口设计-校对版.md`
- `docs/商品专区设计.md`
- `docs/资产体系设计.md`
- `docs/招商与代理规则.md`
- `docs/本地生活业务设计.md`

### 当前实现对齐文档
- `docs/当前实现对齐说明-2026-04-02.md`
- `docs/当前接口实现对齐说明-2026-04-02.md`
- `docs/当前数据库实现对齐说明-2026-04-02.md`
- `docs/部署与联调说明-2026-04-02.md`
- `docs/功能缺口清单-2026-04-02.md`

---

## 当前模块说明

### 后端 `server/`
- 技术栈：FastAPI + SQLAlchemy 2.0 + MySQL 8 + Redis + Celery
- 入口：`server/app/main.py`
- 路由：`server/app/api/v1/`
- 模型：`server/app/models/`
- 服务：`server/app/services/`
- 建表 SQL：`server/sql/schema.sql`
- 运行说明：`server/README.md`

### 后台管理端 `admin-web/`
- 技术栈：Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios
- 路由：`admin-web/src/router/index.js`
- 菜单：`admin-web/src/router/menu.js`
- 页面：`admin-web/src/views/`

### 移动端 H5 `mobile-h5/`
- 技术栈：Vue 3 + Vite + Vant 4 + Vue Router + Axios
- 路由：`mobile-h5/src/router/index.js`
- 页面：`mobile-h5/src/views/`
- rem 适配：`mobile-h5/src/utils/flexible.js`

---

## 当前业务范围

### 已覆盖
- 用户注册、登录、JWT 鉴权、个人资料
- 团队创建、加入、角色管理、解散
- 一级/二级邀请返现、冻结、结算、提现
- 四大专区：首页复购区、自营商城、爆款区、本地生活
- 套餐体系、商品下单、订单明细、演示支付、确认完成
- 余额、积分、兑换券、AI 券四类资产
- 供应商入驻、入场费、代理资格、协议与推荐奖励
- 本地生活商家、门店、服务、订单、收益规则

### 当前仍属轻量实现
- 审计日志未独立落库
- 后台账号未独立拆表
- 资产转赠未拆专用记录表
- 供应商商品未拆独立商品表

详见：
- `docs/当前实现对齐说明-2026-04-02.md`
- `docs/当前接口实现对齐说明-2026-04-02.md`
- `docs/当前数据库实现对齐说明-2026-04-02.md`

---

## 启动顺序建议

### 1. 启动后端
参考：
- `server/README.md`

### 2. 启动后台管理端
在 `admin-web/` 目录执行：

```powershell
npm install
npm run dev
```

### 3. 启动移动端 H5
在 `mobile-h5/` 目录执行：

```powershell
npm install
npm run dev
```

---

## 当前审查建议

建议优先按以下顺序审查：
1. `docs/开发文档-校对版.md`
2. `docs/当前实现对齐说明-2026-04-02.md`
3. `docs/接口设计-校对版.md`
4. `docs/当前接口实现对齐说明-2026-04-02.md`
5. `docs/数据库设计-校对版.md`
6. `docs/当前数据库实现对齐说明-2026-04-02.md`

---

## Git 状态

- 当前仓库已初始化 Git。
- 代码、文档、前后端工程均位于同一仓库下，适合继续按模块提交。
