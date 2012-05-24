from similarity.settings import REQREP_ADDRESS, READ_TIMEOUT
from general import messenger

class Similarity():

    @classmethod
    def search(cls, sound_id, preset, num_results):
        params = {'type': 'Search',
                  'sound_id': sound_id,
                  'num_results': num_results,
                  'preset': preset}
        return messenger.call_service(REQREP_ADDRESS, params)

    @classmethod
    def query(cls, query_parameters, num_results):
        params = {'type': 'Query',
                  'query_parameters': query_parameters,
                  'num_results': num_results}
        return messenger.call_service(REQREP_ADDRESS, params)

    @classmethod
    def add(cls, sound_id, yaml):
        params = {'type': 'AddSound',
                  'sound_id': sound_id,
                  'yaml': yaml}
        return messenger.call_service(REQREP_ADDRESS, params)


    @classmethod
    def delete(cls, sound_id):
        params = {'type': 'DeleteSound',
                  'sound_id': sound_id}
        return messenger.call_service(REQREP_ADDRESS, params)


    @classmethod
    def contains(cls, sound_id):
        params = {'type': 'Contains',
                  'sound_id': sound_id}
        return messenger.call_service(REQREP_ADDRESS, params)
