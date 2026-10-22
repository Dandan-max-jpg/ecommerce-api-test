# seed_admin.py - 生成一个管理员账号，方便测试管理员接口
# 运行：python seed_admin.py   （会在 ecommerce.db 中写入 admin / admin123，角色 admin）
import sqlite3
from app import pw_hash, init_db, DB_PATH

init_db()
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute(
    "INSERT OR REPLACE INTO users (id, username, password, role) "
    "VALUES ((SELECT id FROM users WHERE username='admin'), 'admin', ?, 'admin')",
    (pw_hash("admin123"),),
)
conn.commit()
conn.close()
print("已生成/重置管理员账号：admin / admin123 （角色 admin）")
