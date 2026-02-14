"""
数据库初始化脚本
创建数据库表和默认用户
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database import SessionLocal, init_db
from models import User, UserRole
from src.auth.password import hash_password


def create_default_users():
    """创建默认用户"""
    db = SessionLocal()
    
    try:
        # 检查管理员是否已存在
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("✓ 管理员账户已存在")
        else:
            # 创建管理员
            admin_user = User(
                username="admin",
                email="admin@example.com",
                full_name="系统管理员",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            print("✓ 已创建管理员账户")
            print("  用户名: admin")
            print("  密码: admin123")
        
        # 检查测试用户是否已存在
        user = db.query(User).filter(User.username == "testuser").first()
        if user:
            print("✓ 测试用户已存在")
        else:
            # 创建测试用户
            test_user = User(
                username="testuser",
                email="testuser@example.com",
                full_name="测试用户",
                hashed_password=hash_password("testpass123"),
                role=UserRole.USER,
                is_active=True
            )
            db.add(test_user)
            print("✓ 已创建测试用户")
            print("  用户名: testuser")
            print("  密码: testpass123")
        
        db.commit()
        print("\n✅ 默认用户创建成功！")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建用户失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """主函数"""
    print("=" * 60)
    print("🗄️  数据库初始化")
    print("=" * 60)
    print()
    
    # 初始化数据库表
    print("[1/2] 初始化数据库表...")
    try:
        init_db()
        print()
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 创建默认用户
    print("[2/2] 创建默认用户...")
    print()
    create_default_users()
    
    print()
    print("=" * 60)
    print("✅ 数据库初始化完成！")
    print("=" * 60)
    print()
    print("📝 现在你可以使用以下账户登录：")
    print()
    print("账户1（管理员）：")
    print("  用户名: admin")
    print("  密码: admin123")
    print()
    print("账户2（普通用户）:")
    print("  用户名: testuser")
    print("  密码: testpass123")
    print()
    print("💡 提示：")
    print("  • 你也可以通过注册页面创建新账户")
    print("  • 前端地址: http://localhost:3000")
    print("  • 后端API: http://localhost:8000/api")
    print("  • API文档: http://localhost:8000/docs")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
