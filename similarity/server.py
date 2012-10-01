from twisted.web import server, resource
from twisted.internet import reactor, threads
from gaia_wrapper import GaiaWrapper
import json

def server_interface(resource):
    return {
        'add_point':resource.add_point, # location, sound_id
        'delete_point':resource.delete_point, # sound_id
        'contains':resource.contains, # sound_id
        'nnsearch':resource.nnsearch, # sound_id, num_results
        'nnrange':resource.nnrange,  # query_parameters, num_results
        'save':resource.save
    }


class SimilarityServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False
        self.gaia = GaiaWrapper()
    
    def error(self,message):
        return json.dumps({'Error':message})

    def getChild(self, name, request):
       return self

    def render_GET(self, request):        
        return self.methods[request.prepath[1]](**request.args)        
    
    def add_point(self,location,sound_id):        
        self.gaia.add_point(location[0],sound_id[0])
        return json.dumps({'result':'OK'})
            
    def delete_point(self, sound_id):
        self.gaia.delete_point(sound_id[0])
        return json.dumps({'result':'OK'})

    def contains(self, sound_id):
        return json.dumps({'result':self.gaia.contains(sound_id[0])})

    def nnsearch(self,sound_id,num_results):
        result = self.gaia.search_dataset(sound_id[0], num_results[0])        
        return json.dumps({'result':result})        

    def nnrange(self, query_parameters, num_results):
        result = self.gaia.query_dataset(json.loads(query_parameters[0]), num_results[0])        
        
    def save(self):
        self.gaia.save_index()
        return json.dumps({'result':'OK'})




root = resource.Resource()
root.putChild("similarity",SimilarityServer())
site = server.Site(root)
reactor.listenTCP(8002, site)
reactor.run()