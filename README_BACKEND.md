# Backend 开发说明（AI Tutor API）

本文件是后端专项文档；总开发手册见根目录 `README.md`。

## 当前能力

- 通用解题：`POST /math/solve`
- 通用出题：`POST /math/generate`
- 学习计划生成：`POST /study/plan`
- 听写流程：`POST /dictation/start`、`POST /dictation/submit`
- 学习记录与画像：`POST /practice/submit`、`GET /memory/profile`、`GET /memory/report`
- 时间线能力：`GET /memory/timeline`（最近学习事件）
- 基础接口：`GET /health`、`GET /subjects`

## 稳定性与安全性增强

- 请求链路追踪：自动注入 `X-Request-ID`
- 统一安全响应头：`X-Content-Type-Options`、`Referrer-Policy`
- 轻量限流：基于客户端 IP 的窗口限流（默认 60 秒 120 次）
- 统一异常结构：`error/message/request_id`
- API Key 脱敏日志：模型调用日志不输出明文 key
- CORS 收敛：通过 `ALLOWED_ORIGINS` 环境变量配置（默认 `http://localhost:5173`）

## 运行方式

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 环境变量

- `ALLOWED_ORIGINS`：允许的前端来源，逗号分隔
- `RATE_LIMIT_COUNT`：窗口内允许请求数（默认 `120`）
- `RATE_LIMIT_WINDOW_S`：限流窗口秒数（默认 `60`）

## 后端目录

- `backend/app/main.py`：HTTP 路由、中间件、异常处理
- `backend/app/schemas.py`：请求/响应模型与校验
- `backend/app/tutor.py`：LLM 编排、JSON 解析、学习计划生成
- `backend/app/search.py`：检索工具
- `backend/app/db.py`：SQLite Memory、时间线与报告逻辑
- `backend/tests/test_api.py`：基础测试

## 注意事项

- 当前环境可能无法拉取依赖（代理 403），本地可用正常网络执行测试。
- `backend/memory.db` 为运行时数据，不入库。
