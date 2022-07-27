from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime

from database import database

class HelpThread(database.base):
  __tablename__ = "help_threads"

  thread_id = Column(String, ForeignKey("text_threads.id", ondelete="CASCADE"), primary_key=True, unique=True, index=True)
  owner_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), index=True)
  tags = Column(String, nullable=True)
  last_activity_time = Column(DateTime, index=True, default=datetime.datetime.utcnow)

  thread = relationship("TextThread", uselist=False)
