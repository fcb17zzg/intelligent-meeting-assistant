#!/usr/bin/env python3
"""
最终验证 - 确认所有认证功能正常工作
"""
import requests
import json
import sys

def verify_system():
    """验证整个认证系统"""
    print("=" * 70)
    print("JWT 认证系统 - 最终验证")
    print("=" * 70)
    
    base_url = "http://localhost:8000"
    all_passed = True
    
    # 1. 验证服务器运行中
    print("\n[1] 验证服务器状态...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✓ FastAPI 服务器正在运行")
        else:
            print(f"✗ 服务器返回状态码: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"✗ 无法连接到服务器: {e}")
        return False
    
    # 2. 验证数据库初始化
    print("\n[2] 验证数据库用户...")
    try:
        # 先登录admin来获取token
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        if login_response.status_code != 200:
            print(f"✗ Admin 登录失败")
            all_passed = False
        else:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 获取用户列表
            users_response = requests.get(
                f"{base_url}/api/users/",
                headers=headers
            )
            
            if users_response.status_code == 200:
                users = users_response.json()
                print(f"✓ 数据库初始化正常 - {len(users)} 个用户")
                for u in users:
                    print(f"  - {u['username']} ({u['role']})")
            else:
                print(f"✗ 获取用户列表失败: {users_response.text}")
                all_passed = False
                
    except Exception as e:
        print(f"✗ 错误: {e}")
        all_passed = False
    
    # 3. 验证认证流程
    print("\n[3] 验证完整认证流程...")
    
    flows = [
        {"username": "admin", "password": "admin123", "name": "管理员"},
        {"username": "testuser", "password": "testpass123", "name": "测试用户"},
    ]
    
    for flow in flows:
        try:
            # 登录
            login_resp = requests.post(
                f"{base_url}/api/auth/login",
                json={"username": flow["username"], "password": flow["password"]}
            )
            
            if login_resp.status_code != 200:
                print(f"✗ {flow['name']} 登录失败")
                all_passed = False
                continue
            
            token = login_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 获取用户信息
            me_resp = requests.get(f"{base_url}/api/auth/me", headers=headers)
            
            if me_resp.status_code == 200:
                user = me_resp.json()
                print(f"✓ {flow['name']} 认证成功 - {user['username']} ({user['role']})")
            else:
                print(f"✗ {flow['name']} 获取用户信息失败")
                all_passed = False
                
        except Exception as e:
            print(f"✗ {flow['name']} 验证错误: {e}")
            all_passed = False
    
    # 4. 验证注册功能
    print("\n[4] 验证注册功能...")
    try:
        import random
        import string
        
        # 生成随机用户名
        random_username = "verify_" + "".join(random.choices(string.ascii_lowercase, k=8))
        
        register_resp = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "username": random_username,
                "email": f"{random_username}@test.com",
                "password": "testpass123",
                "full_name": "Verification User"
            }
        )
        
        if register_resp.status_code == 201:
            new_user = register_resp.json()
            print(f"✓ 注册成功 - {new_user['username']}")
            
            # 尝试用新用户登录
            login_resp = requests.post(
                f"{base_url}/api/auth/login",
                json={"username": random_username, "password": "testpass123"}
            )
            
            if login_resp.status_code == 200:
                print(f"✓ 新用户登录成功")
            else:
                print(f"✗ 新用户登录失败")
                all_passed = False
        else:
            print(f"✗ 注册失败: {register_resp.text}")
            all_passed = False
            
    except Exception as e:
        print(f"✗ 注册验证错误: {e}")
        all_passed = False
    
    # 5. 验证权限保护
    print("\n[5] 验证权限保护...")
    try:
        # 尝试无token访问
        response = requests.get(f"{base_url}/api/auth/me")
        
        if response.status_code in [401, 403]:
            print("✓ 无token访问被正确拒绝")
        else:
            print(f"✗ 无token访问没有被拒绝 (状态: {response.status_code})")
            all_passed = False
        
        # 尝试无效token访问
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = requests.get(f"{base_url}/api/auth/me", headers=headers)
        
        if response.status_code in [401, 403]:
            print("✓ 无效token被正确拒绝")
        else:
            print(f"✗ 无效token没有被拒绝 (状态: {response.status_code})")
            all_passed = False
            
    except Exception as e:
        print(f"✗ 权限保护验证错误: {e}")
        all_passed = False
    
    # 最终结果
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 所有验证都通过了！")
        print("JWT 认证系统已完全修复并正常工作")
        print("=" * 70)
        print("\n可以开始以下操作:")
        print("1. 在浏览器中访问 http://localhost:3001")
        print("2. 使用账户登录：")
        print("   - admin / admin123 (管理员)")
        print("   - testuser / testpass123 (普通用户)")
        print("3. 测试所有认证功能")
        return True
    else:
        print("⚠️  某些验证失败了")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = verify_system()
    sys.exit(0 if success else 1)
