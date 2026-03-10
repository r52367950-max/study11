# AI 学习产品后端（通用解题 + 联网检索 + Memory）

按你的要求，本版本直接进入工程实现，重点是：

- 不按知识点维护大量提示词
- 模型先分析题目再解答
- 必要时联网检索增强
- 学习表现写入后台 Memory，并可直接生成能力报告

## README 冲突说明（已处理）

- 现在只有**项目根目录 `README.md`**作为唯一产品/工程说明。
- `backend/.pytest_cache/README.md` 是测试工具自动生成的缓存文件，非项目文档，已清理并加入忽略规则。

## 已实现接口

- `GET /health`
- `GET /subjects`：返回当前支持学科（math / english / chinese）
- `POST /math/solve`：通用解题（含可选检索增强）
- `POST /math/generate`：通用出题
- `POST /dictation/start`：启动听写会话（返回 session_id 与播报文本）
- `POST /dictation/submit`：提交听写文本并评分（可接 ASR 结果）
- `POST /practice/submit`：提交练习结果（进入 Memory）
- `GET /memory/profile`：读取学生能力档案
- `GET /memory/report`：读取能力评估报告（等级/趋势/建议+听写统计）

## 运行

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 示例请求

### 解题

```bash
curl -X POST http://localhost:8000/math/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "stu_001",
    "question": "已知函数f(x)=x^2-2x+1，求最小值",
    "subject": "math",
    "mode": "full",
    "model_config": {
      "provider": "openai_compatible",
      "base_url": "https://api.openai.com/v1",
      "api_key": "YOUR_KEY",
      "model": "gpt-4o-mini",
      "timeout_s": 60
    }
  }'
```

### 听写（文本版，后续可接语音识别）

```bash
curl -X POST http://localhost:8000/dictation/start \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"stu_001","subject":"english","content":"apple banana orange"}'

curl -X POST http://localhost:8000/dictation/submit \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"SESSION_ID","user_id":"stu_001","subject":"english","reference_text":"apple banana orange","answer_text":"apple banan orange","duration_s":20}'
```

### 查看 Memory

```bash
curl 'http://localhost:8000/memory/profile?user_id=stu_001&subject=math'
curl 'http://localhost:8000/memory/report?user_id=stu_001&subject=english'
```

## 深化内容（本次新增）

- 输入校验：限制支持学科、限制 mode 枚举、保证 `correct <= total`
- JSON鲁棒解析：支持原始 JSON / fenced JSON / 文本中提取 JSON
- 检索鲁棒性：检索失败时自动降级，不中断主流程
- 能力报告：基于 Memory 输出等级（A/B/C）、趋势、建议
- 听写闭环：新增听写 session + 文本评分 + 统计回写报告

## 目录

- `backend/app/main.py`：路由与流程
- `backend/app/tutor.py`：LLM调用与通用解题/出题逻辑
- `backend/app/search.py`：联网检索工具
- `backend/app/db.py`：SQLite Memory 存储与报告构建
- `backend/tests/test_api.py`：基础接口测试
