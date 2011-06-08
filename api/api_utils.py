import settings
#from m30_platform.messaging.datastore import Datastore
#from m30_platform.messaging.aaa import AAA
#from m30_platform.messaging.general import ServiceUnreachable, M30Exception
from piston.utils import rc
import traceback
#from processing_utils import *
#import simplejson as json
from models import ApiKey
#from canoris import logger

'''
APPLICATION = 'canoris'

def update_usage(request, updates):
    
    #The update_usage function is used by the auth decorator, but can be used as well to update
    #usage from within API functions.
    
    if not isinstance(updates, dict):
        raise Exception('Specifying updates should be done in a dict.')
    for action_name, buckets in updates.items():
        for bucket_name, val in buckets.items():
            points = val(request) if callable(val) else val
            AAA.update_usage(request.user, APPLICATION, action_name, bucket_name, points)

def check_aaa(api_key, updates):
    for action in updates.keys():
        result = AAA.get_access_by_key(api_key, APPLICATION, action)
        if not result['access']:
            return False, result
    return True, ''
'''

def build_error_response(e):
    resp = rc.BAD_REQUEST
    resp.status_code = e.status_code
    content = {'error': True,
               'type': e.type,
               'status_code': e.status_code,
               'explanation': ''}
    content.update(e.extra)
    resp.content = content
    print resp.status_code
    return resp


class ReturnError(Exception):
    def __init__(self, status_code, type, extra):
        self.status_code = status_code
        self.type = type
        self.extra = extra

def build_unexpected(e):
    debug = traceback.format_exc() if settings.DEBUG else str(e)
    #TODO: logger?
    #logger.error('500!!! ' + debug)
    return build_error_response(ReturnError(500,
                                            'InternalError',
                                            {'explanation':
                                             'An internal Freesound error ocurred.',
                                             'really_really_sorry': True,
                                             'debug': debug}))


class auth():
    
    def __init__(self, get_parameter='api_key'): # FROM FREESOUND
        self.get_parameter = get_parameter

    def __call__(self, f):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        def decorated_api_func(handler, request, *args, **kargs):
            try:
                
                # Try to get the api key
                api_key = request.GET.get(self.get_parameter, False)
                print "api key", api_key
                if not api_key:
                    raise ReturnError(401, 'AuthenticationError',
                                          {'explanation':  'Please include your api key as a parameter'})
                    #api_key = request.POST.get(API_KEY_GET_PARAMETER_NAME, False)
                
                ''' NOT NEEDED (?)
                # if the resource was not marked as public and there is no api_key
                if not self.public and not api_key:
                    raise ReturnError(403, 'AuthenticationError',
                                      {'explanation':  'This is not a public resource and you supplied no api_key.'})
                '''
                
                try:
                    db_api_key = ApiKey.objects.get(key=api_key, status='OK')
                except ApiKey.DoesNotExist:
                    #return False
                    raise ReturnError(401, 'AuthenticationError',
                                          {'explanation':  'Supplied api_key does not exist'})
                request.user = db_api_key.user                
                #return True
            
                '''
                # if an api_key was supplied check if it's valid, even though the resource may be public
                if api_key:
                    # mark the request as public (not the same as the resource being public)
                    setattr(request, 'public', False)
                    try:
                        userd = Datastore.get_user_by_key(api_key)
                        if not userd['valid']:
                            raise ReturnError(401, 'AuthenticationError',
                                              {'explanation':  'Your api_key was not validated yet.'})
                    # if there is no user for the api_key, return '401 Forbidden', this is the authentication in essence
                    except:
                        raise ReturnError(401, 'AuthenticationError',
                                          {'explanation':  'You supplied an invalid api_key'})

                    # if the resource is not marked as public and updates were specified, do authorization and throttling checks
                    if not self.public and self.updates:
                        access, reason = check_aaa(api_key, self.updates)
                        if not access:
                            throttledp = 'throttle_result' in reason
                            if throttledp:
                                tr = json.loads(reason['throttle_result'])
                                if len(tr) > 0:
                                    tr = tr[0]
                                    throttle_error = "Access was throttled for user '%s' because the limit of %s/%ss. (%s) was hit for action %s, used: %s" % \
                                        (tr['username'], tr['limit'], tr['delta'], tr['bucket'], tr['action'], tr['sum'])
                                else:
                                    throttle_error = "Access was throttled, no explanation."
                            raise ReturnError(403, 'AuthorizationError',
                                              {'access': False,
                                               'throttled': throttledp,
                                               'explanation':  throttle_error \
                                                        if throttledp \
                                                        else reason['access_result']})
                    # extend the request object with the user and api_key parameter
                    setattr(request, 'user', userd['username'])
                    setattr(request, 'userd', userd)
                    setattr(request, 'api_key', api_key)
                    # only update if the resource is not marked as public, and an action and updates were specified
                    if not self.public and self.updates:
                        update_usage(request, self.updates)
                
                else:
                    setattr(request, 'public', True)
                    setattr(request, 'user', False)
                    setattr(request, 'api_key', False)
                '''
                
                return f(handler, request, *args, **kargs)
            
            except ReturnError, e:
                print "HEYHEYHEY"
                print "e:" + str(e.status_code)
                return build_error_response(e)
            except Exception, e:
                print "ooooh nooooo"
                return build_unexpected(e)

        return decorated_api_func

''' NOT NEEDED (?)
def get_property(property, user):
    #TODO: return the dictionary retrieved from the AAA component
    return
'''

''' FROM FREESOUND key_authentication
    def challenge(self):
        resp = rc.FORBIDDEN
        resp.content = 'Please include your api key as the %s GET/POST parameter.\n' % self.get_parameter
        return resp
    '''
