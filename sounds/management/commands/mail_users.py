from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
import smtplib, json, sys
from email.mime.text import MIMEText, MIMEMultipart
from django.template import loader, Context


class Command(BaseCommand):
    """Send an email to the users specified in a JSON file.
    """
    help = '''Send an email to the users specified in a JSON file.'''
    args = '''[<foshizzle> <input>]'''

    option_list = BaseCommand.option_list + (
        make_option('--foshizzle', action='store_true', dest='foshizzle', default=False,
                    help="Don't do a dry-run and actually send the messages."),
        make_option('--input', action='store', dest='input', default='/tmp/relevant_users.json',
                    help='Load users to send emails to from this file.'),
        make_option('--template', action='store', dest='template', default=False,
                    help='Use this template to render the message body.'),
        make_option('--subject', action='store', dest='subject', default=False,
                    help='Use this subject line for the emails.'),
        make_option('--from', action='store', dest='from', default='noreply@freesound.org',
                    help='Use this email address as the sender.'),
    )

    def handle(self, *args, **options):

        if not options['template'] \
           or not options['subject']:
            self.stdout.write('ERROR: Please provide a template name to render the email text and a subject line.')
            self.stdout.flush()
            sys.exit(1)

        with open(options['input'], mode='r') as f:
            users = json.load(f)

        if options['foshizzle']:
            s = smtplib.SMTP('localhost')

        t = loader.get_template(options['template'])

        for user in users:
            c = Context(user)
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(t.render(c), 'html'))
            msg.attach(MIMEText('''Hi there,

We wanted to send you an email, but it appears your email client does not support HTML.
If you would still like to read this email try to open it in another client. Otherwise
please ignore this message.

Our apologies,

The Freesound team
''', 'plain'))
            msg['Subject'] = options['subject']
            msg['From'] = options['from']
            msg['To'] = user['email']
            if options['foshizzle']:
                s.sendmail(options['from'], [user['email']], msg.as_string())
            else:
                print msg.as_string()

        if options['foshizzle']:
            s.quit()

