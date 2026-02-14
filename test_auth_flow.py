#!/usr/bin/env python3
"""
测试完整的认证流程
模拟前端的登录和受保护资源访问
"""
import requests
import json
import sys

def test_full_auth_flow():
    """测试完整的认证流程"""
    base_url = "http://localhost:8000"
    
    print("=" * 70)
    print("测试完整认证流程")
    print("=" * 70)
    
    # 1. 测试登录
    print("\n[1/4] 测试登录...")
    try:
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code != 200:
            print(f"✗ 登录失败: {response.text}")
            return False
            
        token_data = response.json()
        access_token = token_data.get("access_token")
        token_type = token_data.get("token_type")
        user = token_data.get("user")
        
        print(f"✓ 登录成功")
        print(f"  - 用户: {user.get('username')}")
        print(f"  - 角色: {user.get('role')}")
        print(f"  - Token: {access_token[:30]}...")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False
    
    # 2. 测试获取当前用户信息 (/me 端点)
    print("\n[2/4] 测试获取当前用户信息...")
    try:
        headers = {
            "Authorization": f"{token_type} {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{base_url}/api/auth/me",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"✗ 获取用户信息失败: {response.text}")
            return False
            
        user_info = response.json()
        print(f"✓ 成功获取用户信息")
        print(f"  - 用户名: {user_info.get('username')}")
        print(f"  - Email: {user_info.get('email')}")
        print(f"  - 全名: {user_info.get('full_name')}")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False
    
    # 3. 测试刷新令牌
    print("\n[3/4] 测试刷新令牌...")
    try:
        response = requests.post(
            f"{base_url}/api/auth/refresh",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"✗ 刷新令牌失败: {response.text}")
            return False
            
        new_token_data = response.json()
        new_token = new_token_data.get("access_token")
        
        print(f"✓ 成功刷新令牌")
        print(f"  - 新Token: {new_token[:30]}...")
        
        # 使用新token进行后续请求
        headers["Authorization"] = f"{token_type} {new_token}"
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False
    
    # 4. 测试获取用户列表（管理员功能）
    print("\n[4/4] 测试获取用户列表...")
    try:
        response = requests.get(
            f"{base_url}/api/users/",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"✗ 获取用户列表失败: {response.text}")
            return False
            
        users = response.json()
        print(f"✓ 成功获取用户列表")
        print(f"  - 用户数: {len(users)}")
        for u in users:
            print(f"    - {u.get('username')} ({u.get('role')})")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False
    
    return True

def test_unauthorized_access():
    """测试未授权访问"""
    base_url = "http://localhost:8000"
    
    print("\n" + "=" * 70)
    print("测试未授权访问保护")
    print("=" * 70)
    
    print("\n测试无效token访问 /api/auth/me...")
    try:
        headers = {
            "Authorization": "Bearer invalid-token",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{base_url}/api/auth/me",
            headers=headers
        )
        
        if response.status_code == 401:
            print("✓ 正确拒绝了无效token")
        else:
            print(f"✗ 应该返回401，但得到: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False
    
    print("\ntest 无token访问 /api/auth/me...")
    try:
        response = requests.get(
            f"{base_url}/api/auth/me",
        )
        
        if response.status_code in [401, 403]:
            print("✓ 正确拒绝了无token请求")
        else:
            print(f"✗ 应该返回401/403，但得到: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = True
    
    if test_full_auth_flow():
        print("\n" + "=" * 70)
        print("✓ 完整认证流程测试通过")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ 完整认证流程测试失败")
        print("=" * 70)
        success = False
    
    if test_unauthorized_access():
        print("\n" + "=" * 70)
        print("✓ 未授权访问保护测试通过")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ 未授权访问保护测试失败")
        print("=" * 70)
        success = False
    
    sys.exit(0 if success else 1)
