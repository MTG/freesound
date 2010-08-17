from __future__ import with_statement
from fabric.api import env, run, cd

env.hosts = ["fsweb@tabasco.upf.edu"]

def syncdb():
    """run syncdb remotely"""
    with cd("freesound/freesound"):
        run("source /home/fsweb/.virtualenvs/freesound/bin/activate && python manage.py syncdb")

def stop():
    """Stop FastCGI"""
    run("sudo supervisorctl stop freesound")
    
def start():
    """Start FastCGI"""
    run("sudo supervisorctl start freesound")
    
def restart():
    """Restart FastCGI"""
    run("sudo supervisorctl restart freesound")
    
def pull():
    """Get latest version from Github"""
    with cd("freesound"):
        run("git pull origin master")

def deploy():
    """pull and restart"""
    pull()
    restart()
