import logging

logger      = logging.getLogger('similarity')
handler     = logging.StreamHandler()
formatter   = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)
