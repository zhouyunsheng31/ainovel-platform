# AI小说拆书系统 - 后端服务

基于FastAPI + LangChain的四层纲生成系统后端服务。

## 技术栈

- **框架**: FastAPI 0.104+
- **数据库**: SQLite (异步)
- **ORM**: SQLAlchemy 2.0+
- **LLM**: LangChain + OpenAI API
- **异步**: asyncio + aiofiles

## 项目结构

```
backend/
├── app/
│   ├── api/              # API路由
│   │   ├── books.py      # 书籍相关接口
│   │   ├── outlines.py   # 纲相关接口
│   │   ├── tasks.py      # 任务相关接口
│   │   └── websocket.py  # WebSocket推送
│   ├── models/           # 数据模型
│   │   ├── database.py   # 数据库连接
│   │   ├── models.py     # ORM模型
│   │   └── schemas.py    # Pydantic模型
│   ├── services/         # 业务服务
│   │   ├── file_processor.py    # 文件处理
│   │   ├── text_splitter.py     # 文本分割
│   │   ├── llm_service.py       # LLM调用
│   │   └── outline_service.py   # 纲生成
│   ├── prompts/          # 提示词模板
│   │   └── outlines.py
│   ├── workflows/        # LangGraph工作流
│   └── config.py         # 配置管理
├── data/                 # 数据目录
│   ├── uploads/          # 上传文件
│   └── novel_platform.db # SQLite数据库
├── main.py              # 主入口
├── requirements.txt     # 依赖清单
└── .env.example         # 环境变量示例

```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，配置API密钥
```

### 3. 启动服务

```bash
python main.py
```

服务将在 http://localhost:8000 启动

### 4. 查看API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

### 书籍管理
- `POST /api/v1/books/upload` - 上传书籍
- `GET /api/v1/books` - 获取书籍列表
- `GET /api/v1/books/{bookId}` - 获取书籍详情
- `DELETE /api/v1/books/{bookId}` - 删除书籍
- `GET /api/v1/books/{bookId}/tree` - 获取纲树结构

### 纲管理
- `GET /api/v1/outlines/{outlineId}` - 获取纲详情
- `POST /api/v1/outlines/{outlineId}/copy` - 复制纲内容

### 任务管理
- `GET /api/v1/tasks/{taskId}` - 获取任务状态
- `GET /api/v1/tasks/{taskId}/errors` - 获取错误日志

### WebSocket
- `WS /api/v1/ws/{taskId}` - 实时进度推送

## 核心功能

### 文件处理
- 支持格式: TXT, EPUB, DOC, DOCX, PDF
- 自动编码检测: UTF-8 → GBK → GB2312 → GB18030
- 标题删除: 正则匹配多种标题模式

### 文本分割
- 智能分割: 2000字/章
- 保留完整句子
- 记录偏移量

### 四层纲生成
1. **章纲** (CHAPTER): 每章约200字概括
2. **粗纲** (COARSE): 每10章合并生成
3. **大纲** (MAIN): 每10份粗纲合并生成
4. **世界纲** (WORLD): 所有大纲合并生成

### LLM调用
- 并发控制: 章纲最大10并发，粗纲/大纲最大5并发
- 重试机制: 3次重试，指数退避
- 错误处理: 记录错误日志

### 实时推送
- WebSocket连接管理
- 进度更新推送
- 纲更新推送
- 错误消息推送

## 开发说明

### 数据库初始化

数据库会在首次启动时自动创建，包含5张表：
- books: 书籍信息
- chapters: 章节内容
- outlines: 四层纲数据
- processing_tasks: 处理任务
- errors_log: 错误日志

### 添加新功能

1. 在 `app/services/` 添加业务逻辑
2. 在 `app/api/` 添加API路由
3. 在 `app/models/schemas.py` 添加数据模型
4. 更新 `main.py` 注册路由

## 注意事项

- 文件大小限制: 50MB
- LLM API配置: 需要有效的OpenAI兼容API密钥
- 数据库路径: 默认 `./data/novel_platform.db`
- 上传文件路径: 默认 `./data/uploads/`

## 后续开发

> 完整收尾计划见项目根目录 [docs/后续开发规划.md](../docs/后续开发规划.md)

- [x] 实现LangGraph工作流编排（outline_graph.py 已完成）
- [x] LLM调用封装（llm_service.py 已完成）
- [x] 四层纲生成服务（outline_service.py 已完成）
- [x] WebSocket实时推送（websocket.py 已完成）
- [x] 门禁命令标准化（gate-check.ps1 已完成）
- [x] 密钥清理与轮换（P0 已完成）
- [x] 工作流循环依赖解耦（P2 已完成）
- [x] 工作流测试纳入pytest（P2 已完成）
- [ ] 集成LangSmith监控（P5）
- [ ] 添加任务队列（Celery/RQ）
- [ ] 实现断点续传
- [ ] 添加用户认证
- [ ] 性能优化和缓存
