from typing import Optional, List
import datetime
import disnake

from config import config
from database import session
from database.tables.help_threads import HelpThread
from database import users_repo, channels_repo

def get_thread(thread_id: int) -> Optional[HelpThread]:
  return session.query(HelpThread).filter(HelpThread.thread_id == str(thread_id)).one_or_none()

def thread_exists(thread_id: int):
  return get_thread(thread_id) is not None

def update_thread_activity(thread_id: int, new_activity: datetime.datetime, commit: bool=True):
  session.query(HelpThread).filter(HelpThread.thread_id == str(thread_id)).update({HelpThread.last_activity_time : new_activity})

  if commit:
    session.commit()

def create_thread(thread: disnake.Thread, owner: disnake.Member, tags: Optional[str]=None) -> Optional[HelpThread]:
  users_repo.get_or_create_member_if_not_exist(owner)
  member_iid_of_main_guild = users_repo.member_identifier_to_member_iid(owner.id, config.ids.main_guild)
  if member_iid_of_main_guild is None: return None

  channels_repo.get_or_create_text_thread(thread)
  item = HelpThread(thread_id=str(thread.id), member_iid=member_iid_of_main_guild, owner_id=str(owner.id), tags=tags)
  session.add(item)
  session.commit()

  return item

def get_all() -> List[HelpThread]:
  return session.query(HelpThread).order_by(HelpThread.last_activity_time.desc()).all()

def delete_thread(thread_id: int):
  session.query(HelpThread).filter(HelpThread.thread_id == str(thread_id)).delete()
  session.commit()

def get_unactive(days_threshold: int) -> List[HelpThread]:
  date_threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days_threshold)
  return session.query(HelpThread).filter(HelpThread.last_activity_time < date_threshold).all()

def delete_unactive(days_threshold: int):
  date_threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days_threshold)
  session.query(HelpThread).filter(HelpThread.last_activity_time < date_threshold).delete()
  session.commit()
