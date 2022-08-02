from config import config
from util.logger import setup_custom_logger
from features.base_bot import BaseAutoshardedBot
from database.database_manipulation import init_tables

logger = setup_custom_logger(__name__)

if config.base.discord_api_key is None:
  logger.error("Discord API key is missing!")
  exit(-1)

# Init database tables
init_tables()

bot = BaseAutoshardedBot()

bot.run(config.base.discord_api_key)
