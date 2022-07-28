from database import session, database

from database.tables import guilds
from database.tables import channels
from database.tables import users
from database.tables import audit_log
from database.tables import user_metrics
from database.tables import messages
from database.tables import projects
from database.tables import help_threads
from database.tables import questions_and_answers
from database.tables import weather_settings

from util.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

def init_tables():
  database.base.metadata.create_all(database.db)
  session.commit()

  logger.info("Initializating all loaded tables")