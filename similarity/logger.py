import logging
from logging.handlers import RotatingFileHandler
from settings import LOGFILE, LOGFILE_LEVEL

logger      = logging.getLogger('similarity')

handler     = RotatingFileHandler(LOGFILE,
                                  maxBytes=2*1024*1024,
                                  backupCount=5)
handler.setLevel(LOGFILE_LEVEL)

std_handler = logging.StreamHandler()
std_handler.setLevel(LOGFILE_LEVEL)

formatter   = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)

std_handler.setFormatter(formatter)
logger.addHandler(std_handler)
