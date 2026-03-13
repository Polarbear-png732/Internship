"""邮件提醒配置与执行路由"""
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query

from services.notify_service import (
    get_notify_status,
    load_notify_config,
    query_next_month_expiring_records,
    query_upcoming_expiring_records,
    reload_notify_scheduler,
    run_monthly_notify,
    sanitize_notify_config,
    save_notify_config,
    send_test_email,
    validate_notify_config,
)

router = APIRouter(prefix="/api/notify", tags=["邮件提醒"])


@router.get("/config")
def get_notify_config() -> Dict[str, Any]:
    config = load_notify_config()
    return {"code": 200, "message": "success", "data": sanitize_notify_config(config)}


@router.put("/config")
def update_notify_config(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        config = save_notify_config(payload)
        ok, message = validate_notify_config(config)
        reload_notify_scheduler()
        return {
            "code": 200,
            "message": "success",
            "data": {
                "config": sanitize_notify_config(config),
                "config_valid": ok,
                "config_message": message,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/preview")
def get_notify_preview() -> Dict[str, Any]:
    try:
        preview = query_upcoming_expiring_records()
        return {"code": 200, "message": "success", "data": preview}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/test")
def test_notify_email() -> Dict[str, Any]:
    try:
        result = send_test_email()
        code = 200 if result.get("status") == "success" else 400
        return {"code": code, "message": result.get("message", ""), "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/run")
def run_notify_job(force: bool = Query(True, description="是否强制执行，默认true")) -> Dict[str, Any]:
    try:
        result = run_monthly_notify(force=force, trigger="manual")
        code = 200 if result.get("status") in {"success", "skipped"} else 400
        return {"code": code, "message": result.get("message", ""), "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
def notify_status() -> Dict[str, Any]:
    try:
        status = get_notify_status()
        return {"code": 200, "message": "success", "data": status}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
