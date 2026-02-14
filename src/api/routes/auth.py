"""
认证相关API路由
包括：登录、注册、用户信息等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import timedelta
from models import (
    User,
    UserRead,
    UserCreate,
    UserLogin,
    Token,
    UserRole,
)
from database import get_db
from src.auth.password import hash_password, verify_password
from src.auth.jwt_handler import create_access_token
from src.auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 认证端点 ====================

@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    Args:
        user_data: 注册数据（username, email, password, full_name）
        db: 数据库会话
    
    Returns:
        新创建的用户信息
    
    Raises:
        HTTPException: 用户已存在或数据验证失败
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(
        User.username == user_data.username
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(
        User.email == user_data.email
    ).first()
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用"
        )
    
    # 创建新用户
    hashed_password = hash_password(user_data.password)
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=UserRole.USER,  # 默认角色
        is_active=True,
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"新用户注册: {user_data.username}")
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/auth/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    Args:
        login_data: 登录数据（username, password）
        db: 数据库会话
    
    Returns:
        Token对象（包含access_token和用户信息）
    
    Raises:
        HTTPException: 用户不存在或密码错误
    """
    # 查询用户
    user = db.query(User).filter(
        User.username == login_data.username
    ).first()
    
    if not user:
        logger.warning(f"登录失败: 用户不存在 {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(login_data.password, user.hashed_password):
        logger.warning(f"登录失败: 密码错误 {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户是否被禁用
    if not user.is_active:
        logger.warning(f"登录失败: 用户被禁用 {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用"
        )
    
    # 创建JWT令牌
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={
            "sub": user.id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"用户登录成功: {user.username}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


@router.get("/auth/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前认证用户的信息
    
    Args:
        current_user: 当前认证用户（自动注入）
    
    Returns:
        当前用户信息
    """
    return current_user


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    刷新访问令牌
    
    Args:
        current_user: 当前认证用户（自动注入）
    
    Returns:
        新的Token对象
    """
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={
            "sub": current_user.id,
            "username": current_user.username,
            "role": current_user.role.value
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"令牌已刷新: {current_user.username}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=current_user
    )


# ==================== 用户管理端点 ====================

@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10
):
    """
    获取用户列表
    
    Args:
        db: 数据库会话
        current_user: 当前认证用户
        skip: 跳过条数
        limit: 限制条数
    
    Returns:
        用户列表
    """
    # 只有管理员可以查看所有用户
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员和经理可以查看用户列表"
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    
    return users


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取特定用户信息
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        用户信息
    
    Raises:
        HTTPException: 用户不存在或无权限
    """
    # 用户只能查看自己的信息，或者管理员可以查看所有用户
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此用户信息"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新用户信息
    
    Args:
        user_id: 用户ID
        user_update: 更新数据
        db: 数据库会话
        current_user: 当前认证用户
    
    Returns:
        更新后的用户信息
    
    Raises:
        HTTPException: 用户不存在或无权限
    """
    # 用户只能更新自己的信息，除非是管理员
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限更新此用户信息"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 不允许更改用户名
    if "username" in user_update:
        del user_update["username"]
    
    # 如果提供了密码，需要哈希处理
    if "password" in user_update:
        user_update["hashed_password"] = hash_password(user_update.pop("password"))
    
    # 只有管理员可以更改角色
    if "role" in user_update and current_user.role != UserRole.ADMIN:
        del user_update["role"]
    
    try:
        for key, value in user_update.items():
            if key not in ["created_at", "hashed_password"]:
                setattr(user, key, value)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"用户信息已更新: {user.username}")
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"更新用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除用户
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前认证用户
    
    Raises:
        HTTPException: 用户不存在、无权限或删除失败
    """
    # 只有管理员可以删除用户
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除用户"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 不允许删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )
    
    try:
        db.delete(user)
        db.commit()
        logger.info(f"用户已删除: {user.username}")
    except Exception as e:
        db.rollback()
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除失败"
        )
