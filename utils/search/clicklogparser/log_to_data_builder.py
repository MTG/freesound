
"""
	- Script for parsing through clickusage log files and adding entries in the
	click and query tables extracted for each log enry.
	- Assumptions:
		- all the log files are in the current directory ('./')
		- all the log file names start with 'clickusage.log'
		- the path to normalizer definitions is '/usr/local/lib/python2.7/dist-packages/pylogsparser-0.8-py2.7.egg/share/logsparser/normalizers'

"""
import os
from logsparser.lognormalizer import LogNormalizer as LN
from sounds.models import Sound, Click

def clicklog_to_model(normalized_log):

	CLICK_TYPES = {'soundpreview':'sp',
				   'sounddownload' : 'sd',
				   'packdownload' : 'pd'}
	
	# Distribute parsed fields
	sound = Sound.objects.get(id=normalized_log.get("sound_id",""))
	click_type=CLICK_TYPES.get(normalized_log.get("click_type",""),"")
	click_datetime=normalized_log.get("date", "")
	authenticated_session_key=normalized_log.get("authenticated_session_key","")
	searchtime_session_key=normalized_log.get("searchtime_session_key","")
    
	c = Click(sound=sound,click_type=click_type,click_datetime=click_datetime,authenticated_session_key=authenticated_session_key,searchtime_session_key=searchtime_session_key)
		  	

normalizer = LN("/usr/local/lib/python2.7/dist-packages/pylogsparser-0.8-py2.7.egg/share/logsparser/normalizers")
for root, dirs, filenames in os.walk('./'):
    for f in filenames:
		if f.startswith('clickusage.log'):
			logs = open(f,'r')
	
			print "Parsing the log file ..."
	
			for log in logs:
				l = {"raw" : log}
				n = normalizer.normalize(l)
		
				if "click_type" in n:
					print "saving click_type"
#						c = clicklog_to_model(n)
#						c.save()
				else:	
					print "TODO: SAVING QUERY LOGS"
		




	
	
