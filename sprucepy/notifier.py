import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import mimetypes
from urllib.parse import urljoin
import requests

api_url = 'http://localhost:1592/api/v1/'
notification_ept = 'notifications'
recipient_ept = 'recipients'


def get_recipients(task_id, category):
    # Get the list to notify from the task
    ept = urljoin(api_url, recipient_ept)

    payload = dict(
        task_id=task_id,
        category=category
    )

    r = requests.get(ept, params=payload)

    return r.json()


def get_recipient_emails(recipient_list=None, task_id=None, category=None):
    if recipient_list is None:
        recipient_list = get_recipients(task_id, category)

    # Get the emails as a dict with structure
    # send_line: [(id, email)], as needed for the Email class
    emails = dict(to=[], cc=[], bcc=[])

    for d in recipient_list:
        if d['mode'] == 'email' and d['email']:
            emails[d['send_line']].append((d['person'], d['email']))

    return emails


def get_recipient_attrs(attr, recipient_list=None, task_id=None, category=None):
    if recipient_list is None:
        recipient_list = get_recipients(task_id, category)

    # Get the attributes as (id, attr) tuples
    attrs = [(d['person'], d[attr]) for d in recipient_list]

    return attrs


class Email:
    def __init__(
        self,
        recipients,
        body,
        from_email='noreply@wphospital.org',
        subject='Automated Email',
        body_type='html',
        attachment=None,
        run=None,
        category='output',
        object='task',
        server='smtp.stellarishealth.net'
    ):
        self.attachment = attachment
        self.email_list = recipients['to']
        self.cc_email_list = recipients['cc']
        self.bcc_email_list = recipients['bcc']
        self.body_type = body_type
        self.subject = subject
        self.body_text = body
        self.from_email = from_email
        self.run = run
        self.category = category
        self.object = object
        self.mode = 'email'
        self.server = server

        self.build_email()

    def build_and_send(self):
        self.build_email()
        self.send_email()

    def build_email(self):
        subject = self.subject
        attachment = self.attachment

        if '[Data Bot]' not in subject:
            subject = '[Data Bot] ' + subject

        msg = MIMEMultipart('related')
        msg['From'] = self.from_email
        msg['To'] = '; '.join([e[1] for e in self.email_list])
        msg['Cc'] = '; '.join([e[1] for e in self.cc_email_list])
        msg['Bcc'] = '; '.join([e[1] for e in self.bcc_email_list])
        msg['Subject'] = self.subject
        msg.attach(MIMEText(self.body_text, self.body_type))

        if attachment is not None:
            attachment = [attachment] if type(
                attachment) != list else attachment

            for a in attachment:
                try:
                    pretty_filename = a.split('\\')[-1]
                except:
                    pretty_filename = a

                with open(a, "rb") as att:
                    # Add file as application/octet-stream
                    # Email client can usually download this automatically as attachment
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(att.read())

                # Encode file in ASCII characters to send by email
                encoders.encode_base64(part)

                # Add header as key/value pair to attachment part
                part.add_header(
                    "Content-Disposition",
                    "attachment; filename= {}".format(pretty_filename),
                )

                # Add attachment to message and convert message to string
                msg.attach(part)

        self.msg = msg

    def send_email(self, msg=None):
        if msg is None:
            msg = self.msg

        ept = urljoin(api_url, notification_ept)

        try:
            with smtplib.SMTP(self.server) as server:
                for sendto in set(self.email_list) | set(self.cc_email_list) | set(self.bcc_email_list):
                    try:
                        # Send the email to this specific email address
                        server.sendmail(self.from_email,
                                        sendto[1], msg.as_string())

                        # Send a POST to the API recording the send
                        payload = dict(
                            run=self.run,
                            person=sendto[0],
                            category=self.category,
                            object=self.object,
                            mode=self.mode,
                            body=self.body_text,
                            return_code=0
                        )

                        requests.post(ept, data=payload)

                    except Exception as e:
                        # Send a POST to the API recording the error
                        payload = dict(
                            run=self.run,
                            person=sendto[0],
                            category=self.category,
                            object=self.object,
                            mode=self.mode,
                            body=self.body_text,
                            return_code=1,
                            error_text=e
                        )

                        requests.post(ept, data=payload)
        except Exception as e:
            for sendto in self.email_list:
                # Send a POST to the API recording the error
                payload = dict(
                    run=self.run,
                    person=sendto[0],
                    category=self.category,
                    object=self.object,
                    mode=self.mode,
                    body=self.body_text,
                    return_code=1,
                    error_text=e
                )

                requests.post(ept, data=payload)
