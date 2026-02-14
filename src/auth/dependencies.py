"""
认证依赖注入
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from models import User, UserRole, TokenData
from database import get_db
from .jwt_handler import verify_token
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer认证
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前认证用户
    
    Args:
        credentials: HTTP认证凭证
        db: 数据库会话
    
    Returns:
        User对象
    
    Raises:
        HTTPException: 认证失败或用户不存在
    """
    token = credentials.credentials
    
    # 验证token
    token_data = verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从数据库获取用户
    try:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户已被禁用",
            )
        
        return user
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前管理员用户
    
    Args:
        current_user: 当前认证用户
    
    Returns:
        User对象（管理员）
    
    Raises:
        HTTPException: 用户不是管理员
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以访问此资源",
        )
    
    return current_user


def require_role(*roles: UserRole):
    """
    创建角色检查依赖
    
    Args:
        roles: 允许的角色列表
    
    Returns:
        异步依赖函数
    """
    async def check_role(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """检查用户角色"""
        if current_user.role not in roles:
            role_names = ", ".join([r.value for r in roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"此操作需要以下角色之一: {role_names}",
            )
        return current_user
    
    return check_role


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    获取可选的认证用户
    
    Args:
        credentials: HTTP认证凭证
        db: 数据库会话
    
    Returns:
        User对象或None
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data is None:
        return None
    
    try:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        return user if user and user.is_active else None
    except Exception as e:
        logger.error(f"获取可选用户失败: {e}")
        return None
