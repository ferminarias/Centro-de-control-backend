"""Seed script: creates a test account with auto_crear_campos=True."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.account import Account


def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Account).filter(Account.nombre == "UEES").first()
        if existing:
            print(f"Account 'UEES' already exists: api_key={existing.api_key}")
            return

        account = Account(
            nombre="UEES",
            api_key="cc_test_uees_key_12345",
            auto_crear_campos=True,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        print(f"Account created: id={account.id}, api_key={account.api_key}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
