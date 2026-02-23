"""
测试摘要持久化功能
验证会议摘要是否能正确保存到数据库并在刷新后恢复
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_summary_persistence():
    """测试摘要持久化全流程"""
    print("=" * 60)
    print("测试摘要持久化功能")
    print("=" * 60)
    
    # 步骤1: 创建会议
    print("\n📝 步骤1: 创建会议...")
    meeting_data = {
        "title": "测试会议-摘要持久化",
        "description": "用于测试摘要是否能被正确保存",
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "duration": 60,
        "participants": 5,
        "location": "会议室A"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/meetings", json=meeting_data)
        if resp.status_code != 200:
            print(f"❌ 创建会议失败: {resp.status_code}")
            print(f"   响应: {resp.text}")
            return False
        
        meeting = resp.json()
        meeting_id = meeting["id"]
        print(f"✅ 创建会议成功, ID: {meeting_id}")
    except Exception as e:
        print(f"❌ 创建会议出错: {e}")
        return False
    
    # 步骤2: 更新会议摘要（模拟前端保存摘要）
    print("\n📝 步骤2: 保存摘要到数据库...")
    summary_data = {
        "summary": "这是一个测试摘要。会议讨论了项目进度，前端完成80%，后端70%",
        "key_topics": json.dumps(["项目进度", "任务分配", "时间表"]),
        "summary_type": "abstractive"
    }
    
    try:
        resp = requests.put(f"{BASE_URL}/meetings/{meeting_id}", json=summary_data)
        if resp.status_code != 200:
            print(f"❌ 保存摘要失败: {resp.status_code}")
            print(f"   响应: {resp.text}")
            return False
        
        print(f"✅ 摘要已保存到数据库")
    except Exception as e:
        print(f"❌ 保存摘要出错: {e}")
        return False
    
    # 步骤3: 获取摘要（第一次）
    print("\n📝 步骤3: 第一次获取摘要...")
    try:
        resp = requests.get(f"{BASE_URL}/meetings/{meeting_id}/summary")
        if resp.status_code != 200:
            print(f"❌ 获取摘要失败: {resp.status_code}")
            print(f"   响应: {resp.text}")
            return False
        
        summary1 = resp.json()
        print(f"✅ 获取摘要成功")
        print(f"   摘要: {summary1.get('summary_text', summary1.get('summary', ''))[:60]}...")
        print(f"   关键议题: {summary1.get('key_topics', [])}")
    except Exception as e:
        print(f"❌ 获取摘要出错: {e}")
        return False
    
    # 步骤4: 再次获取摘要（模拟页面刷新）
    print("\n📝 步骤4: 模拟页面刷新，再次获取摘要...")
    try:
        resp = requests.get(f"{BASE_URL}/meetings/{meeting_id}/summary")
        if resp.status_code != 200:
            print(f"❌ 获取摘要失败: {resp.status_code}")
            print(f"   响应: {resp.text}")
            return False
        
        summary2 = resp.json()
        print(f"✅ 获取摘要成功")
        print(f"   摘要: {summary2.get('summary_text', summary2.get('summary', ''))[:60]}...")
        print(f"   关键议题: {summary2.get('key_topics', [])}")
    except Exception as e:
        print(f"❌ 获取摘要出错: {e}")
        return False
    
    # 步骤5: 验证两次获取的摘要是否一致
    print("\n📝 步骤5: 验证摘要持久化...")
    summary1_text = summary1.get('summary_text', summary1.get('summary', ''))
    summary2_text = summary2.get('summary_text', summary2.get('summary', ''))
    
    if summary1_text == summary2_text and summary1_text:
        print(f"✅ 摘要持久化成功！")
        print(f"   两次获取的摘要内容一致")
        return True
    else:
        print(f"❌ 摘要持久化失败！")
        print(f"   第一次: {summary1_text[:50]}...")
        print(f"   第二次: {summary2_text[:50]}...")
        return False

if __name__ == "__main__":
    try:
        success = test_summary_persistence()
        if success:
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！摘要持久化功能正常")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 测试失败")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
