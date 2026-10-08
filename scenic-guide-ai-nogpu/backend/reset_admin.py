"""
重置管理员密码
"""
import sys
sys.path.insert(0, '.')

from app.db.database import SessionLocal
from app.models.models import User
from app.utils.auth import get_password_hash

def reset_admin_password():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == 'admin').first()
        if not admin:
            print("[X] 管理员账号不存在")
            return

        # 重置为默认密码
        admin.hashed_password = get_password_hash('admin123')
        db.commit()
        print("[OK] 管理员密码已重置!")
        print("   Username: admin")
        print("   Password: admin123")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 重置失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()
