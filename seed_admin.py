#!/usr/bin/env python3
"""
Run once to create the first super_admin user.
Usage: python seed_admin.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, engine, Base
from app.models.user import User, UserRole, Role
from app.models.church import Member
import app.models.user   # noqa — register all models
import app.models.church  # noqa

from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)

db = SessionLocal()

member = db.query(Member).filter(Member.full_name == "Yohanes Satria Nugroho").first()
if not member:
    print("❌ Member 'Yohanes Satria Nugroho' not found.")
    db.close()
    sys.exit(1)

if db.query(User).filter(User.member_id == member.id).first():
    print("User for this member already exists.")
    db.close()
    sys.exit(0)

username = "yohanes"
user = User(
    member_id=member.id,
    username=username,
    password_hash=get_password_hash("111111"),
    is_active=True,
)
db.add(user)
db.flush()

role = db.query(Role).filter(Role.name == "super_admin").first()
if not role:
    print("❌ Role 'super_admin' not found. Run the schema SQL first (INSERT INTO roles ...).")
    db.rollback()
    db.close()
    sys.exit(1)

db.add(UserRole(user_id=user.id, role_id=role.id))
db.commit()

print("✅ User created.")
print(f"   Member   : {member.full_name}")
print(f"   Username : {username}")
print("   Role     : super_admin")

db.close()
