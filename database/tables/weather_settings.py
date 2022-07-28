from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from database import database

class WeatherSettings(database.base):
  __tablename__ = "weather_settings"

  user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, unique=True, index=True)
  place = Column(String, nullable=False)

  user = relationship("User", back_populates="weather_settings", uselist=False)
