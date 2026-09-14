"""认证与权限：密码哈希、令牌签发/校验、FastAPI 依赖。

令牌为无状态 HMAC 签名（base64url(payload).signature），服务重启不失效；
密钥通过环境变量 SECRET_KEY 配置，生产环境务必修改。
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Depends, Header, HTTPException

SECRET_KEY = os.getenv("SECRET_KEY", "canteen-dev-secret-change-in-production")
TOKEN_TTL_SECONDS = 12 * 3600  # 令牌有效期12小时

# 角色定义
ROLE_ADMIN = "admin"          # 食品安全管理员：全部权限
ROLE_KEEPER = "keeper"        # 留样人：仅留样登记与销毁
ROLE_PURCHASER = "purchaser"  # 采购员：仅采购与供应商维护
ROLE_VIEWER = "viewer"        # 其他岗位/检查人员：只读

ROLE_NAMES = {
    ROLE_ADMIN: "食品安全管理员",
    ROLE_KEEPER: "留样人",
    ROLE_PURCHASER: "采购员",
    ROLE_VIEWER: "检查人员",
}


# ---------- 密码 ----------
def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 20000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 20000).hex()
    return hmac.compare_digest(candidate, digest)


# ---------- 令牌 ----------
def make_token(user) -> str:
    payload = {
        "uid": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def parse_token(token: str) -> dict | None:
    try:
        raw, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(raw.encode()))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ---------- FastAPI 依赖 ----------
def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """解析 Bearer 令牌，未登录/过期一律 401"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录或登录已过期")
    payload = parse_token(authorization[7:])
    if not payload:
        raise HTTPException(401, "未登录或登录已过期")
    return payload


def require_roles(*roles: str):
    """限定角色才可访问，否则 403"""
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, "当前岗位无权执行此操作")
        return user
    return dependency
