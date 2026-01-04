import requests

base_url = "http://127.0.0.1:8000"

# 회원가입
signup_data = {
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "fullname": "John Doe"
}

response = requests.post(f"{base_url}/auth/signup", json=signup_data)
print(response.json())


# 로그인
login_data = {
    "username": "john_doe",
    "password": "securepass123"
}

auth_response = requests.post(f"{base_url}/auth/login", json=login_data)
token = auth_response.json()["access_token"]
token = token.strip()
headers = {"Authorization": f"Bearer {token}"}
print(auth_response.json())
# print("토큰: " + token)


# 책 등록
book_data = {
    "title": "Python Programming",
    "author": "John Smith",
    "isbn": "978-0123456789",
    "category": "Programming",
    "total_copies": 5
}

response = requests.post(f"{base_url}/books", json=book_data, headers=headers)
print(response.json())

search_response = requests.get(f"{base_url}/books?category=Programming&available=true")
print(search_response.json())

# 책 대출
borrow_data = {
    "book_id": 1,
    "user_id": 1
}

response = requests.post(f"{base_url}/loans", json=borrow_data, headers=headers)
print(response.json())

# 해당 유저 대출 책 조회
loans_response = requests.get(f"{base_url}/users/me/loans", headers=headers)
print(loans_response.json())

# 책 반납
return_data = {
    "book_id": 1
}

response = requests.post(f"{base_url}/book_return", json=return_data, headers=headers)
print(response.json())