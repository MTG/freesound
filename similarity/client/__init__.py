from similarity.settings import REQREP_ADDRESS
from general import messenger

class Similarity():

    @classmethod
    def search(cls, sound_id, preset, num_results):
        params = {'type': 'Search',
                  'sound_id': sound_id,
                  'num_results': num_results,
                  'preset': preset}
        return messenger.call_service(REQREP_ADDRESS, params, 5)


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
