# TODO: test the built in python mail server:
# python -m smtpd -n -c DebuggingServer localhost:1025 

import asyncore
import smtpd
import socket
import sys

PORT = 2525
HOST = 'localhost'

class FakeServer(smtpd.SMTPServer):
    def __init__(self):
        smtpd.SMTPServer.__init__(self, (HOST, PORT), None)

    def process_message(self, peer, mailfrom, rcpttos, data):
        print "---------------<MAIL>----------------------------------"
        print peer
        print mailfrom
        print rcpttos
        print data
        print "---------------</MAIL>---------------------------------"

if __name__ == "__main__":
    try:
        server = FakeServer()
    except socket.error, e:
        print str(e)
        sys.exit()
        
    print "running fake smtp at", HOST, PORT
    
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print
        sys.exit()
