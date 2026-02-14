"""
用户相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import User, UserRead, UserCreate

router = APIRouter()


@router.get("/users", response_model=list[UserRead])
async def list_users(db: Session = Depends(lambda: None)):
    """
    获取所有用户列表
    """
    # 这里需要依赖注入，暂时简化
    # users = db.exec(select(User)).all()
    return []


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int):
    """
    获取单个用户信息
    """
    # return db.get(User, user_id)
    return {"id": user_id, "username": "test", "email": "test@example.com"}


@router.post("/users", response_model=UserRead)
async def create_user(user: UserCreate):
    """
    创建新用户
    """
    # db_user = User(**user.dict())
    # db.add(db_user)
    # db.commit()
    # db.refresh(db_user)
    # return db_user
    return {"id": 1, **user.dict()}


@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user: UserCreate):
    """
    更新用户信息
    """
    return {"id": user_id, **user.dict()}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """
    删除用户
    """
    return {"message": f"用户 {user_id} 已删除"}
