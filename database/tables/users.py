import disnake
from disnake.ext import commands
from typing import Union, Optional
from sqlalchemy import Column, DateTime, String, UniqueConstraint, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from util import general_util
from database import database, BigIntegerType

class User(database.base):
  __tablename__ = "users"

  id = Column(String, primary_key=True, unique=True, index=True)
  name = Column(String, index=True, nullable=True)

  created_at = Column(DateTime, nullable=False)

  is_bot = Column(Boolean, nullable=False)
  is_system = Column(Boolean, nullable=False)

  members = relationship("Member", back_populates="user", uselist=True)
  help_requests = relationship("HelpThread", uselist=True)
  weather_settings = relationship("WeatherSettings", back_populates="user", uselist=False)
  audit_logs = relationship("AuditLog", back_populates="user", uselist=True)
  messages = relationship("Message", back_populates="user", uselist=True)

  @classmethod
  def from_user(cls, user: Union[disnake.Member, disnake.User]):
    return cls(id=str(user.id), created_at=user.created_at, is_bot=user.bot, is_system=user.system, name=user.name)

  async def to_object(self, bot: commands.Bot) -> Optional[disnake.User]:
    user = bot.get_user(int(self.id))
    if user is None:
      try:
        user = await bot.fetch_user(int(self.id))
      except disnake.NotFound:
        return None
    return user

class Member(database.base):
  __tablename__ = "members"
  __table_args__ = (UniqueConstraint("id", "guild_id", name="guild_member_id"),)

  id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False)
  member_iid = Column(BigIntegerType, index=True, autoincrement=True, unique=True, primary_key=True)

  nick = Column(String, nullable=False)
  icon_url = Column(String)
  premium = Column(Boolean, nullable=False)

  user = relationship("User", back_populates="members", uselist=False)
  guild = relationship("Guild", back_populates="members", uselist=False)

  joined_at = Column(DateTime, nullable=False, index=True)
  left_at = Column(DateTime, index=True)

  audit_logs = relationship("AuditLog", back_populates="member", uselist=True)
  messages = relationship("Message", back_populates="member", uselist=True)

  collect_data = Column(Boolean, default=True, nullable=False, index=True)

  @classmethod
  def from_member(cls, member: disnake.Member):
    return cls(id=str(member.id), guild_id=str(member.guild.id), joined_at=member.joined_at, nick=member.display_name, icon_url=member.display_avatar.url, premium=member.premium_since is not None)

  async def to_object(self, bot: commands.Bot) -> Optional[disnake.Member]:
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    member = await general_util.get_or_fetch_member(guild, int(self.id))
    return member