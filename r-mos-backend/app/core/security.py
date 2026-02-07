"""
认证安全工具（Gate-1 / A-001）。
"""
from __future__ import annotations

import base64
import binascii
import hmac
import hashlib
import os
import re


def is_strong_password(password: str) -> bool:
    """最小密码强度校验：长度>=8，且同时包含字母与数字。"""
    if len(password) < 8:
        return False
    has_letter = re.search(r"[A-Za-z]", password) is not None
    has_digit = re.search(r"\d", password) is not None
    return has_letter and has_digit


def hash_password(password: str) -> str:
    """使用标准库 PBKDF2 生成密码摘要。"""
    iterations = 310000
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    """校验明文密码是否与已存摘要匹配。"""
    try:
        algorithm, iterations_text, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_b64.encode("ascii"), validate=True)
        expected_digest = base64.b64decode(digest_b64.encode("ascii"), validate=True)
    except (ValueError, binascii.Error):
        return False

    calculated_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(calculated_digest, expected_digest)


def hash_token(token: str) -> str:
    """刷新令牌哈希（避免明文落库）。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
