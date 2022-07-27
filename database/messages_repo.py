import disnake
import datetime
from typing import List, Tuple, Optional
import sqlalchemy.orm

from database import session
from database.tables.messages import Message, MessageAttachment
from database import users_repo, channels_repo

def get_message(message_id: int) -> Optional[Message]:
  return session.query(Message).filter(Message.id == str(message_id)).one_or_none()

def update_attachments(message: Message, new_attachments: List[disnake.Attachment], commit: bool=True):
  if get_message(int(message.id)) is None:
    return

  current_attachments: List[MessageAttachment] = message.attachments
  current_urls = [att.url for att in current_attachments]
  new_urls = [att.url for att in new_attachments]
  att_to_create = [att for att in new_attachments if att.url not in current_urls]

  for att_it in current_attachments:
    if att_it.url not in new_urls:
      session.delete(att_it)

  for att in att_to_create:
    item = MessageAttachment(id=str(att.id), message_id=message.id, url=att.url)
    session.add(item)

  if commit:
    session.commit()

def get_author_of_last_message_metric(channel_id: int, thread_id: Optional[int]) -> Optional[int]:
  user_id = session.query(Message.author_id).filter(Message.channel_id == str(channel_id), Message.thread_id == (str(thread_id) if thread_id is not None else None), Message.use_for_metrics == True).order_by(Message.created_at.desc()).first()
  return int(user_id[0]) if user_id is not None else None

def add_message(message: disnake.Message, commit: bool=True) -> Message:
  if message.guild is not None and isinstance(message.author, disnake.Member):
    users_repo.get_or_create_member_if_not_exist(message.author)
  else:
    users_repo.get_or_create_user_if_not_exist(message.author)

  thread = None
  channel = message.channel
  if isinstance(channel, disnake.Thread):
    thread = channel
    channel = channel.parent

  if message.channel is not None:
    channels_repo.get_or_create_text_channel_if_not_exist(message.channel)

  use_for_metrics = get_author_of_last_message_metric(channel.id, thread.id if thread is not None else None) != message.author.id

  item = Message.from_message(message)
  item.use_for_metrics = use_for_metrics
  session.add(item)

  for att in message.attachments:
    att_it = MessageAttachment(id=str(att.id), message_id=str(message.id), url=att.url)
    session.add(att_it)

  if commit:
    session.commit()
  return item

def add_if_not_existing(message: disnake.Message, commit: bool=True) -> Optional[Message]:
  message_it = get_message(message.id)
  if message_it is None:
    return add_message(message, commit)
  return None

def get_messages_iterator(guild_id: int, author_id: Optional[int]) -> sqlalchemy.orm.Query:
  if author_id is not None:
    query = session.query(Message).filter(Message.id == str(author_id), Message.guild_id == str(guild_id)).order_by(Message.created_at.desc())
  else:
    query = session.query(Message).filter(Message.guild_id == str(guild_id)).order_by(Message.created_at.desc())
  return query

def get_message_metrics(guild_id: int, days_back: int) -> List[Tuple[int, datetime.datetime, int, int]]:
  threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
  data = session.query(Message.id, Message.created_at, Message.author_id, Message.channel_id).filter(Message.created_at > threshold_date, Message.use_for_metrics == True, Message.guild_id == str(guild_id)).order_by(Message.created_at.desc()).all()
  return [(int(d[0]), d[1], int(d[2]), int(d[3])) for d in data]

def get_messages_of_member(member_id: int, guild_id: int, hours_back: float) -> List[Message]:
  threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
  return session.query(Message).filter(Message.author_id == str(member_id), Message.guild_id == str(guild_id), Message.created_at > threshold).order_by(Message.created_at.desc()).all()

def delete_message(message_id: int, commit: bool=True):
  session.query(Message).filter(Message.id == str(message_id)).delete()
  if commit:
    session.commit()

def delete_old_messages(days: int, commit: bool=True):
  threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days)
  session.query(Message).filter(Message.created_at <= threshold).delete()
  if commit:
    session.commit()