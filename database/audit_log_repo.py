import datetime
import disnake
from typing import Optional, Union

from database import session
from database.tables.audit_log import AuditLogItemType, AuditLog
from database.users_repo import create_user_if_not_exist
from database.messages_repo import Message

def create_message_edited_log(before: Optional[Union[disnake.Message, Message]], after: disnake.Message) -> AuditLog:
  thread = None
  channel = after.channel
  if isinstance(channel, disnake.Thread):
    thread = channel
    channel = channel.parent

  create_user_if_not_exist(after.author)

  before_attachments = None
  if before is not None:
    before_attachments = (";".join([att.url for att in before.attachments])) if isinstance(before, disnake.Message) else before.attachments

  data = {
    "message_id": after.id,
    "channel_id": channel.id,
    "thread_id": thread.id if thread is not None else None,
    "content_before": before.content if  before is not None else None,
    "attachments_before":  before_attachments,
    "content_after": after.content,
    "attachments_after": ";".join([att.url for att in before.attachments])
  }

  item = AuditLog(timestamp=after.edited_at, user_id=str(after.author.id), log_type=AuditLogItemType.MESSAGE_EDITED, data=data)
  session.add(item)
  session.commit()

  return item

def create_message_deleted_log(message: disnake.Message) -> AuditLog:
  message_id = message.id
  author_id = str(message.author.id)
  thread_id = None
  channel_id = message.channel.id
  if isinstance(message.channel, disnake.Thread):
    thread_id = message.channel.id
    channel_id = message.channel.parent.id
  content = message.content
  attachments = ";".join([att.url for att in message.attachments])

  create_user_if_not_exist(message.author)

  data = {
    "message_id": message_id,
    "channel_id": channel_id,
    "thread_id": thread_id,
    "content": content,
    "attachments": attachments
  }

  item = AuditLog(user_id=author_id, log_type=AuditLogItemType.MESSAGE_DELETED, data=data)
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

  if data.keys():
    create_user_if_not_exist(after)
    item = AuditLog(user_id=str(after.id), log_type=AuditLogItemType.MEMBER_UPDATED, data=data)
    session.add(item)
    if commit:
      session.commit()
    return item
  return None

def delete_old_logs(days: int):
  threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days)
  session.query(AuditLog).filter(AuditLog.timestamp <= threshold).delete()
  session.commit()