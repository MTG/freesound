from __future__ import with_statement
from fabric.api import *
from fabric.contrib.files import put, exists
import os

env.user = 'fsweb'
env.roledefs = {'servers': ['hidalgo.s.upf.edu',
                            'xalapa.s.upf.edu',
                            'toluca.s.upf.edu',
                            'pachuca.s.upf.edu'],
                'master': ['cuernavaca.s.upf.edu']}

@roles('servers', 'master')
def deploy():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    put(this_dir, '/home/%s/' % env.user)

@roles('servers')
def start_servers():
    with cd('load_testing'):
        # No need to make the pidfile, as per description below.
        #run('''/sbin/start-stop-daemon \
        #           --start --exec /usr/bin/jmeter-server  --background \
        #           --make-pidfile --pidfile /home/fsweb/jmeter-server.pid''')
        run('/sbin/start-stop-daemon --start --exec /usr/bin/jmeter-server  --background')
        
@roles('servers')
def stop_servers():
    # This doesn't work because the actual jmeter process doesn't have the pid that's saved to the pidfile
    #run('/sbin/start-stop-daemon --stop --pidfile /home/fsweb/jmeter-server.pid')
    run("kill $(ps aux | grep '[J]Meter' | awk '{print $2}')")

@roles('master')
def run_test():
    with cd('load_testing'):
        run('jmeter -rn -p jmeter.properties -t test_plan_2.jmx -l jmeter.jtl')
