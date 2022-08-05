import disnake
import datetime
from typing import List, Tuple, Optional, Iterator

from database import session
from database.tables.messages import Message
from database import users_repo, channels_repo

def get_message(message_id: int) -> Optional[Message]:
  return session.query(Message).filter(Message.id == str(message_id)).one_or_none()

def get_author_of_last_message_metric(channel_id: int, thread_id: Optional[int]) -> Optional[int]:
  user_id = session.query(Message.author_id).filter(Message.channel_id == str(channel_id), Message.thread_id == (str(thread_id) if thread_id is not None else None), Message.use_for_metrics == True).order_by(Message.created_at.desc()).first()
  return int(user_id[0]) if user_id is not None else None

def add_or_set_message(message: disnake.Message, commit: bool=True) -> Optional[Message]:
  if message.guild is None or not isinstance(message.author, disnake.Member):
    return None

  users_repo.get_or_create_member_if_not_exist(message.author)
  can_collect_data = users_repo.can_collect_data(message.author.id, message.guild.id)

  thread = None
  channel = message.channel
  if isinstance(channel, disnake.Thread):
    thread = channel
    channel = channel.parent

  if message.channel is not None:
    channels_repo.get_or_create_text_channel_if_not_exist(message.channel)

  message_it = get_message(message.id)
  if message_it is None:
    use_for_metrics = get_author_of_last_message_metric(channel.id, thread.id if thread is not None else None) != message.author.id

    message_it = Message.from_message(message)
    message_it.use_for_metrics = use_for_metrics
    session.add(message_it)
  else:
    message_it.content = message.content
    message_it.edited_at = message.edited_at

  if not can_collect_data:
    message_it.content = None
    message_it.data = None

  if commit:
    session.commit()
  return message_it

def get_messages_iterator(guild_id: int, author_id: Optional[int]) -> Iterator[Message]:
  def get_messages(index: int):
    if author_id is not None:
      return session.query(Message).filter(Message.author_id == str(author_id), Message.guild_id == str(guild_id)).order_by(Message.created_at.desc()).offset(index * 2000).limit(2000).all()
    else:
      return session.query(Message).filter(Message.guild_id == str(guild_id)).order_by(Message.created_at.desc()).offset(index * 2000).limit(2000).all()

  iter_index = 0
  messages = get_messages(iter_index)
  while messages:
    for message in messages:
      yield message

    iter_index += 1
    messages = get_messages(iter_index)

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

def remove_message_data(user_id: int, guild_id: int):
  session.query(Message).filter(Message.author_id == str(user_id), Message.guild_id == str(guild_id)).update({Message.content: None, Message.data: None})
  session.commit()
