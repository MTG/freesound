import asyncore
import smtpd
import socket
import sys

class FakeServer(smtpd.SMTPServer):
    def __init__(self):
        smtpd.SMTPServer.__init__(self, ("localhost", 2525), None)

    def process_message(self, peer, mailfrom, rcpttos, data):
        print "---------------<MAIL>----------------------------------"
        print rcpttos
        print data
        print "---------------</MAIL>---------------------------------"

if __name__ == "__main__":
    try:
        server = FakeServer()
    except socket.error, e:
        print str(e)
        sys.exit()
        
    print "running fake smtp"
    
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print
        sys.exit()