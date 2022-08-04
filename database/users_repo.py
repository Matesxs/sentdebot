import datetime

import disnake
from typing import Optional, List, Union, Iterator

from database import session
from database.tables.users import User, Member
from database import guilds_repo

def get_user(user_id: int) -> Optional[User]:
  return session.query(User).filter(User.id == str(user_id)).one_or_none()

def get_member(member_id: int, guild_id: int) -> Optional[Member]:
  member = session.query(Member).filter(Member.id == str(member_id), Member.guild_id == str(guild_id)).one_or_none()
  if member is not None and member.left_at is not None:
    member.left_at = None
    session.commit()
  return member

def get_all_users_iterator() -> Iterator[User]:
  def get_users(index: int):
    return session.query(User).offset(2000 * index).limit(2000).all()

  iter_index = 0
  users = get_users(iter_index)
  while users:
    for user in users:
      yield user

    iter_index += 1
    users = get_users(iter_index)

def get_or_create_user_if_not_exist(user: Union[disnake.Member, disnake.User]) -> User:
  user_it = get_user(user.id)
  if user_it is None:
    user_it = User.from_user(user)
    session.add(user_it)
    session.commit()
  else:
    if isinstance(user, disnake.Member):
      if user_it.status != user.status:
        user_it.status = user.status
        session.commit()
  return user_it

def get_or_create_member_if_not_exist(member: disnake.Member) -> Member:
  member_it = get_member(member.id, member.guild.id)
  user_it = get_or_create_user_if_not_exist(member)

  if member_it is None:
    member_it = Member.from_member(member)
    session.add(member_it)
    session.commit()

  if user_it.status != member.status:
    user_it.status = member.status
    session.commit()

  return member_it

def set_member_left(member: disnake.Member):
  session.query(Member).filter(Member.id == str(member.id), Member.guild_id == str(member.guild.id)).update({Member.left_at: datetime.datetime.utcnow()})
  session.commit()

def delete_left_members(days_after_left: int, commit: bool=True):
  threshold = datetime.datetime.utcnow() - datetime.timedelta(days=days_after_left)
  session.query(Member).filter(Member.left_at != None, Member.left_at <= threshold).delete()
  if commit:
    session.commit()

def members_joined_in_timeframe(from_date: datetime.datetime, to_date: datetime.datetime, guild_id: int) -> List[Member]:
  return session.query(Member).filter(Member.joined_at >= from_date, Member.joined_at <= to_date, Member.guild_id == str(guild_id)).order_by(Member.joined_at.desc()).all()

def member_identifier_to_member_iid(user_id: int, guild_id: int) -> Optional[int]:
  data = session.query(Member.member_iid).filter(Member.id == str(user_id), Member.guild_id == str(guild_id)).one_or_none()
  if data is None: return None
  return data[0]

def can_collect_data(user_id: int, guild_id: int) -> bool:
  data = session.query(Member.collect_data).filter(Member.id == str(user_id), Member.guild_id == str(guild_id)).one_or_none()
  if data is None: return True
  if data[0]: return True
  return False
