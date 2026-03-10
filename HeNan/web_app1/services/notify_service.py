"""
邮件提醒服务
- 读取/保存邮件配置（JSON）
- 查询下月到期版权数据
- 发送提醒邮件
- 维护本地幂等状态
- 提供应用内定时调度
"""
from __future__ import annotations

import json
import smtplib
import threading
from collections import Counter
from copy import deepcopy
from datetime import datetime, date, time
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pymysql
from apscheduler.schedulers.background import BackgroundScheduler

from database import get_db
from logging_config import logger

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "notify_config.json"
STATE_DIR = BASE_DIR / "runtime"
STATE_PATH = STATE_DIR / "notify_state.json"

DEFAULT_NOTIFY_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "smtp": {
        "host": "",
        "port": 587,
        "use_tls": True,
        "username": "",
        "password": "",
        "from_name": "运营管理平台",
    },
    "recipients": [],
    "schedule": {
        "day": 1,
        "time": "09:00",
    },
    "rule": {
        "months_before_expiry": 1,
    },
}

DEFAULT_NOTIFY_STATE: Dict[str, Any] = {
    "last_sent_month": "",
    "last_sent_at": "",
    "last_result": "never",
    "last_count": 0,
    "last_error": "",
    "last_trigger": "",
}

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _ensure_config_file() -> None:
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.write_text(
        json.dumps(DEFAULT_NOTIFY_CONFIG, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_notify_config() -> Dict[str, Any]:
    _ensure_config_file()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return _merge_dict(DEFAULT_NOTIFY_CONFIG, raw)
    except Exception as exc:
        logger.error(f"读取邮件配置失败，使用默认配置: {exc}")
        return deepcopy(DEFAULT_NOTIFY_CONFIG)


def _normalize_recipients(recipients: Any) -> List[str]:
    if recipients is None:
        return []
    if isinstance(recipients, str):
        parts = [p.strip() for p in recipients.replace("\n", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(recipients, list):
        return [str(item).strip() for item in recipients if str(item).strip()]
    return []


def validate_notify_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    smtp = config.get("smtp", {})
    recipients = _normalize_recipients(config.get("recipients"))

    host = str(smtp.get("host", "")).strip()
    username = str(smtp.get("username", "")).strip()
    password = str(smtp.get("password", "")).strip()

    if not host:
        return False, "SMTP服务器不能为空"
    if not username:
        return False, "SMTP账号不能为空"
    if not password:
        return False, "SMTP授权码不能为空"
    if not recipients:
        return False, "收件人不能为空"

    return True, "ok"


def save_notify_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    old = load_notify_config()
    merged = _merge_dict(old, payload or {})

    merged["recipients"] = _normalize_recipients(merged.get("recipients"))

    schedule = merged.get("schedule", {})
    schedule.setdefault("day", 1)
    schedule_time = str(schedule.get("time", "09:00")).strip() or "09:00"
    schedule["time"] = schedule_time
    merged["schedule"] = schedule

    smtp = merged.get("smtp", {})
    smtp["port"] = int(smtp.get("port", 587) or 587)
    smtp["use_tls"] = bool(smtp.get("use_tls", True))

    incoming_password = payload.get("smtp", {}).get("password") if isinstance(payload.get("smtp"), dict) else None
    if incoming_password in (None, ""):
        smtp["password"] = old.get("smtp", {}).get("password", "")
    merged["smtp"] = smtp

    CONFIG_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def sanitize_notify_config(config: Dict[str, Any]) -> Dict[str, Any]:
    data = deepcopy(config)
    if "smtp" not in data:
        data["smtp"] = {}
    password = str(data["smtp"].get("password", ""))
    data["smtp"]["password"] = "******" if password else ""
    data["smtp"]["password_configured"] = bool(password)
    return data


def _ensure_state_file() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_PATH.exists():
        return
    STATE_PATH.write_text(
        json.dumps(DEFAULT_NOTIFY_STATE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_notify_state() -> Dict[str, Any]:
    _ensure_state_file()
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return _merge_dict(DEFAULT_NOTIFY_STATE, raw)
    except Exception as exc:
        logger.error(f"读取提醒状态失败，使用默认状态: {exc}")
        return deepcopy(DEFAULT_NOTIFY_STATE)


def save_notify_state(state: Dict[str, Any]) -> None:
    _ensure_state_file()
    merged = _merge_dict(DEFAULT_NOTIFY_STATE, state or {})
    STATE_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


def _month_window(base_day: date | None = None) -> Tuple[date, date]:
    d = base_day or date.today()
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)

    if next_month.month == 12:
        month_after = date(next_month.year + 1, 1, 1)
    else:
        month_after = date(next_month.year, next_month.month + 1, 1)
    return next_month, month_after


def query_next_month_expiring_records() -> Dict[str, Any]:
    start_day, end_day = _month_window()
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT id, media_name, operator_name, upstream_copyright, copyright_start_date, category_level1, copyright_end_date
            FROM copyright_content
            WHERE copyright_end_date IS NOT NULL
              AND copyright_end_date >= %s
              AND copyright_end_date < %s
            ORDER BY copyright_end_date ASC, operator_name ASC, media_name ASC
            """,
            (start_day, end_day),
        )
        rows = cursor.fetchall()

    group_counter = Counter((row.get("operator_name") or "未填写运营商") for row in rows)
    groups = [{"operator_name": name, "count": count} for name, count in sorted(group_counter.items(), key=lambda x: x[0])]

    return {
        "window": {
            "start": start_day.isoformat(),
            "end": end_day.isoformat(),
            "month": start_day.strftime("%Y-%m"),
        },
        "total": len(rows),
        "groups": groups,
        "records": rows,
    }


def query_upcoming_expiring_records() -> Dict[str, Any]:
    today = date.today()
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT id, media_name, operator_name, upstream_copyright, copyright_start_date, category_level1, copyright_end_date
            FROM copyright_content
            WHERE copyright_end_date IS NOT NULL
              AND copyright_end_date >= %s
            ORDER BY copyright_end_date ASC, operator_name ASC, media_name ASC
            """,
            (today,),
        )
        rows = cursor.fetchall()

    return {
        "window": {
            "start": today.isoformat(),
            "type": "upcoming",
        },
        "total": len(rows),
        "records": rows,
    }


def _build_email_content(preview: Dict[str, Any]) -> Tuple[str, str]:
    month = preview["window"]["month"]
    total = preview["total"]

    lines = [
        f"【版权到期提醒】下月到期版权清单（{month}）",
        "",
        f"总计: {total} 条",
        "",
        "按运营商统计:",
    ]
    for group in preview["groups"]:
        lines.append(f"- {group['operator_name']}: {group['count']} 条")

    lines.append("")
    lines.append("明细:")
    for idx, row in enumerate(preview["records"], start=1):
        lines.append(f"{idx}.")
        lines.append(f"  到期时间: {row.get('copyright_end_date') or '-'}")
        lines.append(f"  介质名称: {row.get('media_name') or '-'}")
        lines.append(f"  运营商: {row.get('operator_name') or '-'}")
        lines.append(f"  上游版权方: {row.get('upstream_copyright') or '-'}")
        lines.append("")

    lines.append("")
    lines.append("请及时处理到期版权。")

    subject = f"[版权到期提醒] 下月到期版权清单（{month}）"
    body = "\n".join(lines)
    return subject, body


def _send_email(config: Dict[str, Any], subject: str, body: str, recipients: List[str]) -> None:
    smtp = config.get("smtp", {})

    msg = EmailMessage()
    from_name = str(smtp.get("from_name", "运营管理平台")).strip() or "运营管理平台"
    from_user = str(smtp.get("username", "")).strip()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_user}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    host = str(smtp.get("host", "")).strip()
    port = int(smtp.get("port", 587) or 587)
    username = from_user
    password = str(smtp.get("password", "")).strip()
    use_tls = bool(smtp.get("use_tls", True))

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        server.login(username, password)
        server.send_message(msg)


def send_test_email() -> Dict[str, Any]:
    config = load_notify_config()
    ok, message = validate_notify_config(config)
    if not ok:
        return {"status": "failed", "message": message}

    recipients = _normalize_recipients(config.get("recipients"))
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = "[测试邮件] 版权到期提醒配置测试"
    body = f"这是一封测试邮件。\n发送时间: {now_text}\n若收到此邮件，说明SMTP配置可用。"

    _send_email(config, subject, body, recipients)
    return {"status": "success", "message": "测试邮件发送成功", "recipients": recipients}


def run_monthly_notify(force: bool = False, trigger: str = "manual") -> Dict[str, Any]:
    now = datetime.now()
    config = load_notify_config()

    if not config.get("enabled", False) and not force:
        return {"status": "skipped", "message": "邮件提醒已禁用"}

    ok, message = validate_notify_config(config)
    if not ok:
        return {"status": "failed", "message": message}

    if now.day != 1 and not force:
        return {"status": "skipped", "message": "今天不是每月1号，跳过执行"}

    preview = query_next_month_expiring_records()
    target_month = preview["window"]["month"]

    state = load_notify_state()
    if state.get("last_sent_month") == target_month and not force:
        return {"status": "skipped", "message": f"{target_month} 已发送提醒，跳过执行", "preview": preview}

    if preview["total"] == 0:
        save_notify_state({
            "last_result": "skipped",
            "last_sent_at": now.isoformat(timespec="seconds"),
            "last_error": "",
            "last_count": 0,
            "last_trigger": trigger,
        })
        return {"status": "skipped", "message": "下个月无到期版权数据", "preview": preview}

    subject, body = _build_email_content(preview)
    recipients = _normalize_recipients(config.get("recipients"))
    _send_email(config, subject, body, recipients)

    save_notify_state({
        "last_sent_month": target_month,
        "last_sent_at": now.isoformat(timespec="seconds"),
        "last_result": "success",
        "last_count": preview["total"],
        "last_error": "",
        "last_trigger": trigger,
    })

    return {
        "status": "success",
        "message": f"提醒邮件发送成功，共 {preview['total']} 条",
        "preview": preview,
        "target_month": target_month,
        "recipients": recipients,
    }


def _parse_schedule_time(config: Dict[str, Any]) -> Tuple[int, int]:
    schedule = config.get("schedule", {})
    raw = str(schedule.get("time", "09:00")).strip() or "09:00"
    try:
        hh, mm = raw.split(":", 1)
        hour = max(0, min(23, int(hh)))
        minute = max(0, min(59, int(mm)))
        return hour, minute
    except Exception:
        return 9, 0


def _scheduled_job() -> None:
    try:
        result = run_monthly_notify(force=False, trigger="scheduler")
        logger.info(f"定时提醒任务执行结果: {result.get('status')} - {result.get('message')}")
    except Exception as exc:
        logger.exception(f"定时提醒任务执行失败: {exc}")
        save_notify_state({
            "last_result": "failed",
            "last_sent_at": datetime.now().isoformat(timespec="seconds"),
            "last_error": str(exc),
            "last_trigger": "scheduler",
        })


def _run_startup_compensation() -> None:
    config = load_notify_config()
    hour, minute = _parse_schedule_time(config)
    now = datetime.now()
    target_time = time(hour=hour, minute=minute)
    if now.day == 1 and now.time() >= target_time:
        try:
            result = run_monthly_notify(force=False, trigger="startup_compensation")
            logger.info(f"启动补偿检查结果: {result.get('status')} - {result.get('message')}")
        except Exception as exc:
            logger.exception(f"启动补偿检查失败: {exc}")


def start_notify_scheduler() -> None:
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            return

        config = load_notify_config()
        hour, minute = _parse_schedule_time(config)

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            _scheduled_job,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="copyright_expiry_notify_job",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info(f"邮件提醒调度器已启动: 每天 {hour:02d}:{minute:02d} 执行")

    _run_startup_compensation()


def reload_notify_scheduler() -> None:
    stop_notify_scheduler()
    start_notify_scheduler()


def stop_notify_scheduler() -> None:
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("邮件提醒调度器已停止")
        _scheduler = None


def get_notify_status() -> Dict[str, Any]:
    state = load_notify_state()
    scheduler_running = bool(_scheduler and _scheduler.running)
    next_run = None
    if scheduler_running:
        try:
            job = _scheduler.get_job("copyright_expiry_notify_job")
            next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
        except Exception:
            next_run = None

    return {
        "scheduler_running": scheduler_running,
        "scheduler_next_run": next_run,
        "state": state,
    }
