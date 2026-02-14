"""
认证系统测试
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database import SessionLocal, init_db
from models import User, UserRole
from src.auth import hash_password, verify_password, create_access_token, verify_token
from datetime import timedelta


def test_password_hashing():
    """测试密码哈希"""
    print("\n🔐 测试密码哈希...")
    
    password = "test_password_123"
    hashed = hash_password(password)
    
    # 验证密码
    assert verify_password(password, hashed), "密码验证失败"
    assert not verify_password("wrong_password", hashed), "错误密码不应该通过"
    
    print("✅ 密码哈希测试通过")


def test_jwt_token():
    """测试 JWT Token"""
    print("\n🎫 测试 JWT Token...")
    
    # 创建 Token
    token_data = {
        "sub": 1,
        "username": "testuser",
        "role": "user"
    }
    
    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(hours=1)
    )
    
    assert token, "Token 创建失败"
    print(f"  Created token: {token[:50]}...")
    
    # 验证 Token
    decoded = verify_token(token)
    assert decoded is not None, "Token 验证失败"
    assert decoded.user_id == 1, "User ID 不匹配"
    assert decoded.username == "testuser", "用户名不匹配"
    
    print("✅ JWT Token 测试通过")


def test_user_creation():
    """测试用户创建"""
    print("\n👤 测试用户创建...")
    
    # 初始化数据库
    init_db()
    
    db = SessionLocal()
    
    # 清除测试用户
    test_user = db.query(User).filter(User.username == "testuser").first()
    if test_user:
        db.delete(test_user)
        db.commit()
    
    # 创建测试用户
    user = User(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        hashed_password=hash_password("password123"),
        role=UserRole.USER,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    assert user.id is not None, "用户 ID 为空"
    assert user.username == "testuser", "用户名不匹配"
    assert user.role == UserRole.USER, "角色不匹配"
    
    print(f"✅ 用户创建测试通过 (ID: {user.id})")
    
    # 清理
    db.delete(user)
    db.commit()
    db.close()


def test_user_roles():
    """测试用户角色"""
    print("\n🎭 测试用户角色...")
    
    db = SessionLocal()
    
    roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.GUEST]
    
    for role in roles:
        assert role.value in ["admin", "manager", "user", "guest"], f"未知角色: {role}"
        print(f"  ✓ {role.value}")
    
    db.close()
    print("✅ 用户角色测试通过")


def test_authentication_flow():
    """测试认证流程"""
    print("\n🔄 测试完整认证流程...")
    
    init_db()
    db = SessionLocal()
    
    # 步骤 1: 清除测试用户
    User_to_delete = db.query(User).filter(User.username == "authtest").first()
    if User_to_delete:
        db.delete(User_to_delete)
        db.commit()
    
    # 步骤 2: 创建用户
    print("  1️⃣  创建用户...")
    user = User(
        username="authtest",
        email="authtest@example.com",
        hashed_password=hash_password("secure_password_123"),
        role=UserRole.USER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"    ✓ 用户创建成功 (ID: {user.id})")
    
    # 步骤 3: 验证密码
    print("  2️⃣  验证密码...")
    assert verify_password("secure_password_123", user.hashed_password)
    assert not verify_password("wrong_password", user.hashed_password)
    print("    ✓ 密码验证成功")
    
    # 步骤 4: 生成 Token
    print("  3️⃣  生成 Token...")
    token = create_access_token(
        data={
            "sub": user.id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=timedelta(hours=1)
    )
    print(f"    ✓ Token 生成成功")
    
    # 步骤 5: 验证 Token
    print("  4️⃣  验证 Token...")
    token_data = verify_token(token)
    assert token_data is not None
    assert token_data.user_id == user.id
    assert token_data.role == UserRole.USER.value
    print("    ✓ Token 验证成功")
    
    # 清理
    db.delete(user)
    db.commit()
    db.close()
    
    print("✅ 认证流程测试通过")


def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 JWT 认证系统测试")
    print("=" * 50)
    
    try:
        # 运行测试
        test_password_hashing()
        test_jwt_token()
        test_user_roles()
        test_user_creation()
        test_authentication_flow()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        print("\n🚀 认证系统已准备就绪")
        print("\n快速开始：")
        print("  1. 后端: python app.py")
        print("  2. 前端: cd frontend && npm run dev")
        print("  3. 访问: http://localhost:3000/register")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
