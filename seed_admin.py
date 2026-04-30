#!/usr/bin/env python3
"""
Run once to create the first admin user.
Usage: python seed_admin.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models import church  # noqa
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)

db = SessionLocal()

if db.query(User).filter(User.username == "admin").first():
    print("Admin user already exists.")
else:
    admin = User(
        username="admin",
        email="admin@ifgftaipei.org",
        hashed_password=get_password_hash("changeme123"),
        full_name="Administrator",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created.")
    print("   Username : admin")
    print("   Password : changeme123")
    print("   ⚠️  Change the password immediately after first login!")

db.close()
