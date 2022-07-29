from sqlalchemy import Column, DateTime, String, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
import enum
import datetime

from database import database, BigIntegerType

class AuditLogItemType(enum.Enum):
  MESSAGE_DELETED = 0
  MESSAGE_EDITED = 1
  MEMBER_UPDATED = 2

class AuditLog(database.base):
  __tablename__ = "audit_log"

  id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True, unique=True)
  timestamp = Column(DateTime, index=True, nullable=False, default=datetime.datetime.utcnow)

  user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=True)
  member_iid = Column(BigIntegerType, ForeignKey("members.member_iid", ondelete="CASCADE"), index=True, nullable=True)

  member = relationship("Member", back_populates="audit_logs", uselist=False)
  user = relationship("User", back_populates="audit_logs", uselist=False)

  log_type = Column(Enum(AuditLogItemType), index=True)
  data = Column(JSON, nullable=True)
