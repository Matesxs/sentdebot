import disnake
from disnake.ext import commands
from typing import Optional
from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from database import database, BigIntegerType
from database import users_repo
from util import general_util

class MessageAttachment(database.base):
  __tablename__ = "message_attachments"

  id = Column(String, primary_key=True, unique=True)

  message_id = Column(String, ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False)
  url = Column(String, index=True, nullable=False)

  message = relationship("Message", back_populates="attachments", uselist=False)

class Message(database.base):
  __tablename__ = "messages"

  id = Column(String, primary_key=True, unique=True, index=True)
  author_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=True, index=True)
  member_iid = Column(BigIntegerType, ForeignKey("members.member_iid", ondelete="CASCADE"), index=True, nullable=True)

  member = relationship("Member", back_populates="messages", uselist=False)
  user = relationship("User", back_populates="messages", uselist=False)

  created_at = Column(DateTime, index=True, nullable=False)
  edited_at = Column(DateTime)

  channel_id = Column(String, ForeignKey("text_channels.id", ondelete="CASCADE"), index=True, nullable=False)
  thread_id = Column(String, ForeignKey("text_threads.id", ondelete="CASCADE"), index=True, nullable=True)
  content = Column(String)

  attachments = relationship("MessageAttachment", back_populates="message", uselist=True)
  channel = relationship("TextChannel", back_populates="messages", uselist=False)

  use_for_metrics = Column(Boolean, nullable=False, default=False)

  @classmethod
  def from_message(cls, message: disnake.Message):
    channel_is_thread = isinstance(message.channel, disnake.Thread)
    channel_id = message.channel.parent.id if channel_is_thread else message.channel.id
    thread_id = message.channel.id if channel_is_thread else None
    guild_id = message.guild.id if message.guild is not None else None
    user_id = message.author.id
    member_iid = None
    if guild_id is not None:
      member_iid = users_repo.member_identifier_to_member_iid(user_id, guild_id)

    return cls(id=str(message.id),
               author_id=str(user_id),
               guild_id=str(guild_id) if guild_id is not None else None,
               member_iid=member_iid,
               created_at=message.created_at,
               channel_id=str(channel_id),
               thread_id=str(thread_id) if thread_id is not None else None,
               content=message.content)

  async def to_object(self, bot: commands.Bot) -> Optional[disnake.Message]:
    message = await general_util.get_or_fetch_message(bot, None, int(self.id))
    if message is None:
      channel = await self.channel.to_object(bot)
      if channel is None: return None

      message = await general_util.get_or_fetch_message(bot, channel, int(self.id))

    return message
