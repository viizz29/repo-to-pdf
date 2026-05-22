from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.auth.model import User


# SEED_USERS = [
#     {
#         "email": "admin@example.com",
#         "name": "Admin User",
#         "password": "admin123",
#     },
#     {
#         "email": "jane@example.com",
#         "name": "Jane Doe",
#         "password": "jane123",
#     },
#     {
#         "email": "john@example.com",
#         "name": "John Doe",
#         "password": "john123",
#     },
# ]


SEED_USERS = []
for i in range(1,6):
    SEED_USERS.append({
        "email": f"user{i}@example.com",
        "name": f"User {i}",
        "password": "password123",
    })


def seed_users() -> None:
    db = SessionLocal()
    try:
        for entry in SEED_USERS:
            user = db.query(User).filter(User.email == entry["email"]).first()
            if user:
                user.name = entry["name"]
                user.password = hash_password(entry["password"])
                continue

            db.add(
                User(
                    email=entry["email"],
                    name=entry["name"],
                    password=hash_password(entry["password"]),
                )
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
    print(f"Seeded {len(SEED_USERS)} users.")
