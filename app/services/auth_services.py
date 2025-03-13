from passlib.context import CryptContext
from datetime import datetime
from app.services.database import admins_collection
from app.models.admin import AdminSignup, AdminLogin
from datetime import datetime, timedelta


# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def admin_signup(admin: AdminSignup):
    """Registers an admin in MongoDB Atlas"""
    existing_admin = admins_collection.find_one({"email": admin.email})
    if existing_admin:
        return {"error": "Admin already exists!"}

    hashed_password = pwd_context.hash(admin.password)
    admin_data = {
        "email": admin.email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    }
    admins_collection.insert_one(admin_data)  # Save to MongoDB
    return {"message": "Admin registered successfully!"}

async def admin_login(email, password):
    """Authenticates an admin and returns a JWT token"""
    admin = admins_collection.find_one({"email": email})
    if not admin or not pwd_context.verify(password, admin["password"]):
        return None  # Invalid login

    # Generate JWT Token
    from jose import jwt
    from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM
    token_data = {"sub": email, "exp": datetime.utcnow() + timedelta(minutes=60)}
    access_token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer"}
