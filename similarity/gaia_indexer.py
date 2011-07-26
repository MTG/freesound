from __future__ import with_statement
from gaia_wrapper import *
from threading import Lock
from shared_lock import SharedLock
import time, os, json, logging
from settings import PRESETS, READ_TIMEOUT, UPDATE_TIMEOUT

logger = logging.getLogger('similarity')

class GaiaIndexer:

    def __init__(self):
        logger.debug('Initializing GaiaIndexer')
        self.lock = Lock()
        self.shared_lock = SharedLock()
        self.index = GaiaWrapper()
        logger.debug('Initialized GaiaIndexer')


    def __acquire_shared(self, timeout):
        logger.debug('Acquiring shared lock')
        acquired = self.shared_lock.acquire_shared(timeout)
        return True if acquired else self.raise_locked()


    def __release_shared(self):
        self.shared_lock.release_shared()
        logger.debug('Released shared lock')


    def __acquire_exclusive(self, timeout):
        logger.debug('Acquiring exclusive lock')
        acquired = self.shared_lock.acquire(timeout)
        return True if acquired else self.raise_locked()


    def __release_exclusive(self):
        self.shared_lock.release()
        logger.debug('Released exclusive lock')


    def __raise_locked(self):
        logger.error('Could not get lock.')
        raise Exception('The index is currently locked which probably means it is being updated.')


    def add(self, yaml_path, sound_id):
        logger.debug('Adding point with id %s' % sound_id)
        self.__acquire_exclusive(UPDATE_TIMEOUT)
        try:
            self.index.add_point(yaml_path, sound_id)
        finally:
            self.__release_exclusive()


    def delete(self, sound_id):
        logger.debug('Deleting point with id %s' % sound_id)
        self.__acquire_exclusive(UPDATE_TIMEOUT)
        try:
            self.index.delete_point(sound_id)
        finally:
            self.__release_exclusive()


    def search(self, point, no_of_results, presetkey):
        '''
        The 'point' argument can either be the name of an already present point
        or the location of a yaml file (has to have extension .yaml).
        '''
        logger.debug('Searching with id %s' % point)
        self.__acquire_shared(READ_TIMEOUT)
        try:
            return self.index.search_dataset(point, no_of_results, presetkey)
        finally:
            self.__release_shared()

    def contains(self, point):
        self.__acquire_shared(READ_TIMEOUT)
        try:
            return self.index.contains(point)
        finally:
            self.__release_shared()
