# Excellent

Excellent 是一个三服务一体化项目，当前有效目录为：

- `server/`: 后端 API，FastAPI + SQLAlchemy + MySQL + Redis
- `admin-web/`: 后台管理系统，Vue 3 + Vite + Element Plus
- `mobile-uniNew2/`: 移动端，uni-app Vue 3，可构建 H5/App/小程序
- `docs/`: 业务、接口、数据库、部署说明文档

## 服务与端口

| 服务 | 目录 | 本地开发端口 | Docker 端口 |
| --- | --- | --- | --- |
| 后端 API | `server/` | `8000` | `8000 -> 8000` |
| 后台管理 | `admin-web/` | `5173` | `5173 -> 80` |
| 移动端 | `mobile-uniNew2/` | `5174` | `5174 -> 80` |

后端接口统一前缀为 `/api/v1`。两个前端都通过 `VITE_API_BASE_URL` 指向后端，Docker 场景默认使用同域 `/api` 代理到 `server:8000`。

## 本地开发

启动后端：

```powershell
cd D:\Excellent\server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后台管理：

```powershell
cd D:\Excellent\admin-web
npm install
npm run dev
```

启动移动端 H5：

```powershell
cd D:\Excellent\mobile-uniNew2
npm install
npm run dev:h5
```

访问地址：

- 后端健康检查：`http://127.0.0.1:8000/health`
- 后端 Swagger：`http://127.0.0.1:8000/docs`
- 后台管理：`http://127.0.0.1:5173`
- 移动端 H5：`http://127.0.0.1:5174`

## Docker Compose

```powershell
cd D:\Excellent
docker compose up -d --build
```

Compose 会启动：

- `excellent-mysql`
- `excellent-redis`
- `excellent-server`
- `excellent-admin-web`
- `excellent-mobile-uni-new2`

默认管理端账号：

- 手机号：`18800000000`
- 密码：`Admin@123`

## 配置文件

- 后端配置示例：[server/.env.example](server/.env.example)
- 后台配置示例：[admin-web/.env.example](admin-web/.env.example)
- 移动端配置示例：[mobile-uniNew2/.env.example](mobile-uniNew2/.env.example)

## 目录约定

后台管理调用 `/api/v1/admin/...` 接口，移动端调用 `/api/v1/app/...` 与 `/api/v1/auth/...` 接口。不要再新增旧的 `mobile-h5/` 或 `mobile-uni/` 服务编排；当前移动端统一使用 `mobile-uniNew2/`。
