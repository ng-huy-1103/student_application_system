from flask import Blueprint, request, jsonify, session
import bcrypt
from models.user import User

auth_bp = Blueprint('auth', __name__)

def login_user(username, password):
    user = User.query.filter_by(username=username).first()
    if not user:
        return None, "User not found"
    
    # So sánh mật khẩu nhập vào với mật khẩu đã băm
    if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return {"id": user.id}, None
    else:
        return None, "Wrong password"

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Not enough fields"}), 400
        
    user, error = login_user(username, password)
    if error:
        return jsonify({"error": error}), 401
    
    
    session['user_id'] = user["id"]
    print({"id": user["id"]})
    return jsonify({"id": user["id"]}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    # Xóa thông tin phiên của người dùng
    session.pop('user_id', None)
    return jsonify({"message": "Logout successfully"}), 200

@auth_bp.route('/user', methods=['GET'])
def current_user():
    # Lấy id người dùng từ session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not login yet"}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_info = {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role.value,
        "created_at": user.created_at.isoformat()
    }
    return jsonify(user_info), 200

