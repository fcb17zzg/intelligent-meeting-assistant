"""
JWT Token处理
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import ValidationError
from models import TokenData, UserRole
import logging

logger = logging.getLogger(__name__)

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
    
    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    
    # 确保 sub 是字符串
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token创建失败: {e}")
        raise


def verify_token(token: str) -> Optional[TokenData]:
    """
    验证JWT令牌
    
    Args:
        token: JWT令牌
    
    Returns:
        TokenData对象或None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))  # 转换为 int
        username: str = payload.get("username")
        role: str = payload.get("role", "user")
        
        if user_id is None:
            logger.warning("Token中缺少user_id")
            return None
        
        token_data = TokenData(
            user_id=user_id,
            username=username,
            role=role
        )
        return token_data
    except jwt.ExpiredSignatureError:
        logger.warning("Token已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token无效: {e}")
        return None
    except (ValueError, TypeError) as e:
        logger.warning(f"Token数据转换失败: {e}")
        return None
    except ValidationError as e:
        logger.warning(f"Token数据验证失败: {e}")
        return None


def get_token_data(token: str) -> Optional[TokenData]:
    """
    获取Token中的数据
    
    Args:
        token: JWT令牌
    
    Returns:
        TokenData对象或None
    """
    return verify_token(token)


def check_token_expiration(token: str) -> bool:
    """
    检查Token是否过期
    
    Args:
        token: JWT令牌
    
    Returns:
        True表示未过期，False表示已过期
    """
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False
