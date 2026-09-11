# 本地 Docker 启动

在项目根目录运行：

```powershell
.\tools\start-local-docker.ps1
```

该脚本先构建，再启动并等待五个服务健康。仅启动已构建镜像可使用 `-NoBuild`；修改代码后使用默认命令重新构建。

编排文件为 `tools/compose.local-test.yml` 和 `tools/compose.local-app.yml`，Compose 项目名为 `excellent-localtest`。

| 服务 | 本地地址 |
| --- | --- |
| 后台管理（Nginx） | http://127.0.0.1:5173/commission |
| 移动端 H5（Nginx） | http://127.0.0.1:5174/ |
| 后端 API（FastAPI） | http://127.0.0.1:8000/docs |
| MySQL | 127.0.0.1:13306，excellent_local_test |
| Redis | 127.0.0.1:16379 |

后台测试账号 `18800000000`，密码 `Admin@123`。移动端本地登录可获取模拟验证码。切换运行方式后如果原登录令牌失效，重新登录即可。

本地编排不加载服务器的 `.env` 和支付密钥文件；支付、短信均为模拟模式，两个前端通过同域 Nginx 代理访问容器 API。所有发布端口只绑定 `127.0.0.1`。根目录原部署 Compose 保留原配置。

已有测试库保存在 Docker 卷 `excellent-localtest_mysql_localtest`，本次继续复用。上传目录绑定项目的 `server/uploads`。普通停止/重建不会清空测试库；不要使用 `down -v`，该参数会删除数据库卷。

查看状态和日志：

```powershell
docker compose -f tools/compose.local-test.yml -f tools/compose.local-app.yml ps
docker compose -f tools/compose.local-test.yml -f tools/compose.local-app.yml logs --tail 100 server
```

停止应用容器、保留数据库和 Redis：

```powershell
docker compose -f tools/compose.local-test.yml -f tools/compose.local-app.yml stop server admin-web mobile-uni-new2
```

若需要恢复原生 Python/Node 开发方式，先执行上面的停止命令，再运行 `tools/start-local-test.ps1`。两种方式使用相同的应用端口，不能同时监听；切换时只需停止本项目占用这些端口的进程。

本机首次拉取 Docker Hub 基础镜像出现连接超时，使用 Google Docker Hub 缓存成功拉取。相同情况下可以执行：

```powershell
.\tools\start-local-docker.ps1 -UseRegistryMirror
```

这个选项将缓存的 Python、Node、Nginx 基础镜像拉取并标记为本地构建所需名称，不更改 Docker Desktop 全局代理或其他项目配置。后端 Dockerfile 还会规范化入口脚本的 Windows 换行；入口脚本已修复 `su` 的参数分隔，避免把 Uvicorn 的 `--host` 当成 `su` 选项。实际 API 进程以 UID 1000 运行。

2026-09-10 本机启动验证完成：五个容器均为 `running / healthy`；三个发布端口的健康检查均返回 MySQL、Redis 正常；Chrome 浏览器通过后台登录、佣金页面、移动端模拟验证码登录和城市席位列表检查，没有页面异常或失败 HTTP 响应。两端 API 请求分别经过 5173、5174 的同域 Nginx 代理。证据位于 `logs/local-test/docker-browser-results.json`、`docker-admin.png`、`docker-mobile.png`。

原本项目的 Python/Node 开发进程已停止，当前由容器提供三个应用服务。已有测试数据库和席位记录继续可见，其他 Docker 项目保持运行。
