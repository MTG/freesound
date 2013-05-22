# Create your views here.

from clickthrough.models import Click,Query
from sounds.models import Sound,DeletedSound
import sys,traceback
import os
import linecache
import datetime
import numpy
from django.db import connection
from datetime import timedelta


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
    sound=None
    deletedsound=None
    try:
        sound_id=normalized_log.get("sound_id","")
        sound = Sound.objects.get(id=sound_id)
    except Sound.DoesNotExist:
        try:
                deletedsound=DeletedSound.objects.get(sound_id=sound_id)
        except DeletedSound.DoesNotExist:
                deletedsound=DeletedSound(sound_id=sound_id, user_id=795023)
                deletedsound.save()
    click_type=CLICK_TYPES.get(normalized_log.get("click_type",""),"")
    click_datetime=normalized_log.get("datetime", "")
    authenticated_session_key=normalized_log.get("authenticated_session_key","")
    searchtime_session_key=normalized_log.get("searchtime_session_key","")
    
    return Click(sound=sound,click_type=click_type,click_datetime=click_datetime,
                 deletedsound=deletedsound,
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
    
    query_time=normalized_log.get("datetime", "")
    searchtime_session_key=normalized_log.get("searchtime_session_key","")
    query_text=normalized_log.get("q","").replace("+"," ")
    rank_order=normalized_log.get("sound_ids","")
    results_page_no=int(normalized_log.get("current_page",1))
    advanced=normalized_log.get("advanced","")
    a_tag=normalized_log.get("a_tag","")
    a_filename=normalized_log.get("a_filename","")
    a_description=normalized_log.get("a_description","")
    a_packname=normalized_log.get("a_packname","")
    a_soundid=normalized_log.get("a_soundid","")
    a_username=normalized_log.get("a_username","")
    sortby=normalized_log.get("s","").replace("+"," ")
    duration_min=int(normalized_log.get("duration_min",0))
    try:
        duration_max=int(normalized_log.get("duration_max",1000000))
    except ValueError:
        duration_max=1000000
    is_geotagged=normalized_log.get("is_geotagged","")
    group_by_pack=normalized_log.get("g","")
    
    q=Query(query_time=query_time,
            searchtime_session_key=searchtime_session_key,
            query_text=query_text,
            advanced=advanced,
            a_tag=a_tag,
            a_filename=a_filename,
            a_description=a_description,
            a_packname=a_packname,
            a_soundid=a_soundid,
            a_username=a_username,
            sortby=sortby,
            duration_min=duration_min,
            duration_max=duration_max,
            is_geotagged=is_geotagged,
            group_by_pack=group_by_pack,
            rank_order=rank_order,             
            results_page_no=results_page_no)

                
    
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
    from logsparser.lognormalizer import LogNormalizer as LN
    
    if os.path.isdir(dirpath) is False:
        print dirpath + " is not a directory"
    normalizer = LN("/usr/local/lib/python2.7/dist-packages/pylogsparser-0.8-py2.7.egg/share/logsparser/normalizers")
    # Number of non-normalizable logs
    num_unparsed_logs=0
    num_unsaved_logs=0
    counter=input("Enter the index number of the starting line (ie 1 from the beginning)\n")
    unparsedlogs_file = open('unparsed_clickusage.log','a')
    f='clickusage.log'
    
    
    print "Parsing the log file %s"%f
    log = linecache.getline(f, counter)
    while log is not '':
        l = {"raw" : log[:-1]}
        try:
            n = None
            n = normalizer.normalize(l)
        except:
            unparsedlogs_file.write(log)
            num_unparsed_logs+=1
        if n is not None:
            try:
                if "click_type" in n:
                    c = clicklog_to_model(n)
                    c.save()
                else:                           
                    q = querylog_to_model(n)
                    q.save()
            except:
                print "Error in saving the log..."
                print "Index number of the last line successfully parsed and saved: %s"%(counter-1)
                traceback.print_exc(file=sys.stdout)
                print 'closing %s'%unparsedlogs_file
                unparsedlogs_file.close()
                
                sys.exit(0)
        counter+=1
        log = linecache.getline(f, counter)
        if counter%1000 is 0:
            print 'processing the %sth log'%counter
    print 'clearing the linecache'
    linecache.clearcache()
    print 'closing %s'%unparsedlogs_file.name
    unparsedlogs_file.close()
    print "%s logs out of %s couldn't be parsed\n"%(num_unparsed_logs,counter)

def average_query_to_download_deltatime():
    
    d_clicks=Click.objects.filter(click_type='sd').filter(click_datetime__gte=datetime.datetime(2013,04,27,0,0,0,0)).filter(click_datetime__lte=datetime.datetime(2013,4,28,0,0,0,0))
    
    print "processing clicks..."
    lst=[]
    click_count=0
    for click in d_clicks:
        # filter all the queries whose session_key matches the d_clicks session_keys and
        queries=Query.objects.filter(
                                searchtime_session_key=click.searchtime_session_key
                                ).filter(
                                    query_time__lte=click.click_datetime
                                        ).filter(
                                            query_time__gte=(click.click_datetime-datetime.timedelta(hours=1)))
        try:
            if len(queries)>0:
                query_times=[q.query_time for q in queries]
                query_times.sort(reverse=True)
                lst.append(click.click_datetime-query_times[0])
        except IndexError:
            print queries
            print query_times
            sys.exit(0)
        if click_count%10 is 0:
            print '%s download clicks processed so far'%click_count
        click_count+=1
        
        
    return numpy.average([l.total_seconds() for l in lst])


def which_query_for_click(first,last,winsize):
    '''
    For the given click find the latest query whose session_key matches the click's session_key and the clicked sound was present in the results of the query
    '''
    from django.db import transaction
    count=first
    while(count>=first and count<=last):
        with transaction.commit_on_success():
            for click in Click.objects.filter(id__gte=count).filter(id__lt=count+winsize):
                qs = Query.objects.filter(searchtime_session_key=click.searchtime_session_key).filter(
                                            query_time__lte=click.click_datetime).filter(
                                            query_time__gte=(click.click_datetime+timedelta(minutes=-10))).order_by('query_time')
                if len(qs)>0:
                    q=qs[0]
                    click.query=q
                    click.save()
                count+=1
                if count%winsize==0:
                    print '%s clicks so far'%count
                if count>last:
                    break;
                
                
def query_term_counter():
    cursor = connection.cursor()
    cursor.execute("""
        select query_text from clickthrough_query
        """)
    all_queries = cursor.fetchall()
    len_all_queries=len(all_queries)
    num_terms=numpy.zeros(len_all_queries)
    for i in range(len_all_queries):
        query_text=all_queries[i][0] # all_queries contains tuples
        if query_text is not None:
            num_terms[i]=len(query_text.split(" "))
        
    return num_terms,numpy.average(num_terms),numpy.std(num_terms)
    
        
def top_10_most_occuring_queries():
    cursor = connection.cursor()
    cursor.execute("""
    select query_text, count(query_text) from clickthrough_query group by query_text order by count desc limit 20
    """)
    return cursor.fetchall()

def num_queries_with_no_results():
    cursor=connection.cursor()
    cursor.execute("""
        select query_text, count(query_text)
        from clickthrough_query 
        where results_shown='[]'
        group by query_text
        order by count desc
        """)
    
    quries_with_no_results=cursor.fetchall()
    
    
    cursor.execute("""
        select count(*)
        from clickthrough_query 
        where results_shown='[]'
        """)
    total_num_of_queries_with_no_results=cursor.fetchall()
    
    return quries_with_no_results,total_num_of_queries_with_no_results
    
    
def num_preview_clicks_on_SERP():
    
    all_queries = Query.objects.all()[:10000]
    num_previews=numpy.zeros(len(all_queries))
    i=0
    for query in all_queries:
        next_queries=Query.objects.filter(
                            searchtime_session_key=query.searchtime_session_key).filter(
                                query_time__gt=query.query_time).filter(
                            query_time__lt = query.query_time+timedelta(minutes=10)).order_by('query_time')
        if len(next_queries) > 0:
            next_query=next_queries[0]
            clicks=Click.objects.filter(
                                        click_type='sp').filter(
                                            searchtime_session_key = query.searchtime_session_key).filter(
                                            click_datetime__gt = query.query_time).filter(
                                                click_datetime__lt = next_query.query_time)
            num_previews[i]=len(clicks)  
        else:
            num_previews[i]=0
                                      
        i+=1
        if i%1000==0:
            print '%s queries processed'%i
        
                                    
    return num_previews

def num_download_clicks_on_SERP():
    
    all_queries = Query.objects.all()[:10000]
    num_downloads=numpy.zeros(len(all_queries))
    i=0
    for query in all_queries:
        next_queries=Query.objects.filter(
                            searchtime_session_key=query.searchtime_session_key).filter(
                                query_time__gt=query.query_time).filter(
                            query_time__lt = query.query_time+timedelta(minutes=10)).order_by('query_time')
        if len(next_queries) > 0:
            next_query=next_queries[0]
            clicks=Click.objects.filter(
                                        click_type='sd').filter(
                                            searchtime_session_key = query.searchtime_session_key).filter(
                                            click_datetime__gt = query.query_time).filter(
                                                click_datetime__lt = next_query.query_time)
            num_downloads[i]=len(clicks)  
        else:
            num_downloads[i]=0
                                      
        i+=1
        if i%1000==0:
            print '%s queries processed'%i
        
                                    
    return num_downloads
            
    
def length_of_session():
    # from query to the first download
    all_queries = Query.objects.all()[:10000]
    session_lengths=[]
    i=0
    for query in all_queries:
        downloads=Click.objects.filter(
                                    click_type='sd').filter(searchtime_session_key=query.searchtime_session_key).filter(
                                                         click_datetime__gt=query.query_time).filter(
                                                             click_datetime__lt=query.query_time+timedelta(minutes=20)).order_by('click_datetime')
        if len(downloads) > 0:
            first_download=downloads[0]
            session_lengths.append(first_download.click_datetime - query.query_time)
        else:
            session_lengths.append(timedelta(0))
    
        i+=1
        if i%1000==0:
            print '%s queries processed'%i
            
    sum_=timedelta(0)
    non_zero_count=0
    for td in session_lengths:
        sum_+=td
        if td!=timedelta(0):
            non_zero_count+=1
    average_all=sum_.total_seconds()/len(session_lengths)
    average_successful_downloads=sum_.total_seconds()/non_zero_count
        
   
    return average_all,average_successful_downloads
    
