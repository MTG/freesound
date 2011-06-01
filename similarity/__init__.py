import logging, multiprocessing
from logging.handlers import RotatingFileHandler
from settings import LOGFILE
logger      = logging.getLogger('similarity')

handler     = RotatingFileHandler(LOGFILE,
                                  maxBytes=2*1024*1024,
                                  backupCount=5)
handler.setLevel(logging.DEBUG)

std_handler = logging.StreamHandler()
std_handler.setLevel(logging.DEBUG)

formatter   = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)

std_handler.setFormatter(formatter)
logger.addHandler(std_handler)

print logger
