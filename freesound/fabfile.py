# fabfile.py
from fabric.api import run

def stop():
    """Stop FastCGI"""
    run('''sudo supervisorctl stop freesound''')
    
def start():
    """Start FastCGI"""
    run('''sudo supervisorctl start freesound''')
    
def restart():
    """Restart FastCGI"""
    run('''sudo supervisorctl restart freesound''')
    
def deploy():
    """Get latest version from Github and restart."""
    run('''cd freesound/ && git pull''')
    restart()
    
    
    