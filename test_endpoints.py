#!/usr/bin/env python3
"""
测试登录端点
"""
import requests
import json
import sys
import time

def test_login():
    """测试登录端点"""
    base_url = "http://localhost:8000"
    
    # 等待服务器启动
    print("等待服务器启动...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/docs", timeout=1)
            if response.status_code == 200:
                print("✓ 服务器已启动")
                break
        except:
            time.sleep(1)
    else:
        print("✗ 服务器启动超时")
        return False
    
    # 测试登录
    print("\n测试登录端点...")
    try:
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ 登录成功！")
            print(f"  - Token: {result.get('access_token', '')[:50]}...")
            print(f"  - Token Type: {result.get('token_type')}")
            print(f"  - User: {result.get('user', {}).get('username')}")
            return True
        else:
            print(f"✗ 登录失败")
            print(f"应答: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_register():
    """测试注册端点"""
    base_url = "http://localhost:8000"
    
    print("\n测试注册端点...")
    try:
        register_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpass123",
            "full_name": "New User"
        }
        
        response = requests.post(
            f"{base_url}/api/auth/register",
            json=register_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("✓ 注册成功！")
            print(f"  - Username: {result.get('username')}")
            print(f"  - Email: {result.get('email')}")
            print(f"  - Role: {result.get('role')}")
            return True
        elif response.status_code == 400:
            print(f"✗ 注册失败（用户可能已存在）: {response.json().get('detail')}")
            return True  # 这是预期的
        else:
            print(f"✗ 注册失败")
            print(f"应答: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("测试认证端点")
    print("=" * 60)
    
    results = []
    results.append(("登录", test_login()))
    results.append(("注册", test_register()))
    
    print("\n" + "=" * 60)
    print("测试结果:")
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r for _, r in results)
    if all_passed:
        print("\n所有测试都通过了！✓")
        sys.exit(0)
    else:
        print("\n某些测试失败了 ✗")
        sys.exit(1)
