import settings
from piston.utils import rc
import traceback
from models import ApiKey
from piston.emitters import Emitter
from piston.handler import typemapper
import logging

logger = logging.getLogger("api")

def build_error_response(e, request):
    
    #logger.error(str(e.status_code) + ' API error: ' + e.type)
    content = {"error": True,
               "type": e.type,
               "status_code": e.status_code,
               "explanation": ""}
    content.update(e.extra)
    response = rc.BAD_REQUEST
    format = request.GET.get("format", "json")
    
    em_info = Emitter.get(format)
    RequestEmitter = em_info[0]
    emitter = RequestEmitter(content, typemapper, "", "", False)
    response.content = emitter.render(request)
    response['Content-Type'] = em_info[1]

    return response
    

class ReturnError(Exception):
    def __init__(self, status_code, type, extra):
        self.status_code = status_code
        self.type = type
        self.extra = extra

def build_unexpected(e, request):
    debug = traceback.format_exc() if settings.DEBUG else str(e)
    logger.error('500 API error: Unexpected')
    
    return build_error_response(ReturnError(500,
                                            "InternalError",
                                            {"explanation":
                                             "An internal Freesound error ocurred.",
                                             "really_really_sorry": True,
                                             "debug": debug}
                                             ), request)

def build_invalid_url(e):
    format = e.GET.get("format", "json")
    logger.error('404 API error: Invalid Url')
    
    return build_error_response(ReturnError(404,
                                            "InvalidUrl",
                                            {"explanation":
                                             "The introduced url is invalid.",}
                                             ), e)

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
                if not api_key:
                    logger.error('401 API error: Authentication error (no api key supplied)')
                    raise ReturnError(401, "AuthenticationError",
                                          {"explanation":  "Please include your api key as the api_key GET parameter"},
                                          )
                try:
                    db_api_key = ApiKey.objects.get(key=api_key, status='OK')
                except ApiKey.DoesNotExist:
                    logger.error('401 API error: Authentication error (wrong api key)')
                    raise ReturnError(401, "AuthenticationError",
                                          {"explanation":  "Supplied api_key does not exist"},
                                          )

                request.user = db_api_key.user
                return f(handler, request, *args, **kargs)
            except ReturnError, e:
                return build_error_response(e, request)
            except Exception, e:
                return build_unexpected(e, request)

        return decorated_api_func


def parse_filter(filter_string):

    operators = ['OR','AND','(',')']

    # Find ':'
    filter_struct = []

    min_pos = 0
    while filter_string.find(':',min_pos) != -1:
        current_pos = filter_string.find(':',min_pos)
        min_pos = current_pos + 1

        # Left part (feature name)
        previous_space_pos = filter_string.rfind(' ',0,current_pos)
        feature_name = filter_string[previous_space_pos+1:current_pos]

        # Right part (value, range)
        if filter_string[current_pos+1] == '[':
            next_space_pos = current_pos + 1
            for i in range(0,3):
                next_space_pos = filter_string.find(' ',next_space_pos + 1)
            right_part = filter_string[current_pos+2:next_space_pos]
            type_val = "RANGE"

        elif filter_string[current_pos+1] == '"':
            next_quote_pos = filter_string.find('"',current_pos + 2)
            right_part = filter_string[current_pos+1:next_quote_pos+1]
            type_val = "STRING"
        else:
            next_space_pos = filter_string.find(' ',current_pos + 1)
            if next_space_pos == -1:
                next_space_pos = len(filter_string)
            right_part = filter_string[current_pos+1:next_space_pos + 1]
            if not "," in right_part:
                type_val = "NUMBER"
            else:
                type_val = "ARRAY"

        for op in operators:
            feature_name = feature_name.replace(op,"")
            right_part = right_part.replace(op,"")

        filter_struct.append({'feature':feature_name,'type':type_val,'value':right_part,'delimiter_position':current_pos,'id':len(filter_struct)+1})

    # Find OPERATORS clauses
    for op in operators:
        min_pos = 0
        while filter_string.find(op,min_pos) != -1:
            current_pos = filter_string.find(op,min_pos)
            min_pos = current_pos + 1
            # Insert OPERATOR clause in appropiate place of filter_struct
            for i,f in enumerate(filter_struct):
                if type(f) == dict:
                    if f['delimiter_position'] > current_pos:
                        filter_struct.insert(i,op)
                        break

    # Add AND operators by default (only where there are no other operators between two features)
    final_filter_struct = []
    for i in range(0,len(filter_struct)):
        if i < len(filter_struct) -1:
            if type(filter_struct[i]) == dict and type(filter_struct[i+1]) == dict:
                final_filter_struct.append(filter_struct[i])
                final_filter_struct.append('AND')
            elif type(filter_struct[i]) == dict and filter_struct[i+1] == "(":
                final_filter_struct.append(filter_struct[i])
                final_filter_struct.append('AND')
            elif filter_struct[i] == ")" and type(filter_struct[i+1]) == dict:
                final_filter_struct.append(filter_struct[i])
                final_filter_struct.append('AND')
            else:
                final_filter_struct.append(filter_struct[i])
        else:
            final_filter_struct.append(filter_struct[i])

    # Check good pairing of parenthesis
    if final_filter_struct.count("(") != final_filter_struct.count(")"):
        return "BAD FILTER"

    # Change values for corrent types
    for f in final_filter_struct:
        if type(f) == dict:
            if f['type'] == 'NUMBER':
                f['value'] = float(f['value'])
            elif f['type'] == 'ARRAY':
                f['value'] = [float(x) for x in f['value'].split(',')]
            elif f['type'] == 'STRING':
                f['value'] = str(f['value'].replace('sharp','#'))
            elif f['type'] == 'RANGE':
                min_str = f['value'][:f['value'].find("TO")-1]
                if min_str != "*":
                    min_v = float(min_str)
                else:
                    min_v = None
                max_str = f['value'][f['value'].find("TO")+3:].replace(']','')
                if max_str != "*":
                    max_v = float(max_str)
                else:
                    max_v = None
                f['value'] = {'min':min_v,'max':max_v}

    return final_filter_struct


def parse_target(target_string):
    target_struct = {}

    min_pos = 0
    while target_string.find(':',min_pos) != -1:
        current_pos = target_string.find(':',min_pos)
        min_pos = current_pos + 1

        # Left part (feature name)
        previous_space_pos = target_string.rfind(' ',0,current_pos)
        feature_name = target_string[previous_space_pos+1:current_pos]

        # Right part
        next_space_pos = target_string.find(' ',current_pos + 1)
        if next_space_pos == -1:
            next_space_pos = len(target_string)
        right_part = target_string[current_pos+1:next_space_pos + 1]
        if not "," in right_part:
            value = float(right_part)
        else:
            value = [float(x) for x in right_part.split(',')]

        target_struct[feature_name] = value

    return target_struct
