from typing import Optional

from database import session
from database.tables.weather_settings import WeatherSettings

def get_weather_settings(user_id: int) -> Optional[WeatherSettings]:
  return session.query(WeatherSettings).filter(WeatherSettings.user_id == str(user_id)).one_or_none()

def set_weather_settings(user_id: int, place: str) -> WeatherSettings:
  weather_it = get_weather_settings(user_id)
  if weather_it is None:
    weather_it = WeatherSettings(user_id=str(user_id), place=place)
    session.add(weather_it)
  else:
    weather_it.place = place

  session.commit()
  return weather_it

def remove_weather_settings(user_id: int) -> bool:
  deleted = session.query(WeatherSettings).filter(WeatherSettings.user_id == str(user_id)).delete() == 1
  session.commit()
  return deleted
