import logging
from settings import LOGFILE, LOGFILE_LEVEL

logger      = logging.getLogger('similarity')

handler     = logging.handlers.RotatingFileHandler(LOGFILE,
                                                   maxBytes=2*1024*1024,
                                                   backupCount=5)
handler.setLevel(LOGFILE_LEVEL)

formatter   = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)
