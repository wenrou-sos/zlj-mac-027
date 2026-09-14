"""认证与审计：登录、当前用户、操作日志查询"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, ROLE_NAMES, get_current_user, make_token, require_roles, verify_password
from ..database import get_db
from ..models import AuditLog, User
from ..services import log_action

router = APIRouter(prefix="/api", tags=["认证与审计"])


class LoginIn(BaseModel):
    username: str
    password: str


def user_info(user: dict) -> dict:
    return {
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "role_name": ROLE_NAMES.get(user["role"], user["role"]),
    }


@router.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = make_token(user)
    # 登录也留痕
    log_action(db, {"uid": user.id, "username": user.username, "name": user.name, "role": user.role},
               "登录", "user", user.id, f"{user.name} 登录系统")
    db.commit()
    return {"token": token, "user": user_info({"username": user.username, "name": user.name, "role": user.role})}


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user_info(user)


@router.get("/audit-logs")
def audit_logs(
    action: Optional[str] = None,
    keyword: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles(ROLE_ADMIN)),
):
    """操作日志分页查询（仅食品安全管理员）"""
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if keyword:
        q = q.filter((AuditLog.user_name.contains(keyword))
                     | (AuditLog.detail.contains(keyword))
                     | (AuditLog.username.contains(keyword)))
    if date_from:
        q = q.filter(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))

    total = q.count()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    rows = (q.order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all())
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "user_name": r.user_name,
                "username": r.username,
                "role": r.role,
                "role_name": ROLE_NAMES.get(r.role, r.role),
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "detail": r.detail,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
