# 来点妹抖吗？

上海妹抖店地图。可交互地图 + AI 问答 + 社交评论，支持网页、Telegram Bot 和 RESTful API。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 16 + PostGIS |
| 前端 | Vue 3 · Vite · Tailwind CSS · 高德地图 JS API |
| AI | 浏览器端 Gemma 4 E2B（WebGPU，优先） + Ollama（回退） |
| Bot | python-telegram-bot v20 |
| 部署 | Docker Compose |

## 快速启动

**前置条件**：Docker Desktop、Ollama（可选）

```bash
# 1. 复制并填写环境变量
cp .env.example .env
# 编辑 .env，至少填写高德地图密钥（见下方说明）

# 2. 启动所有服务
docker compose up --build

# 3. 导入测试数据
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@diantu.local","password":"***REMOVED***"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/v1/shops/admin/import/markdown \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/test_data.md"
```

| 服务 | 地址 |
|------|------|
| 网页前端 | http://localhost:5173 |
| API 文档 | http://localhost:8000/docs |
| 数据库 | localhost:5432 |

## 环境变量

```ini
# 数据库（Docker 内已预设，通常不用改）
DATABASE_URL=postgresql+asyncpg://diantu:diantu123@db:5432/diantu

# JWT 签名密钥（生产环境必须换成随机字符串）
SECRET_KEY=your-secret-key

# 高德地图（https://console.amap.com/）
AMAP_KEY=          # Web 服务密钥，后端地理编码用
AMAP_JS_KEY=       # JS API 密钥，前端加载地图用（在控制台绑定域名白名单）
VITE_AMAP_JS_KEY=  # 同上，Vite 构建时注入前端
AMAP_JSCODE=       # 安全密钥（jscode），仅后端代理使用，不暴露给浏览器

# Ollama AI（可选，本机需运行 ollama serve）
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma3

# 浏览器端 Edge AI（可选）
# 留空时，前端自动回退到 Ollama。
# 如需启用浏览器端 Gemma 4 E2B，请先把 3.42GB 单文件 GGUF 切成多个 <=256MB 分片，
# 并把分片 URL 按顺序用英文逗号拼接到 VITE_EDGE_MODEL_URLS。
VITE_EDGE_MODEL_URLS=
VITE_EDGE_MODEL_SIZE_BYTES=3416118240

# Telegram Bot（可选）
TELEGRAM_BOT_TOKEN=

# 超级管理员（首次启动自动创建）
SUPERADMIN_EMAIL=admin@diantu.local
SUPERADMIN_PASSWORD=your-password
SUPERADMIN_USERNAME=superadmin
```

### 高德密钥安全说明

`AMAP_JSCODE`（安全密钥）**永远不会出现在浏览器中**。前端配置 `window._AMapSecurityConfig.serviceHost` 指向后端 `/_AMapService` 代理，后端在转发时自动附加 `jscode`。

## 导入数据

支持通过 Markdown 表格批量导入店铺。表格格式：

```markdown
| 店名      | 颜色     | 地址           |
| --------- | -------- | -------------- |
| 示例咖啡  | 纯绿     | 南京东路 100 号 |
```

**颜色字段映射：**

| 中文值 | 含义 | 地图圆点颜色 |
|--------|------|-------------|
| 纯素 | 纯素食 | 浅绿 `#8FBC8F` |
| 半绿半素 | 半素 | 橄榄绿 `#6B8E23` |
| 纯绿 | 纯绿色 | 深绿 `#2E8B57` |
| 半荤半绿 | 半荤半绿 | 鲑鱼红 `#FA8072` |
| 纯荤 | 纯荤 | 热粉 `#FF69B4` |

导入 API（需 admin 或 superadmin token）：

```bash
curl -X POST http://localhost:8000/api/v1/shops/admin/import/markdown \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@your_data.md"
```

## 主要 API

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

GET    /api/v1/shops                      # 列表，支持 ?color=&status=&style= 筛选
POST   /api/v1/shops                      # 新建（admin）
GET    /api/v1/shops/{id}
PATCH  /api/v1/shops/{id}                 # 编辑（店长本人 / admin）
DELETE /api/v1/shops/{id}                 # 删除（admin）

POST   /api/v1/shops/admin/import/markdown

GET    /api/v1/shops/{id}/reviews
POST   /api/v1/shops/{id}/reviews         # 发评论 + 打分（1-5）
DELETE /api/v1/reviews/{id}
POST   /api/v1/reviews/{id}/reactions     # 点赞 / 点踩

