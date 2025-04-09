from flask import Flask
from database.db import db
from routes.auth_routes import auth_bp
from routes.upload_routes import upload_bp
from routes.navigate_route import navigate_bp
# import het cac tables trong database
from models.document import Document
from models.application import Application
from models.user import User
from models.studentinfo import StudentInfo
from models.summary import Summary
from models.evaluation import Evaluation


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Tienmanh2001@localhost:5432/student_analysis'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Khởi tạo SQLAlchemy với app
db.init_app(app)

# Đăng ký Blueprint cho API Authentication
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(navigate_bp, url_prefix='/api')

# Tạo bảng nếu chưa có
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0')
