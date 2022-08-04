import datetime
import disnake
from typing import Optional, Union

from database import session
from database.tables.audit_log import AuditLogItemType, AuditLog
from database.users_repo import get_or_create_member_if_not_exist, member_identifier_to_member_iid
from database.messages_repo import Message
from features.base_bot import BaseAutoshardedBot

async def create_message_edited_log(bot: BaseAutoshardedBot, before: Optional[Union[disnake.Message, Message]], after: disnake.Message) -> AuditLog:
  thread = None
  channel = after.channel
  if isinstance(channel, disnake.Thread):
    thread = channel
    channel = channel.parent

  get_or_create_member_if_not_exist(after.author)
  if before is not None and isinstance(before, Message):
    before = await before.to_object(bot)

  data = {
    "message_id": after.id,
    "channel_id": channel.id,
    "thread_id": thread.id if thread is not None else None,
    "content_before": before.content if  before is not None else None,
    "attachments_before": [att.url for att in before.attachments] if before is not None else None,
    "content_after": after.content,
    "attachments_after": [att.url for att in after.attachments]
  }

  user_id = after.author.id
  guild_id = after.guild.id if after.guild is not None else None
  member_iid = None
  if guild_id is not None:
    member_iid = member_identifier_to_member_iid(user_id, guild_id)

  item = AuditLog(timestamp=after.edited_at, user_id=str(user_id), guild_id=str(guild_id) if guild_id is not None else None, member_iid=member_iid, log_type=AuditLogItemType.MESSAGE_EDITED, data=data)
  session.add(item)
  session.commit()

  return item

def create_message_deleted_log(message: disnake.Message) -> AuditLog:
  message_id = message.id
  thread_id = None
  channel_id = message.channel.id
  if isinstance(message.channel, disnake.Thread):
    thread_id = message.channel.id
    channel_id = message.channel.parent.id
  content = message.content
  attachments = [att.url for att in message.attachments]

  get_or_create_member_if_not_exist(message.author)

  data = {
    "message_id": message_id,
    "channel_id": channel_id,
    "thread_id": thread_id,
    "content": content,
    "attachments": attachments
  }

  user_id = message.author.id
  guild_id = message.guild.id if message.guild is not None else None
  member_iid = None
  if guild_id is not None:
    member_iid = member_identifier_to_member_iid(user_id, guild_id)

  item = AuditLog(user_id=str(user_id), guild_id=str(guild_id) if guild_id is not None else None, member_iid=member_iid, log_type=AuditLogItemType.MESSAGE_DELETED, data=data)
  session.add(item)
  session.commit()

  return item

def create_member_changed_log(before: disnake.Member, after: disnake.Member, commit: bool=False) -> Optional[AuditLog]:
  data = {}
  if before.display_name != after.display_name:
    data["nick_before"] = before.display_name
    data["nick_after"] = after.display_name

  if before.display_avatar.url != after.display_avatar.url:
    data["avatar_url_before"] = before.display_avatar.url
    data["avatar_url_after"] = after.display_avatar.url

  if before.premium_since != after.premium_since:
    data["new_premium_state"] = after.premium_since is not None

  if data.keys():
    get_or_create_member_if_not_exist(after)

    user_id = after.id
    guild_id = after.guild.id if after.guild is not None else None
    member_iid = member_identifier_to_member_iid(user_id, guild_id)

    item = AuditLog(user_id=str(user_id), guild_id=str(guild_id), member_iid=member_iid, log_type=AuditLogItemType.MEMBER_UPDATED, data=data)
    session.add(item)
    if commit:
      session.commit()
    return item
  return None

def delete_old_logs(days: int, commit: bool=True):
  threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days)
  session.query(AuditLog).filter(AuditLog.timestamp <= threshold).delete()
  if commit:
    session.commit()
