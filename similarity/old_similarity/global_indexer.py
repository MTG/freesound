from gaia_indexer import GaiaIndexer
import logging

logger = logging.getLogger('similarity')

global indexer
try:
    print indexer
except NameError:
    logger.debug('Initializing indexer')
    indexer = 'This should never be printed. If it is printed it means the indexer is initialized several times.'
    indexer = GaiaIndexer()
