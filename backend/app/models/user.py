# app/models/user.py

from werkzeug.security import generate_password_hash, check_password_hash
from app.database import get_db
from bson import ObjectId

class User:
    def __init__(self, email, password, user_id=None):
        self.id = user_id
        self.email = email
        self.password_hash = generate_password_hash(password)

    async def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    async def get_user_by_email(email):
        db = await get_db()
        user_data = await db.users.find_one({'email': email})
        if user_data:
            user_id = str(user_data['_id'])
            user = User(
                email=user_data['email'],
                password='',  # Password is not needed here
                user_id=user_id
            )
            user.password_hash = user_data['password_hash']
            return user
        return None

    @staticmethod
    async def create_user(email, password):
        user = User(email, password)
        db = await get_db()
        result = await db.users.insert_one({
            'email': user.email,
            'password_hash': user.password_hash
        })
        user.id = str(result.inserted_id)
        return user.id

    @staticmethod
    async def get_email_by_user_id(user_id):
        db = await get_db()
        user = await db.users.find_one({'_id': ObjectId(user_id)})
        return user['email'] if user else None