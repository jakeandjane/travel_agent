# 🌍 智行 TripMind — 多 Agent 并行旅行规划助手

> 输入目的地、日期与偏好，5 个 Agent 并行搜索高德真实数据，自动生成"几点去哪玩、三餐吃什么、住哪里、花多少钱"的完整旅行计划。

| 指标 | 数值 | 说明 |
|------|------|------|
| 查询耗时 | **≤ 15s** | 4 路并行搜索（串行基线约 60s，↓75%） |
| 规划成功率 | **≥ 95%** | 原生 Function Calling + 解析重试 + Schema 校验 |
| 工具可用性 | **7 / 7** | 高德 7 个 API 全部可用 |
| 工具初始化 | **≤ 0.5s** | 直连 HTTP，零子进程、零外部依赖 |
| 静默失败 | **0** | 分层显式报错，杜绝"假数据、假进度" |
| API 端点 | **9 个** | 规划/流式/历史/微调/画像/健康检查 |

## ✨ 功能特点

- 🤖 **5 Agent 并行协作**：景点/天气/酒店/餐厅 4 个搜索 Agent 通过 `asyncio.gather` 真并行查询，1 个规划 Agent 汇总生成结构化行程
- 🗺️ **直连高德 7 大 API**：自研 `AmapDirectTool` 通过 HTTP 直连高德（POI 搜索/天气/地理编码/详情/步行·驾车·公交路线），**不依赖 MCP、uvx 或任何子进程**
- 🧠 **原生 Function Calling**：基于 FunctionCallAgent 的可靠工具调用，替代文本正则解析方案
- ⏱️ **颗粒级行程**：每个景点/每餐具体到 HH:MM，景点间标注交通方式，每日天气、酒店、分项预算一应俱全
- 📡 **SSE 真实进度**：4 事件（查询开始/查询完成/规划开始/规划完成）流式驱动前端三步进度指示，进度与后端阶段强一致
- 💬 **两阶段 AI 微调**：30s 快速建议 → 用户确认 → 90s 工具执行，只修改你要求的部分，其余保持原样
- 🕐 **历史回溯与相似参考**：PlanStore 持久化全部计划；相似历史计划（同城+50/偏好+15/天数+10，阈值≥50）作为新规划的结构参考
- 👤 **用户偏好画像**：记住饮食禁忌、旅行风格、预算水平、已去城市，二次规划更贴合
- ✏️ **编辑与导出**：手动编辑（增删景点/调整顺序/回滚）+ 图片/PDF 双格式导出
- 🛡️ **三层容错体系**：重试 3 次 + 四级超时（45/120/30/90s）+ 分层异常（503/502/500），失败永远显式可见


## 🛠️ 技术栈

### 后端
- **框架**: FastAPI + Uvicorn
- **智能体**: FunctionCallAgent（原生 function calling）
- **工具**: 自研 AmapDirectTool（httpx 直连高德 REST API，无 MCP）
- **LLM**: DeepSeek-V4（OpenAI 兼容协议，可配置切换）
- **校验**: Pydantic 全链路 Schema 校验

### 前端

- **框架**: Vue 3 + TypeScript + Vite
- **UI**: Ant Design Vue
- **地图**: 高德地图 JS API 2.0（动态中心 + POI 标记 + 路线）
- **流式**: fetch + ReadableStream 消费 SSE
- **导出**: html2canvas + jsPDF



## 特性文档网页：

https://jakeandjane.github.io/travel_agent/

## 📁 项目结构

```
trip-mind/
├── backend/
│   ├── run.py                        # 启动入口
│   ├── debug_test.py / test_e2e.py   # 分层调试 / 端到端脚本
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── config.py                 # 配置管理（.env 外置）
│       ├── agents/
│       │   ├── trip_planner_agent.py # 核心：5 Agent + 并行/缓存/清洗/重试
│       │   └── refinement_agent.py   # 两阶段微调
│       ├── tools/
│       │   ├── amap_direct.py        # 直连高德（7 个子工具）
│       │   └── registry.py           # 静态工具注册表
│       ├── memory/
│       │   ├── plan_store.py         # 计划持久化 + 相似度匹配
│       │   └── profile_manager.py    # 用户画像
│       ├── models/schemas.py         # Pydantic 数据模型
│       ├── services/                 # LLM 单例 / 图片服务
│       └── api/                      # FastAPI 路由
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts                # 端口 5173，/api 代理 → 8000
    └── src/
        ├── App.vue / main.ts
        ├── services/api.ts           # axios + SSE 封装
        ├── types/index.ts            # 与 Pydantic 对齐的 TS 类型
        └── views/Home.vue / Result.vue
```

