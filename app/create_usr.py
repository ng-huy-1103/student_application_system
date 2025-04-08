from main import app
from database.db import db
from models.user import User
import bcrypt

with app.app_context():
    # Tạo mật khẩu băm từ mật khẩu gốc "123456"
    password = '123456'
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    # Tạo người dùng mẫu
    new_user = User(
        name="Giáo sư Nguyễn Văn A",
        username="giaosu01",
        password_hash=password_hash,
        role="admin"
    )
    db.session.add(new_user)
    db.session.commit()
    print("User được tạo thành công với id:", new_user.id)
