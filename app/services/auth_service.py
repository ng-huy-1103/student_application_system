import bcrypt
from models.user import User

def login_user(username, password):
    user = User.query.filter_by(username=username).first()
    if not user:
        return None, "Người dùng không tồn tại"
    
    # So sánh mật khẩu nhập vào với mật khẩu đã băm
    if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return {"id": user.id}, None
    else:
        return None, "Sai mật khẩu"
