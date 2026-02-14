"""
密码处理
"""
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

# 密码加密配置 - 仅使用 pbkdf2_sha256（不需要额外依赖）
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    
    Args:
        password: 原始密码
    
    Returns:
        哈希后的密码
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"密码哈希失败: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 原始密码
        hashed_password: 哈希后的密码
    
    Returns:
        True表示密码正确，False表示错误
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False
