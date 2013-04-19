# Create your views here.

from clickthrough.models import Click,Query
from sounds.models import Sound
import datetime


def clicklog_to_model(normalized_log):
    """
        Example nomralized_log:
            {'authenticated_session_key': '09c0af5d7a6ee6eddd7f11b1b2b79a9f',
             'click_type': 'soundpreview',
             'date': datetime.datetime(2013, 4, 18, 16, 17, 46, 837000),
             'raw': '[2013-04-18 16:17:46,837] # INFO    # soundpreview : 09c0af5d7a6ee6eddd7f11b1b2b79a9f : 09c0af5d7a6ee6eddd7f11b1b2b79a9f : 52899',
             'searchtime_session_key': '09c0af5d7a6ee6eddd7f11b1b2b79a9f',
             'sound_id': '52899'}

    """
    CLICK_TYPES = {'soundpreview':'sp',
                   'sounddownload' : 'sd',
                   'packdownload' : 'pd'}
    
    # Distribute parsed fields
    sound = Sound.objects.get(id=normalized_log.get("sound_id",""))
    click_type=CLICK_TYPES.get(normalized_log.get("click_type",""),"")
    click_datetime=normalized_log.get("date", "")
    authenticated_session_key=normalized_log.get("authenticated_session_key","")
    searchtime_session_key=normalized_log.get("searchtime_session_key","")
    
    return Click(sound=sound,click_type=click_type,click_datetime=click_datetime,
                 authenticated_session_key=authenticated_session_key,
                 searchtime_session_key=searchtime_session_key)

def querylog_to_model(normalized_log):
    """
        Example normalized_log:
            {'current_page': '2',
             'date': datetime.datetime(2013, 4, 17, 13, 49, 13, 7000),
             'full_request': '/search/?q=piano&page=2',
             'raw': '[2013-04-17 13:49:13,007] # INFO    # QUERY : /search/?q=piano&page=2 : 1ccff2a2f23e672a96091b04dbc2d0c1 : [38551, 108935, 18331, 12693, 68448, 53767, 31955, 46220, 104025, 11669, 121079, 121078, 121077, 104182, 104181] : 2',
             'searchtime_session_key': '1ccff2a2f23e672a96091b04dbc2d0c1',
             'sound_ids': '[38551, 108935, 18331, 12693, 68448, 53767, 31955, 46220, 104025, 11669, 121079, 121078, 121077, 104182, 104181]'}

    """
    
    query_time=normalized_log.get("date", "")
    searchtime_session_key=normalized_log.get("searchtime_session_key","")
    query_text=normalized_log.get("full_request","")
    rank_order=normalized_log.get("sound_ids","")
    results_page_no=normalized_log.get("current_page","")
    
    q=Query(query_time=query_time,searchtime_session_key=searchtime_session_key,
             query_text=query_text,
             rank_order=rank_order,
             results_page_no=results_page_no)
    q.save()
    
    import ast
    sound_ids=ast.literal_eval(rank_order)
    for sound_id in sound_ids:
        sound = Sound.objects.get(id=sound_id)
        q.sounds.add(sound)
    
    return q

def log_data_builder(dirpath):
    
    """
        - Script for parsing through clickusage log files and adding entries in the
        clickthrough table extracted for each log enry.
        - Assumptions:
            - all the log files are in the current directory ('./')
            - all the log file names start with 'clickusage.log'
            - the path to normalizer definitions is '/usr/local/lib/python2.7/dist-packages/pylogsparser-0.8-py2.7.egg/share/logsparser/normalizers'
    
    """
    import os
    from logsparser.lognormalizer import LogNormalizer as LN
    
    if os.path.isdir(dirpath) is False:
        print dirpath + " is not a directory"
    normalizer = LN("/usr/local/lib/python2.7/dist-packages/pylogsparser-0.8-py2.7.egg/share/logsparser/normalizers")
    for root, dirs, filenames in os.walk(dirpath):
        for f in filenames:
            if f.startswith('clickusage.log'):
                print f
                logs = open(f,'r')
                print "Parsing the log file ..."
                for log in logs:
                    l = {"raw" : log}
                    n = normalizer.normalize(l)
                    if "click_type" in n:
                        print "saving click"
                        c = clicklog_to_model(n)
                        c.save()
                    else:    
                        q = querylog_to_model(n)
                        print "saving query"
                        