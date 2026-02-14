#!/usr/bin/env python3
"""
测试修复后的登录功能
验证数据库查询方法是否正确
"""
import sys
from database import SessionLocal
from models import User
from src.auth.password import verify_password

def test_login_query():
    """测试登录查询是否能够工作"""
    db = SessionLocal()
    try:
        print("测试登录查询...")
        
        # 尝试用新的query()方法查询用户
        user = db.query(User).filter(
            User.username == "testuser"
        ).first()
        
        if user:
            print(f"✓ 成功查询到用户: {user.username}")
            print(f"  - Email: {user.email}")
            print(f"  - Role: {user.role}")
            
            # 测试密码验证
            if verify_password("testpass123", user.hashed_password):
                print("✓ 密码验证成功")
                return True
            else:
                print("✗ 密码验证失败")
                return False
        else:
            print("✗ 找不到测试用户")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_register_check():
    """测试注册时的username检查"""
    db = SessionLocal()
    try:
        print("\n测试用户名检查...")
        
        # 尝试检查admin是否存在
        existing = db.query(User).filter(
            User.username == "admin"
        ).first()
        
        if existing:
            print(f"✓ 成功检查到已存在用户: {existing.username}")
            return True
        else:
            print("✗ 检查失败")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_list_users():
    """测试列表用户查询"""
    db = SessionLocal()
    try:
        print("\n测试用户列表查询...")
        
        users = db.query(User).offset(0).limit(10).all()
        
        if users:
            print(f"✓ 成功查询到 {len(users)} 个用户:")
            for u in users:
                print(f"  - {u.username} ({u.role})")
            return True
        else:
            print("✗ 没有查询到用户")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_get_user():
    """测试获取单个用户"""
    db = SessionLocal()
    try:
        print("\n测试获取单个用户...")
        
        # 先找到一个用户ID
        first_user = db.query(User).first()
        if not first_user:
            print("✗ 没有用户")
            return False
            
        user = db.query(User).filter(User.id == first_user.id).first()
        
        if user:
            print(f"✓ 成功获取用户: {user.username}")
            return True
        else:
            print("✗ 获取失败")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("验证数据库查询修复")
    print("=" * 60)
    
    results = []
    results.append(("登录查询", test_login_query()))
    results.append(("用户名检查", test_register_check()))
    results.append(("用户列表", test_list_users()))
    results.append(("获取单个用户", test_get_user()))
    
    print("\n" + "=" * 60)
    print("测试结果摘要:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试都通过了！✓")
        sys.exit(0)
    else:
        print("某些测试失败了 ✗")
        sys.exit(1)
