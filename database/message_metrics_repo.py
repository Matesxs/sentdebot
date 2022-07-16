import disnake
from database import session
from database.tables.message_metrics import MessageMetrics
import datetime
from typing import List, Tuple, Optional

def add_message_metrics(message: disnake.Message) -> MessageMetrics:
  item = MessageMetrics(message_id=str(message.id), timestamp=datetime.datetime.utcnow(), author_id=str(message.author.id), channel_id=str(message.channel.id))
  session.add(item)
  session.commit()
  return item

def get_message_metrics(days_back: int) -> List[Tuple[int, datetime.datetime, int, int]]:
  threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
  data:List[MessageMetrics] = session.query(MessageMetrics).filter(MessageMetrics.timestamp > threshold_date).order_by(MessageMetrics.timestamp).all()

  output = []
  for d in data:
    output.append((int(d.message_id), d.timestamp, int(d.author_id), int(d.channel_id)))
  return output

def get_author_of_last_message(channel_id: int) -> Optional[int]:
  user_id = session.query(MessageMetrics.author_id).filter(MessageMetrics.channel_id == str(channel_id)).order_by(MessageMetrics.timestamp).first()
  return int(user_id[0]) if user_id is not None else None