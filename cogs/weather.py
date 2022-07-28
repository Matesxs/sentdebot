import aiohttp
import datetime
import urllib.parse
import json
from typing import Optional, List
import disnake
from disnake.ext import commands

from config import cooldowns
from util import general_util
from features.base_cog import Base_Cog
from features.paginator import EmbedView
from database import weather_settings_repo
from static_data.strings import Strings

DAY_PHASES = {
  "Morning": 2,
  "Day": 4,
  "Evening": 6,
  "Night": 7,
}


def _get_current_day_phase() -> str:
  now = datetime.datetime.now()
  if now.hour <= 6:
    return "Morning"
  if now.hour <= 12:
    return "Day"
  if now.hour <= 18:
    return "Evening"
  return "Night"


def _get_useful_data(all_data: dict) -> List[dict]:
  weather = []
  nearest_place = all_data["nearest_area"][0]["areaName"][0]["value"]
  for i in range(3):
    day = all_data["weather"][i]
    day_dict = {
      "date": day["date"],
      "nearest_place": nearest_place,
    }
    day = day["hourly"]
    for day_phase, hour in DAY_PHASES.items():
      day_dict.update(
        {
          day_phase: {
            "state": day[hour]["weatherDesc"][0]["value"],
            "temp": day[hour]["tempC"],
            "feels_like": day[hour]["FeelsLikeC"],
            "wind_speed": day[hour]["windspeedKmph"],
            "rain_chance": day[hour]["chanceofrain"],
          }
        }
      )

    weather.append(day_dict)
  return weather


async def _create_embeds(inter: disnake.CommandInteraction, place: str) -> Optional[List[disnake.Embed]]:
  """create embeds for scrollable embed"""
  safe_name: str = urllib.parse.quote_plus(place)
  url = f"https://wttr.in/{safe_name}?format=j1&lang=en"
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
        data = await resp.text()
  except aiohttp.ClientResponseError:
    return None

  try:
    resp_json = json.loads(data)
  except json.JSONDecodeError:
    return None

  current_day_phase: str = _get_current_day_phase()

  # create day embeds
  days = _get_useful_data(resp_json)
  embeds = []
  for i, day in enumerate(days):
    if i == 0:
      title = "Today"
    elif i == 1:
      title = "Tomorrow"
    else:
      title = day["date"]

    if i == 0:
      # Show current weather in title
      now = day[current_day_phase]
      title = f"{title}: {now['state']}, {now['temp']} ˚C"
    else:
      # Show maximum and minimum in title
      temperatures = [int(info["temp"]) for phase, info in day.items() if type(info) is dict]
      min_t, max_t = min(temperatures), max(temperatures)
      title = f"{title}: {min_t}\N{EN DASH}{max_t} °C"

    embed = disnake.Embed(title=title, description=f"Weather forecast for **{place}**, {day['date']}", color=disnake.Color.dark_blue())
    general_util.add_author_footer(embed, inter.author)

    skip_day_phase: bool = True
    for day_phase, weather_info in day.items():
      # skip 'date' and 'nearest_place' strings
      if type(weather_info) != dict:
        continue

      # skip today's day phase if it has already ended
      if day_phase == current_day_phase:
        skip_day_phase = False
      if i == 0 and skip_day_phase:
        continue

      embed.add_field(name=f"{day_phase}: {weather_info['state']}",
                      value=f"Temperature: **{weather_info['temp']} ˚C** (feels like **{weather_info['feels_like']} ˚C**)\n"
                            f"Wind speed: **{weather_info['wind_speed']} km/h**\n"
                            f"Chance of rain: **{weather_info['rain_chance']} %**", inline=False)

    embeds.append(embed)

  return embeds


def _place_is_valid(name: str) -> bool:
  for char in ("&", "#", "?"):
    if char in name:
      return False
  return True


class Weather(Base_Cog):
  def __init__(self, bot: commands.Bot):
    super(Weather, self).__init__(bot, __file__)

  @commands.slash_command()
  async def weather(self, inter: disnake.CommandInteraction):
    pass

  @weather.sub_command(name="set_place", description=Strings.weather_set_place_brief)
  @cooldowns.default_cooldown
  async def set_weather_place(self, inter: disnake.CommandInteraction, *, place: str=commands.Param(description="Place where to request weather for")):
    if not _place_is_valid(place):
      return general_util.generate_error_message(inter, Strings.weather_set_place_invalid_place)

    weather_settings_repo.set_weather_settings(inter.author.id, place)
    await general_util.generate_success_message(inter, Strings.weather_set_place_set(place=place))

  @weather.sub_command(name="unset_place", description=Strings.weather_unset_place_brief)
  @cooldowns.default_cooldown
  async def unset_weather_place(self, inter: disnake.CommandInteraction):
    if not weather_settings_repo.remove_weather_settings(inter.author.id):
      return await general_util.generate_error_message(inter, Strings.weather_unset_place_not_place_to_remove)
    await general_util.generate_success_message(inter, Strings.weather_unset_place_removed)

  @weather.sub_command(name="get", description=Strings.weather_request_weather_breif)
  @cooldowns.default_cooldown
  async def weather_request(self, inter: disnake.CommandInteraction, place: Optional[str]=commands.Param(default=None, description="Place where to request weather for")):
    await inter.response.defer(with_message=True)

    if place is None:
      # try to get user preference
      place_it = weather_settings_repo.get_weather_settings(inter.author.id)
      if place_it is not None:
        place = place_it.place

    if place is None:
      return await general_util.generate_error_message(inter, Strings.weather_request_weather_place_not_set)

    embeds = await _create_embeds(inter, place)

    if embeds is None:
      return await general_util.generate_error_message(inter, Strings.weather_request_weather_error)
    await EmbedView(inter.author, embeds).run(inter)

def setup(bot) -> None:
  bot.add_cog(Weather(bot))
