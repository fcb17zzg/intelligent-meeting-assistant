"""
FastAPI主应用
智能会议助手系统后端
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from database import init_db, get_db
from models import User, Meeting, Task

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 应用启动和关闭事件 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动事件
    logger.info("🚀 应用启动...")
    init_db()
    logger.info("✓ 数据库已初始化")
    
    yield
    
    # 关闭事件
    logger.info("🛑 应用关闭...")


# ==================== 创建FastAPI应用 ====================
app = FastAPI(
    title="智能会议助手系统API",
    description="基于AI的会议转录、分析和任务管理系统",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== CORS配置 ====================
origins = [
    "http://localhost:3000",  # 前端开发服务器
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 中间件 ====================
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """添加请求处理时间头"""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ==================== 全局异常处理 ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "内部服务器错误",
            "status_code": 500,
        },
    )


# ==================== 健康检查端点 ====================
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/api/status")
async def api_status(db: Session = Depends(get_db)):
    """API状态检查"""
    try:
        # 尝试查询数据库
        user_count = len(db.query(User).all())
        meeting_count = len(db.query(Meeting).all())
        task_count = len(db.query(Task).all())
        
        return {
            "status": "operational",
            "database": "connected",
            "statistics": {
                "users": user_count,
                "meetings": meeting_count,
                "tasks": task_count,
            },
        }
    except Exception as e:
        logger.error(f"API状态检查失败: {e}")
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
        }


# ==================== 导入并注册路由 ====================

try:
    from src.api.routes import users, meetings, tasks, transcription
    
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(meetings.router, prefix="/api", tags=["meetings"])
    app.include_router(tasks.router, prefix="/api", tags=["tasks"])
    app.include_router(transcription.router, prefix="/api", tags=["transcription"])
    
    logger.info("✓ API路由已注册")
except ImportError as e:
    logger.warning(f"路由导入失败: {e}")


# ==================== 根端点 ====================
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "欢迎使用智能会议助手系统API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "api_status": "/api/status",
    }


# ==================== 文档端点 ====================
@app.get("/docs-json")
async def get_openapi_schema():
    """获取OpenAPI schema"""
    return app.openapi()


if __name__ == "__main__":
    import uvicorn
    
    # 获取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    
    logger.info(f"🚀 启动服务器: {host}:{port}")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
