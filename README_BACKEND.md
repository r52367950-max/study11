# Backend 开发说明（AI Tutor API）

本文件是后端专项文档；总开发手册见根目录 `README.md`。

## 当前能力

- 通用解题：`POST /math/solve`
- 通用出题：`POST /math/generate`
- 听写流程：`POST /dictation/start`、`POST /dictation/submit`
- 学习记录与画像：`POST /practice/submit`、`GET /memory/profile`、`GET /memory/report`
- 基础接口：`GET /health`、`GET /subjects`

## 运行方式

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 后端目录

- `backend/app/main.py`：HTTP 路由
- `backend/app/schemas.py`：请求/响应模型与校验
- `backend/app/tutor.py`：LLM 编排与 JSON 解析
- `backend/app/search.py`：检索工具
- `backend/app/db.py`：SQLite Memory 与报告逻辑
- `backend/tests/test_api.py`：基础测试

## 注意事项

- 当前环境可能无法拉取依赖（代理 403），本地可用正常网络执行测试。
- `backend/memory.db` 为运行时数据，不入库。
