# 学校食堂食品安全管理系统

覆盖食堂食品安全核心场景：**食材采购**、**食品留样**、**从业人员健康证**、**异常上报**与**整改跟踪**，内置留样 48 小时到期提醒、健康证临期预警、系统巡检自动生成异常工单。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + Vite + Ant Design 5 + ECharts |
| 后端 | FastAPI + SQLAlchemy 2 |
| 数据库 | PostgreSQL（生产）/ SQLite（本地演示默认，零依赖） |

## 快速开始

```bash
# 1. 安装后端依赖
pip install -r backend/requirements.txt

# 2. 安装前端依赖
cd frontend && npm install && cd ..

# 3. 一键启动（后端 :8000 + 前端 :5173）
./start.sh
```

打开 http://localhost:5173 ，API 文档见 http://localhost:8000/docs 。

首次启动自动建表并写入本地模拟数据（供应商 4 家、采购 20 条、留样 15 条、从业人员 12 名、异常 5 条、整改 3 条），日期均相对当前时间生成，演示时各类预警场景始终可见。

## 切换 PostgreSQL

```bash
docker compose up -d   # 启动 PostgreSQL 16
DATABASE_URL=postgresql+psycopg2://canteen:canteen123@localhost:5432/canteen \
  python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

代码不依赖任何 SQLite 专有特性，切换数据库无需改代码。

## 功能说明

### 仪表盘
- 核心指标：今日留样、留样临期/待销毁、健康证临期/过期、待处理异常、整改逾期、本月采购金额
- 图表：近 30 天采购分类占比、近 7 天采购金额、异常工单分类
- 实时预警列表（每分钟自动刷新），右上角铃铛全局可见

### 食材采购
- 采购登记/编辑/删除，索证索票（检疫合格证号）、批次号、存放位置
- 按分类、验收状态、日期范围、关键词筛选
- 保质期自动跟踪：临期（≤3 天）橙色提醒、过期红色高亮

### 留样记录
- 登记时自动校验留样重量 ≥125g、留样时间不得晚于当前时间，自动计算 48 小时到期时间
- 倒计时标签：剩余 <2h 橙色提醒、超期红色待销毁
- 满 48 小时后方可销毁登记（销毁人+时间），超期未销毁自动生成异常工单

### 健康证管理
- 从业人员档案 + 健康证编号/发证日期/有效期
- 剩余天数自动计算：≤30 天橙色临期提醒、过期红色高亮并自动生成异常工单

### 异常上报与整改跟踪
- 人工上报（分类/严重程度/描述）+ 系统巡检自动生成工单
- 整改闭环：下达整改任务（措施/责任人/期限）→ 完成整改 → 验收通过 → 工单关闭
- 整改逾期自动标记并升级生成工单

### 系统巡检（自动预警引擎）
巡检默认**自动运行**：每日 07:00 / 13:00 / 19:00 三班各一次（「异常与整改」页可修改启停与运行时刻），到点自动扫描；服务重启后自动补跑错过的最近一次班次，同一时刻槽位不会重复执行。也可随时点击「系统巡检」手动触发（`POST /api/inspection/run`）。每次扫描：
1. 健康证已过期 → 生成「严重」工单
2. 食材已过保质期 → 生成「较重」工单
3. 留样超过48小时保存期未销毁 → 生成工单
4. 整改逾期 → 更新状态并生成工单

同一对象的未关闭工单不会重复生成。

**工单自动核销**：每次巡检同时复查系统生成的未关闭工单，关联问题已消除的自动关闭并注明复查结论——健康证已换发或人员离职、食材已处理（标记不合格/修改保质期/删除记录）、留样已销毁、整改已完成。人工上报的工单不参与自动核销。

页面状态条实时显示：最近一次运行时刻/触发方式/新开单数、当前未处理工单数、下次计划运行时间；**超过24小时未成功运行**会进入全局预警列表并在页面红色告警（停用自动巡检时不参与该判断）。运行记录（含失败原因）落库于 `inspection_runs` 表。

相关接口：`GET /api/inspection/status`（状态）、`PUT /api/inspection/config`（配置启停与时刻）。

## 目录结构

```
canteen-system/
├── backend/
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── database.py      # 数据库连接（DATABASE_URL 可切换 PG）
│   │   ├── models.py        # 8 张表：供应商/采购/留样/人员/异常/整改/巡检记录/配置
│   │   ├── schemas.py       # Pydantic 模型
│   │   ├── services.py      # 预警计算 + 系统巡检
│   │   ├── scheduler.py     # 自动巡检调度器（asyncio 后台任务）
│   │   ├── seed.py          # 本地模拟数据
│   │   └── routers/         # 7 组 REST API
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx          # 布局 + 预警铃铛
│       ├── pages/           # 仪表盘/采购/留样/健康证/异常整改
│       └── components/      # ECharts 封装
├── docker-compose.yml       # PostgreSQL 16
└── start.sh                 # 一键启动
```

## 主要 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/dashboard | 仪表盘统计+图表+预警聚合 |
| GET | /api/alerts | 实时预警列表 |
| POST | /api/inspection/run | 手动触发一次巡检 |
| GET | /api/inspection/status | 巡检状态（最近运行/未处理数/超时标志） |
| PUT | /api/inspection/config | 配置自动巡检启停与每日运行时刻 |
| GET/POST/PUT/DELETE | /api/purchases | 食材采购 CRUD |
| GET/POST/DELETE | /api/samples | 留样登记/查询/删除 |
| POST | /api/samples/{id}/dispose | 留样销毁登记 |
| GET/POST/PUT/DELETE | /api/staff | 从业人员健康证 CRUD |
| GET/POST | /api/incidents | 异常上报/查询 |
| POST | /api/incidents/{id}/close | 关闭工单 |
| GET/POST | /api/rectifications | 整改任务下达/查询 |
| POST | /api/rectifications/{id}/complete | 完成整改 |
| POST | /api/rectifications/{id}/verify | 验收通过 |
