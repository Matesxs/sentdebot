from database import session, database
import pkgutil
import importlib

from util.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

def load_sub_modules(module):
  package = importlib.import_module(module)

  for _, name, _ in pkgutil.iter_modules(package.__path__):
    importlib.import_module(f'{package.__name__}.{name}')

def init_tables():
  load_sub_modules("database.tables")

  database.base.metadata.create_all(database.db)
  session.commit()

  logger.info("Initializating all loaded tables")