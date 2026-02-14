"""
认证系统核心功能测试
这个测试不需要数据库依赖
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试导入"""
    print("\n📦 测试模块导入...")
    try:
        from src.auth.password import hash_password, verify_password
        from src.auth.jwt_handler import create_access_token, verify_token
        print("✅ 所有认证模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_password_hashing():
    """测试密码哈希"""
    print("\n🔐 测试密码哈希...")
    
    try:
        from src.auth.password import hash_password, verify_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        # 验证密码
        assert verify_password(password, hashed), "密码验证失败"
        assert not verify_password("wrong_password", hashed), "错误密码不应该通过"
        
        print("✅ 密码哈希测试通过")
        return True
    except Exception as e:
        print(f"❌ 密码哈希测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jwt_token():
    """测试 JWT Token"""
    print("\n🎫 测试 JWT Token...")
    
    try:
        from src.auth.jwt_handler import create_access_token, verify_token
        from datetime import timedelta
        
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
        assert decoded.role == "user", "角色不匹配"
        
        print("✅ JWT Token 测试通过")
        return True
    except Exception as e:
        print(f"❌ JWT Token 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_expiration():
    """测试Token过期"""
    print("\n⏰ 测试Token过期...")
    
    try:
        from src.auth.jwt_handler import create_access_token, verify_token
        from datetime import timedelta
        import time
        
        # 创建一个立即过期的 Token
        token = create_access_token(
            data={"sub": 1, "username": "test", "role": "user"},
            expires_delta=timedelta(seconds=1)
        )
        
        # 立即验证（应该成功）
        decoded = verify_token(token)
        assert decoded is not None, "新Token应该有效"
        
        # 等待Token过期
        time.sleep(2)
        
        # 再次验证（应该失败）
        decoded = verify_token(token)
        assert decoded is None, "过期Token应该无效"
        
        print("✅ Token 过期测试通过")
        return True
    except Exception as e:
        print(f"❌ Token 过期测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_roles():
    """测试用户角色"""
    print("\n🎭 测试用户角色...")
    
    try:
        from models import UserRole
        
        roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.GUEST]
        expected = ["admin", "manager", "user", "guest"]
        
        for role, expected_value in zip(roles, expected):
            assert role.value == expected_value, f"角色值不匹配: {role}"
            print(f"  ✓ {role.value}")
        
        print("✅ 用户角色测试通过")
        return True
    except Exception as e:
        print(f"❌ 用户角色测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 JWT 认证系统核心功能测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("模块导入", test_imports()))
    results.append(("密码哈希", test_password_hashing()))
    results.append(("JWT Token", test_jwt_token()))
    results.append(("Token 过期", test_token_expiration()))
    results.append(("用户角色", test_user_roles()))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n总体: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n🚀 认证系统已准备就绪")
        print("\n快速开始步骤：")
        print("  1. 安装所有依赖: pip install -r requirements.txt")
        print("  2. 启动后端: python app.py")
        print("  3. 启动前端: cd frontend && npm run dev")
        print("  4. 访问: http://localhost:3000/register")
        print("\n📚 详细指南: 查看 AUTH_IMPLEMENTATION_GUIDE.md")
        return 0
    else:
        print("\n❌ 某些测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
