from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"charset": "utf8mb4", "use_unicode": True},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pymysql_conn():
    """获取原生pymysql连接（用于避免SQLAlchemy ORM复杂性问题）"""
    import pymysql
    # 从 DATABASE_URL 解析连接参数
    url = settings.DATABASE_URL
    # 格式: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
    info = url.replace("mysql+pymysql://", "").split("@")
    user_pass = info[0].split(":")
    host_db = info[1].split("/")
    host_port = host_db[0].split(":")
    db_name = host_db[1].split("?")[0]
    return pymysql.connect(
        host=host_port[0],
        port=int(host_port[1]) if len(host_port) > 1 else 3306,
        user=user_pass[0],
        password=user_pass[1],
        database=db_name,
        charset="utf8mb4",
        autocommit=False
    )


def init_db():
    """初始化数据库表"""
    # 所有模型注册在 app.models.models 的 Base 上，必须用同一个 Base 建表，
    # 否则 create_all 作用在空 metadata 上，不会创建任何表。
    from app.models.models import Base as ModelsBase  # noqa: F401
    ModelsBase.metadata.create_all(bind=engine)
    print("[OK] 数据库表初始化完成")


if __name__ == "__main__":
    init_db()