POST   /api/v1/shops/{id}/favorite        # 收藏 / 取消收藏（toggle）
POST   /api/v1/shops/{id}/checkin         # 打卡

GET    /api/v1/users/me
POST   /api/v1/users/me/apikey            # 生成 API Key

GET    /api/v1/ai/context                 # 浏览器端 AI 上下文
POST   /api/v1/ai/chat                    # AI 问答
```

完整文档见 http://localhost:8000/docs

## 浏览器端 AI（WebGPU）启用方式

首版浏览器端 AI 只支持**桌面 Chromium + WebGPU**。前端会优先尝试本地运行 Gemma 4 E2B；浏览器不支持、模型未就绪或推理失败时，会自动回退到 Ollama。

### 为什么默认仍会回退到 Ollama

你指定的模型文件：

- `Huihui-gemma-4-E2B-it-qat-q4_0-unquantized-abliterated-Q4_K.gguf`

体积约 **3.42GB**，而当前浏览器端 GGUF 路线存在**单文件 2GB 左右上限**。因此不能直接把这个单文件 URL 交给浏览器加载，必须先切分成多个分片。

### 切分模型

仓库提供了一个辅助脚本，会调用 `llama-gguf-split` 把 GGUF 切成多个分片，并打印可直接粘贴到 `.env` 的 `VITE_EDGE_MODEL_URLS=` 行：

```bash
chmod +x scripts/split-edge-model.sh

scripts/split-edge-model.sh \
  /path/to/Huihui-gemma-4-E2B-it-qat-q4_0-unquantized-abliterated-Q4_K.gguf \
  ./frontend/public/models/gemma4-e2b \
  https://your-domain.example
```

默认按 **256MB** 切分。如果输出目录位于 `frontend/public` 下，脚本会自动把对应公开子路径拼到你传入的站点根 URL 上。切分后，把脚本输出的 `VITE_EDGE_MODEL_URLS=...` 复制到 `.env`，然后重新构建前端：

```bash
docker compose up --build
```

或生产环境：

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### 行为说明

- **未配置 `VITE_EDGE_MODEL_URLS`**：前端显示原因并继续使用 Ollama。
- **配置了分片 URL 且浏览器支持 WebGPU**：首次 AI 请求会提示下载约 3.42GB 模型，确认后预热并优先本地推理。
- **Safari / Firefox / 移动端 / WebGPU 不可用**：自动回退到 Ollama。

## 权限

| 操作 | 游客 | 用户 | 店长 | 管理员 | 站长 |
|------|:----:|:----:|:----:|:------:|:----:|
| 查看地图 / 店铺 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 评论 / 收藏 / 打卡 | | ✓ | ✓ | ✓ | ✓ |
| 编辑自己的店铺 | | | ✓ | ✓ | ✓ |
| 新建 / 删除店铺 | | | | ✓ | ✓ |
| 用户管理 / 全部 API | | | | | ✓ |

注册时选择角色：`user`（普通用户）或 `owner`（店长）。

## 用户权重与评分算法

```
用户权重 = max(0.1, min(10.0, 1.0 + 净赞数 / 10))
净赞数 = Σ(该用户所有评论收到的加权点赞) - Σ(加权点踩)

店铺分数 = Σ(评分 × 评论者权重) / Σ(评论者权重)
```

## 项目结构

```
diantu/
├── backend/           # FastAPI 后端
│   └── app/
│       ├── core/      # 配置、数据库、JWT
│       ├── models/    # SQLAlchemy ORM
│       ├── routers/   # API 路由
│       ├── schemas/   # Pydantic 数据校验
│       └── services/  # 业务逻辑（地理编码、AI、MD 解析、评分）
├── frontend/          # Vue 3 前端
│   └── src/
│       ├── components/  # MapView、FilterBar、ShopPanel 等
│       ├── views/       # Home、Auth
│       ├── stores/      # Pinia 状态管理
│       └── api/         # axios 封装
├── bot/               # Telegram Bot
├── data/              # 原始数据（test_data.md）
├── docker-compose.yml
└── .env.example
```

## Telegram Bot 命令

```
/start   — 帮助
/shops   — 所有店铺列表
/open    — 营业中的店铺
直接发消息 — AI 推荐
```

## 待实现（预留接口）

- 定时抓取美团 / 百度 / 高德新点评（`platform` 字段已预留）
- 今日店员头像 / 排班表编辑 UI
