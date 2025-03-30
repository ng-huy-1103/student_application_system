from flask import Flask
from db import db
from routes.auth_routes import auth_bp
import bcrypt
from models.user import User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Tienmanh2001@localhost:5432/student_analysis'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Khởi tạo SQLAlchemy với app
db.init_app(app)

# Đăng ký Blueprint cho API Authentication
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Tạo bảng nếu chưa có
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
