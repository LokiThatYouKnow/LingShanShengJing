"""
创建默认管理员账号
"""
import sys
sys.path.insert(0, '.')

from app.db.database import SessionLocal
from app.models.models import User
from app.utils.auth import get_password_hash

def create_default_admin():
    db = SessionLocal()
    try:
        # 检查是否已存在管理员
        existing = db.query(User).filter(User.username == 'admin').first()
        if existing:
            print(f"管理员账号已存在: {existing.username}")
            return

        # 创建默认管理员
        admin = User(
            username='admin',
            email='admin@scenic-guide.com',
            hashed_password=get_password_hash('admin123'),
            role='super_admin',
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("✅ 默认管理员账号创建成功!")
        print("   用户名: admin")
        print("   密码: admin123")
    except Exception as e:
        db.rollback()
        print(f"❌ 创建失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_default_admin()
