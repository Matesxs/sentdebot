import datetime

import disnake
from typing import Optional

from features import before_message_context
from database.tables.audit_log import AuditLog, AuditLogItemType
from database import session
from database import users_repo
from database.tables import messages

def auditlog_member_joined(member: disnake.Member) -> AuditLog:
  item = AuditLog(guild_id=str(member.guild.id), data={"user_id": member.id}, log_type=AuditLogItemType.MEMBER_JOINED, timestamp=member.joined_at)
  session.add(item)
  session.commit()
  return item

def auditlog_member_left(member: disnake.Member) -> AuditLog:
  item = AuditLog(guild_id=str(member.guild.id), data={"user_id": member.id}, log_type=AuditLogItemType.MEMBER_LEFT)
  session.add(item)
  session.commit()
  return item

def auditlog_member_updated(before: disnake.Member, after: disnake.Member) -> Optional[AuditLog]:
  before_data = {}
  after_data = {}

  if before.display_name != after.display_name:
    before_data["nick"] = before.display_name
    after_data["nick"] = after.display_name

  if before.display_avatar.url != after.display_avatar.url:
    before_data["icon_url"] = before.display_avatar.url
    after_data["icon_url"] = after.display_avatar.url

  if (before.premium_since is not None and after.premium_since is None) or \
     (before.premium_since is None and after.premium_since is not None):
    before_data["premium"] = before.premium_since is not None
    after_data["premium"] = after.premium_since is not None

  if not before_data.keys():
    return None

  users_repo.get_or_create_member_if_not_exist(after)
  member_iid = users_repo.member_identifier_to_member_iid(after.id, after.guild.id)
  item = AuditLog(user_id=str(after.id), guild_id=str(after.guild.id), member_iid=member_iid, log_type=AuditLogItemType.MEMBER_UPDATED, data={"before": before_data, "after": after_data})
  session.add(item)
  session.commit()
  return item

def auditlog_user_update(before: disnake.User, after: disnake.User):
  before_data = {}
  after_data = {}

  if before.name != after.name:
    before_data["name"] = before.name
    after_data["name"] = after.name

  if not before_data.keys():
    return None

  users_repo.get_or_create_user_if_not_exist(after)
  item = AuditLog(user_id=str(after.id), log_type=AuditLogItemType.USER_UPDATED, data={"before": before_data, "after": after_data})
  session.add(item)
  session.commit()
  return item

def auditlog_message_edited(before: Optional[before_message_context.BeforeMessageContext], after: disnake.Message) -> Optional[AuditLog]:
  before_data = {}
  after_data = {}

  before_urls = [att.url for att in before.attachments] if before is not None else []
  after_ulrs = [att.url for att in after.attachments]

  if before_urls != after_ulrs:
    if before is not None:
      before_data["attachments"] = messages.message_to_message_data(before)["attachments"]
    after_data["attachments"] = messages.message_to_message_data(after)["attachments"]

  if before is not None:
    if before.content != after.content:
      before_data["content"] = before.content
      after_data["content"] = after.content

  if not after_data.keys():
    return None

  if after.guild is not None and isinstance(after.author, disnake.Member):
    guild_id = str(after.guild.id)
    users_repo.get_or_create_member_if_not_exist(after.author)
    member_iid = users_repo.member_identifier_to_member_iid(after.author.id, after.guild.id)
  else:
    users_repo.get_or_create_user_if_not_exist(after.author)
    guild_id = None
    member_iid = None

  channel_id = after.channel.id if not isinstance(after.channel, disnake.DMChannel) else None

  item = AuditLog(user_id=str(after.author.id), guild_id=guild_id, member_iid=member_iid, log_type=AuditLogItemType.MESSAGE_EDITED, data={"message_id": after.id, "channel_id": channel_id, "before": before_data, "after": after_data})
  session.add(item)
  session.commit()
  return item

def auditlog_message_deleted(message: before_message_context.BeforeMessageContext):
  if message.guild is not None and isinstance(message.author, disnake.Member):
    guild_id = str(message.guild.id)
    users_repo.get_or_create_member_if_not_exist(message.author)
    member_iid = users_repo.member_identifier_to_member_iid(message.author.id, message.guild.id)
  else:
    users_repo.get_or_create_user_if_not_exist(message.author)
    guild_id = None
    member_iid = None

  channel_id = message.channel.id if not isinstance(message.channel, disnake.DMChannel) else None

  item = AuditLog(user_id=str(message.author.id), guild_id=guild_id, member_iid=member_iid, log_type=AuditLogItemType.MESSAGE_DELETED, data={"message_id": message.id, "channel_id": channel_id, "content": message.content, "attachments": messages.message_to_message_data(message)["attachments"]})
  session.add(item)
  session.commit()

def delete_old_auditlogs(days_back: int):
  threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
  session.query(AuditLog).filter(AuditLog.timestamp < threshold).delete()
  session.commit()
