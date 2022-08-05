import datetime
import disnake
from typing import List, Union, Optional
import dataclasses

from features.base_bot import BaseAutoshardedBot
from database import messages_repo

@dataclasses.dataclass
class Attachment:
  filename: str
  url: str

class BeforeMessageContext:
  def __init__(self, id, author, created_at, edited_at, channel, guild, content, attachments):
    self.id = id
    self.author: Union[disnake.Member, disnake.User] = author
    self.created_at: datetime.datetime = created_at
    self.edited_at: Optional[datetime.datetime] = edited_at
    self.channel: Optional[Union[disnake.VoiceChannel, disnake.StageChannel, disnake.TextChannel, disnake.CategoryChannel, disnake.ForumChannel, disnake.Thread]] = channel
    self.guild: Optional[disnake.Guild] = guild
    self.content: Optional[str] = content
    self.attachments: List[Attachment] = attachments

  @classmethod
  def from_message(cls, message: disnake.Message):
    author = message.author
    content = message.content
    created_at = message.created_at
    edited_at = message.edited_at
    channel = message.channel if not isinstance(message.channel, disnake.DMChannel) else None
    guild = message.guild
    attachments = [Attachment(att.filename, att.url) for att in message.attachments]
    return cls(message.id, author, created_at, edited_at, channel, guild, content, attachments)

  @classmethod
  async def from_database(cls, message_item: messages_repo.Message, bot: BaseAutoshardedBot):
    if message_item.member_iid is not None:
      author = await message_item.member.to_object(bot)
    else:
      author = await message_item.user.to_object(bot)
    content = message_item.content
    created_at = message_item.created_at
    edited_at = message_item.edited_at
    if not message_item.is_DM:
      if message_item.thread_id is not None:
        channel = await message_item.thread.to_object(bot)
      else:
        channel = await message_item.channel.to_object(bot)
    else:
      channel = None
    guild = await message_item.guild.to_object(bot) if message_item.guild_id is not None else None
    attachments = [Attachment(att["filename"], att["url"]) for att in message_item.data["attachments"]]
    return cls(int(message_item.id), author, created_at, edited_at, channel, guild, content, attachments)
