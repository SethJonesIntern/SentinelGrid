from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """
    Maps to the existing `public.users` table owned by the team (do not change
    the columns here without coordinating the table). `id` auto-increments via
    the `users_id_seq` sequence; `role` defaults to 'analyst' server-side.
    """

    __tablename__ = "users"

    # Integer (not BigInteger) so the autoincrement PK also works in the SQLite
    # test DB; Postgres stores it as bigint either way.
    id = Column(Integer, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False, index=True)
    email = Column(Text, unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=True, server_default="analyst")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
