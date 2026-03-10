# AI 学习产品开发手册（总 README）

> 本文档是项目唯一“总开发手册”。
> 后端专项说明在 `README_BACKEND.md`。

---

## 1. 产品目标

我们要做一个面向高中阶段（英语/数学/语文）的 AI 学习产品，核心目标：

1. **AI 解题与出题**：给出结构化思路、分步答案、易错点、同类题。
2. **AI 听写/默写**：支持听写任务创建、作答评分、错项反馈。
3. **能力评估报告**：基于历史作答形成持续更新的 Memory 档案。
4. **模型可配置接入**：支持 OpenAI 兼容 API、可切换模型与基址。

产品原则：
- 不做按知识点硬编码模板爆炸。
- 优先“通用推理 + 工具增强”。
- 所有学习行为尽量进入长期 Memory。

---

## 2. 当前实现范围（后端已落地）

### 2.1 可用 API

- `GET /health`
- `GET /subjects`
- `POST /math/solve`
- `POST /math/generate`
- `POST /dictation/start`
- `POST /dictation/submit`
- `POST /practice/submit`
- `GET /memory/profile`
- `GET /memory/report`

### 2.2 当前能力说明

- 解题：LLM 调用 + 输出 JSON 解析兜底。
- 出题：按学科/难度/数量生成题目/答案/解析。
- 听写：先做文本评分链路（便于后续接 ASR）。
- 报告：按正确率与行为数据生成等级、趋势、建议。

---

## 3. 技术实现方法

## 3.1 技术栈

- Web API：FastAPI
- 数据存储：SQLite（`backend/memory.db`）
- 外部模型调用：HTTP（OpenAI 兼容 Chat Completions）
- 检索增强：DuckDuckGo Instant API（可替换）

## 3.2 架构分层

1. **API Layer**（`backend/app/main.py`）
   - 参数接收
   - 错误处理
   - 组合服务

2. **Schema Layer**（`backend/app/schemas.py`）
   - 入参/出参模型
   - 边界校验（subject、mode、correct<=total）

3. **Tutor Layer**（`backend/app/tutor.py`）
   - 模型请求封装
   - JSON 鲁棒解析
   - 题目处理逻辑

4. **Search Tool Layer**（`backend/app/search.py`）
   - 检索调用
   - 检索结果结构化

5. **Memory Layer**（`backend/app/db.py`）
   - 练习数据落库
   - 听写记录落库
   - 报告计算（等级/趋势/建议）

---

## 4. 数据与报告模型（概要）

## 4.1 表结构

- `profiles`
  - user_id, subject
  - attempts, correct_total, total_questions
  - avg_duration_s
  - top_pitfalls

- `dictation_records`
  - session_id, user_id, subject
  - reference_text, answer_text
  - accuracy, wrong_tokens, duration_s

## 4.2 报告输出字段

- level（A/B/C）
- trend（improving/stable/needs_attention）
- suggestions（可执行建议）
- dictation_sessions
- dictation_accuracy

---

## 5. 本地开发指南

## 5.1 启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 5.2 常见验证命令

```bash
python -m compileall backend/app backend/tests
cd backend && pytest -q
```

> 当前容器环境可能因代理导致安装依赖失败（403），本地网络正常时可直接运行。

---

## 6. 协作规范（重要）

1. **总手册固定为 `README.md`**（本文件）。
2. 后端专项说明固定为 **`README_BACKEND.md`**。
3. 每个 AI / 每条分支的工作记录，必须使用不重名文档（建议放到 `docs/ai-notes/`）。
4. 每次改动后，同步更新相关文档（至少更新影响范围与使用方式）。

---

## 7. 下一阶段开发计划（建议）

### P1：把“文本听写”升级到“语音听写”
- 接 TTS：生成播报音频
- 接 ASR：将语音答题转文本
- 用现有 `dictation/submit` 评分链路复用

### P2：前端 MVP 联调
- 题目输入页（solve）
- 出题练习页（generate）
- 听写页（start/submit）
- 报告页（profile/report）

### P3：线上化与可靠性
- API Key 加密/脱敏
- 限流、配额、重试
- 监控告警、链路日志

---

## 8. 快速索引

- 总手册：`README.md`
- 后端专项：`README_BACKEND.md`
- 后端代码：`backend/`
- API 测试：`backend/tests/test_api.py`

