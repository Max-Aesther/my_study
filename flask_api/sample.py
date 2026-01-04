from sqlalchemy import text
from flask import Flask, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)

app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "secret_key"

db = SQLAlchemy(app)
jwt = JWTManager(app)

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String)
    email = db.Column(db.String)
    password = db.Column(db.String)
    fullname = db.Column(db.String)
    
class Book(db.Model):
    book_id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String)
    author = db.Column(db.String)
    isbn = db.Column(db.String)
    category = db.Column(db.String)
    total_copies = db.Column(db.Integer)
    available = db.Column(db.Boolean, default=True, server_default=text("1"))

class Loans(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.user_id))
    book_id = db.Column(db.Integer, db.ForeignKey(Book.book_id))
# 서버 확인용
@app.route('/')
def home():
    return "Hello Flask!"

# 회원가입
@app.route("/auth/signup", methods=["POST"])
def signup():
    data = request.json
    py_user = User.query.filter_by(email = data["email"]).first()
    
    if(py_user):
        return jsonify({"message": "중복된 이메일입니다."})
    
    hashed_pw = generate_password_hash(data["password"])
    user = User(username=data["username"], email=data["email"],
                password=hashed_pw, fullname=data["fullname"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"data": data, "message": "회원가입 성공"})
    
# 로그인
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"]).first()
    if(check_password_hash(user.password, data["password"])):
        token = create_access_token(identity=user.email, additional_claims={"role": "admin"})
        return jsonify({"access_token": token, "message": "로그인 성공"})
    else:
        return jsonify({"message": "로그인 실패"})
    
# 책 등록
@app.route("/books", methods=["POST"])
@jwt_required()
def add_book():    
    payload = get_jwt()
    role = payload["role"]
    if(role != "admin"):
        return jsonify({"message": "관리자 권한 필요"})
    
    
    data = request.json
    book = Book(title=data["title"], author=data["author"], isbn=data["isbn"],
                category=data["category"], total_copies=data["total_copies"])
    db.session.add(book)
    db.session.commit()
    return jsonify({"message": "책 등록 성공", "data": data})
    
# 책 조회
@app.route("/books", methods=["GET"])
def book():
    category = request.args.get("category")
    available = request.args.get("available")
    available = available.lower() == "true"
    print(category)
    print(available)
    book = Book.query.filter_by(category = category, available = available).first()
    
    if not book:
        return jsonify({"message": "조건에 맞는 책 없음"})
    
    book_sample = {
        "book_id": book.book_id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "category": book.category,
        "total_copies": book.total_copies,
        "available": book.available
    }
    
    return jsonify({"message": "책 조회 성공", "book": book_sample})
    
# 책 대출
@app.route("/loans", methods=["POST"])
@jwt_required()
def book_loan():
    data = request.json
    print(data["user_id"])
    print(data["book_id"])
    book = Book.query.filter_by(book_id = data["book_id"]).first()
    if(book.available == False):
        return jsonify({"message": "이미 대출된 책임"})
    
    loans = Loans(user_id=data["user_id"], book_id=data["book_id"])
    db.session.add(loans)
    db.session.commit()
    book.available = False
    db.session.commit()
    
    update_book = Book.query.filter_by(book_id = data["book_id"]).first()
    
    book_available = update_book.available
        
    update_loans = {
        "id": loans.id,
        "user_id": loans.user_id,
        "book_id": loans.book_id
    }
    
    return jsonify({"message": "책 대출 성공", "book_avilable": book_available, "loans": update_loans})
    
# 해당 유저가 빌린 책 조회
@app.route("/users/me/loans", methods=["GET"])
@jwt_required()
def user_book_loans():
    payload = get_jwt()
    sub = payload["sub"]
    user = User.query.filter_by(email = sub).first()
    loans = Loans.query.filter_by(user_id=user.user_id).first()
    
    if not loans:
        return jsonify({"message": "해당 유저가 빌린 책은 없음"})
    book = Book.query.filter_by(book_id=loans.book_id).first()
    
    sample_user = {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "fullname": user.fullname
    }
    
    sample_book = {
        "book_id": book.book_id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "category": book.category,
        "total_copies": book.total_copies,
        "available": book.available
    }
    
    return jsonify({"message": "대출 책 조회 성공", "user": sample_user, "book": sample_book})


# 책 반납
@app.route("/book_return", methods=["POST"])
@jwt_required()
def book_return():
    data = request.json
    payload = get_jwt()
    email = payload["sub"]
    user = User.query.filter_by(email = email).first()
    loans = Loans.query.filter_by(user_id = user.user_id, book_id = data["book_id"]).first()
    
    if loans is None:
        return jsonify({"message": "해당 유저가 빌린 책이 아님"})
    
    book = Book.query.filter_by(book_id = data["book_id"]).first()
    book.available = True
    db.session.delete(loans)
    db.session.commit()
    
    return jsonify({"message": "책 반납 성공", "book": book.title, "user": user.username})

# JWT 인증 실패 시 로그인 필요 메시지
@jwt.unauthorized_loader
def unauthorized_response():
    return jsonify({"message": "로그인 필요"})

# 실행
if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
    app.run(debug=True, port=8000)
    