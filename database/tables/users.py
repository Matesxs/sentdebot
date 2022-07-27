import disnake
from disnake.ext import commands
from typing import Union, Optional
from sqlalchemy import Column, DateTime, String, PrimaryKeyConstraint, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from util import general_util
from database import database

class User(database.base):
  __tablename__ = "users"

  id = Column(String, primary_key=True, unique=True, index=True)
  created_at = Column(DateTime, nullable=False)

  is_bot = Column(Boolean, nullable=False)
  is_system = Column(Boolean, nullable=False)

  members = relationship("Member", back_populates="user", uselist=True)
  help_requests = relationship("HelpThread")

  @classmethod
  def from_user(cls, user: Union[disnake.Member, disnake.User]):
    return cls(id=str(user.id), created_at=user.created_at, is_bot=user.bot, is_system=user.system)

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
  __table_args__ = (PrimaryKeyConstraint("id", "guild_id", name="guild_member_id"),)

  id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), index=True, nullable=False)

  nick = Column(String, nullable=False)
  icon_url = Column(String)
  premium = Column(Boolean, nullable=False)

  user = relationship("User", back_populates="members", uselist=False)
  guild = relationship("Guild", back_populates="members", uselist=False)

  joined_at = Column(DateTime, nullable=False, index=True)
  left_at = Column(DateTime, index=True)

  audit_logs = relationship("AuditLog", primaryjoin="and_(foreign(Member.id) == AuditLog.user_id, foreign(Member.guild_id) == AuditLog.guild_id)", viewonly=True, uselist=True)
  messages = relationship("Message", primaryjoin="and_(foreign(Member.id) == Message.author_id, foreign(Member.guild_id) == Message.guild_id)", viewonly=True, uselist=True)

  @classmethod
  def from_member(cls, member: disnake.Member):
    return cls(id=str(member.id), guild_id=str(member.guild.id), joined_at=member.joined_at, nick=member.display_name, icon_url=member.display_avatar.url, premium=member.premium_since is not None)

  async def to_object(self, bot: commands.Bot) -> Optional[disnake.Member]:
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    member = await general_util.get_or_fetch_member(guild, int(self.id))
    return member