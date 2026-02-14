# FastAPI 后端应用指南

## 概述

这是智能会议助手系统的FastAPI后端实现，包含：
- 用户管理
- 会议管理
- 任务管理
- 转录处理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

数据库会在应用启动时自动初始化（SQLite）

### 3. 启动应用

```bash
# 开发模式（自动重载）
python -m uvicorn app:app --reload

# 生产模式
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### 4. 访问应用

- **应用首页**: http://localhost:8000
- **API文档**: http://localhost:8000/docs（Swagger UI）
- **RedDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 项目结构

```
├── app.py                      # FastAPI主应用
├── database.py                 # 数据库配置和初始化
├── models.py                   # 数据模型定义（SQLModel）
├── src/
│   └── api/
│       └── routes/
│           ├── users.py        # 用户API
│           ├── meetings.py      # 会议API（核心）
│           ├── tasks.py         # 任务API
│           └── transcription.py # 转录API
├── test_fastapi_setup.py       # 完整性测试脚本
└── requirements.txt            # 依赖列表
```

## 数据库

### 默认配置
- **数据库**: SQLite (meetings.db)
- **ORM**: SQLModel（SQLAlchemy + Pydantic结合）

### 支持PostgreSQL

设置环境变量切换到PostgreSQL：

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/meetings"
```

### 数据库表

已实现的主要数据表：

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| meetings | 会议表 |
| tasks | 任务表 |
| transcript_segments | 转录分段表 |
| comments | 评论表 |

## API端点

### 用户管理 (`/api/users`)
- `GET /api/users` - 获取用户列表
- `GET /api/users/{user_id}` - 获取用户详情
- `POST /api/users` - 创建用户
- `PUT /api/users/{user_id}` - 更新用户
- `DELETE /api/users/{user_id}` - 删除用户

### 会议管理 (`/api/meetings`)
- `GET /api/meetings` - 获取会议列表
- `GET /api/meetings/{meeting_id}` - 获取会议详情
- `POST /api/meetings` - 创建会议
- `PUT /api/meetings/{meeting_id}` - 更新会议
- `DELETE /api/meetings/{meeting_id}` - 删除会议
- `POST /api/meetings/{meeting_id}/upload-audio` - 上传音频
- `POST /api/meetings/{meeting_id}/transcribe` - 开始转录
- `GET /api/meetings/{meeting_id}/summary` - 获取摘要
- `GET /api/meetings/{meeting_id}/key-topics` - 获取关键议题

### 任务管理 (`/api/tasks`)
- `GET /api/tasks` - 获取任务列表（支持多种筛选）
- `GET /api/tasks/{task_id}` - 获取任务详情
- `POST /api/tasks` - 创建任务
- `PUT /api/tasks/{task_id}` - 更新任务
- `DELETE /api/tasks/{task_id}` - 删除任务
- `PATCH /api/tasks/{task_id}/status` - 更新任务状态
- `PATCH /api/tasks/{task_id}/assign` - 分配任务
- `GET /api/tasks/stats/summary` - 获取任务统计

### 转录处理 (`/api/transcription`)
- `POST /api/transcription/transcribe` - 转录音频
- `GET /api/transcription/{id}` - 获取转录结果
- `GET /api/transcription/{id}/segments` - 获取转录分段
- `POST /api/transcription/{id}/enhance` - 优化转录
- `POST /api/transcription/{id}/identify-speakers` - 识别说话人
- `POST /api/transcription/{id}/summarize` - 生成摘要
- `POST /api/transcription/{id}/extract-actions` - 提取行动项
- `POST /api/transcription/{id}/extract-topics` - 提取议题

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | 数据库连接字符串 | sqlite:///./meetings.db |
| HOST | 服务器绑定地址 | 0.0.0.0 |
| PORT | 服务器端口 | 8000 |
| RELOAD | 是否启用自动重载 | True |
| FRONTEND_URL | 前端URL（CORS） | http://localhost:3000 |

## 测试

运行完整性测试：

```bash
python test_fastapi_setup.py
```

该脚本会测试：
- ✓ 模块导入
- ✓ 数据库连接
- ✓ 路由注册
- ✓ API端点

## 开发注意事项

### 1. 依赖注入
使用FastAPI的Depends()进行数据库会话管理：

```python
from fastapi import Depends
from database import get_db
from sqlmodel import Session

@router.get("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):
    # 使用db进行数据库操作
    pass
```

### 2. 数据模型
所有数据模型都使用SQLModel定义，支持：
- Pydantic验证
- SQLAlchemy持久化
- 自动ORM映射

### 3. 路由组织
路由按功能模块分组在`src/api/routes/`中，使用`include_router()`在主应用中注册

## 集成计划

### 与现有模块的集成

**音频处理模块** (`src/audio_processing/`)
```python
from src.audio_processing.api.sync_api import transcribe_audio
# 在API端点中调用
```

**NLP处理模块** (`src/nlp_processing/`)
```python
from src.meeting_insights.processor import MeetingInsightsProcessor
# 用于会议分析和任务提取
```

**可视化模块** (`src/visualization/`)
```python
from src.visualization.report_generator import ReportGenerator
# 生成报告
```

## 部署

### Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 使用docker-compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/meetings
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: meetings
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 故障排查

### SQLModel导入错误
```bash
pip install sqlmodel
```

### Python-multipart错误
```bash
pip install python-multipart
```

### 数据库连接错误
检查`DATABASE_URL`环境变量或使用默认SQLite配置

## 后续开发

1. **用户认证** - 添加JWT认证和权限管理
2. **WebSocket** - 实时转录和通知
3. **任务分配邮件** - 集成邮件通知
4. **报告导出** - PDF、Excel格式导出
5. **缓存** - Redis缓存集成
6. **日志** - 结构化日志记录

## 许可证

MIT License