## 🚀 快速开始

### 前提条件

- Python 3.10+
- Node.js 16+
- 高德开放平台 Key（Web 服务 API）
- DeepSeek API Key
- 前端地图还需高德 Web 端 JS Key

### 后端启动

```bash
cd backend

# 1. 创建虚拟环境（可选但推荐）
python -m venv venv
venv\Scripts\activate        # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置密钥
cp .env.example .env
# 编辑 .env，填入 AMAP_API_KEY 与 DeepSeek API Key

# 4. 启动（端口 8000）
python run.py
```

### 前端启动

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 配置环境变量
cp .env.example .env
# 填入 VITE_AMAP_WEB_KEY、VITE_AMAP_WEB_JS_KEY

# 3. 启动开发服务器
npm run dev
```

打开浏览器访问 `http://localhost:5173`。

## 📄 API 一览

启动后访问 `http://localhost:8000/docs` 查看交互式文档。核心端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trip/plan` | 同步生成旅行计划 |
| POST | `/api/trip/plan/stream` | 流式生成（SSE 4 事件，推荐） |
| GET | `/api/trip/plans?user_id=` | 历史计划列表 |
| GET | `/api/trip/plan/{plan_id}` | 计划详情 |
| POST | `/api/trip/plan/{plan_id}/refine` | 微调建议（不修改计划） |
| POST | `/api/trip/plan/{plan_id}/apply` | 应用微调（工具调用 + 另存新计划） |
| GET | `/api/trip/health` | 健康检查 |
| GET/PUT | `/api/user/profile/{user_id}` | 读取/更新偏好画像 |
| GET | `/api/tools/*` | 工具/Agent 静态清单（6 个端点） |

## 🎯 核心设计

### 1. 并行调度（查询 60s → 15s）
4 个搜索 Agent 无数据依赖，通过 `asyncio.gather` + `asyncio.to_thread` 真并行执行；单路失败不阻塞其余路，查询总耗时 = 最慢一路的耗时。

### 2. 数据清洗层（杜绝"垃圾进、垃圾出"）
原始 API 返回 → JSON 提取 → 结构化裁剪（POI top 10 简化字段）→ 降级截断，保证进入规划提示词的数据紧凑、可解析。

### 3. 三层容错体系
- **重试**：搜索/规划调用失败重试 3 次（含 LLM 输出非 JSON 的解析重试）
- **超时**：四级独立超时——查询 45s / 规划 120s / 建议 30s / 应用 90s
- **分层异常**：RuntimeError→503、ValueError→502、Exception→500，前端按状态码针对性提示；**任何失败都不静默返回假数据**

### 4. 两阶段微调（感知速度 > 实际速度）
完整微调需 90s 且不可逆。拆为两阶段：纯 LLM 快速建议（30s，无工具开销）→ 用户确认 → FunctionCallAgent 调工具执行（90s），用户全程有控制权，确认前系统零修改。

### 5. PlanStore 相似参考（"宁可漏掉，不能污染"）
同城 +50 / 偏好重叠 +15/项 / 天数相近 +10，阈值 ≥50 才注入历史结构参考，且提示词强制要求使用本次新数据，避免复制过期信息。

## 🗺️ 使用指南

1. 首页填写：目的地、日期（自动算天数）、交通方式、住宿偏好、兴趣标签、额外要求
2. 点击"生成旅行计划"，观察三步真实进度（搜索 → 规划 → 完成）
3. 结果页查看：地图落点、时间线、每日行程、三餐、酒店、天气、预算
4. 不满意？点"AI 微调"用自然语言提要求，或进编辑模式手动改
5. 点"导出行程"保存为图片/PDF

## 🤝 贡献

欢迎提交 Issue 与 Pull Request。

## 📜 开源协议

CC BY-NC-SA 4.0

## 🙏 致谢

- [高德开放平台](https://lbs.amap.com/) — 地图与 POI 数据
- [DeepSeek](https://www.deepseek.com/) — 大模型推理服务
- [HelloAgents](https://github.com/jjyaoao/HelloAgents) — 底层智能体框架
- [Ant Design Vue](https://www.antdv.com/) · [Vue.js](https://vuejs.org/) — 前端生态

---

**智行 TripMind** — 让旅行计划简单而真实 🌈
