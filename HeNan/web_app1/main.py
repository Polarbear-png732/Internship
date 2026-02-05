"""
FastAPI 应用主入口
提供视频内容运营管理平台的核心服务，包括客户管理、剧集管理、版权数据管理等功能
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path

from routers import customers, dramas, episodes, copyright, scan_result
from logging_config import logger

# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(title="运营管理平台", description="剧集信息管理系统")


# ============================================================
# 全局异常处理器
# ============================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    HTTP异常处理器
    记录异常日志，返回标准化错误响应
    """
    logger.warning(
        f"HTTP {exc.status_code} | {request.method} {request.url.path} | {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    请求验证错误处理器
    处理参数验证失败的情况
    """
    errors = exc.errors()
    error_messages = [f"{err['loc'][-1]}: {err['msg']}" for err in errors]
    
    logger.warning(
        f"Validation Error | {request.method} {request.url.path} | {error_messages}"
    )
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求参数验证失败",
            "details": error_messages,
            "error_code": "VALIDATION_ERROR"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    捕获所有未处理的异常，避免暴露敏感信息（如SQL错误）
    """
    # 记录完整错误信息到日志（包含堆栈跟踪）
    logger.exception(
        f"Unhandled Exception | {request.method} {request.url.path} | {type(exc).__name__}: {str(exc)}"
    )
    
    # 返回通用错误消息，不暴露内部细节
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误，请稍后重试",
            "error_code": "INTERNAL_ERROR"
        }
    )

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 注册路由
app.include_router(customers.router)
app.include_router(dramas.router)
app.include_router(episodes.router)
app.include_router(copyright.router)
app.include_router(scan_result.router)


@app.get("/")
async def read_root():
    """返回首页"""
    return FileResponse(str(BASE_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
