from __future__ import with_statement
from fabric.api import env, run, cd, sudo

env.hosts = ["fsweb@tabasco.upf.edu"]

def clearpyc():
    """run syncdb remotely"""
    with cd("freesound/freesound"):
        run("find . -name \"*.pyc\" -exec rm '{}' ';'")

def make_stereofy():
    pull()
    with cd("freesound/sandbox/legacy/stereofy/"):
        run("make clean")
        run("make")

def syncdb():
    """run syncdb remotely"""
    with cd("freesound/freesound"):
        run("source /home/fsweb/.virtualenvs/freesound/bin/activate && python manage.py syncdb")

def stop():
    """Stop FastCGI"""
    sudo("supervisorctl stop freesound", shell=False)
    
def start():
    """Start FastCGI"""
    sudo("supervisorctl start freesound", shell=False)
    
def restart():
    """Restart FastCGI"""
    sudo("supervisorctl restart freesound", shell=False)
    
def pull():
    """Get latest version from Github"""
    with cd("freesound"):
        run("git pull origin master")

def deploy():
    """pull and restart"""
    pull()
    make_stereofy()
    clearpyc()
    restart()
