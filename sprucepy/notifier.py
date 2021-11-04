import requests
import os
import mimetypes
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from urllib.parse import urljoin
from .constants import api_url

from sprucepy.secrets import get_secret_by_key
import boto3

notification_ept = 'notifications'
recipient_ept = 'recipients'


def get_recipients(task_id, category, api_url=api_url):
    # Get the list to notify from the task
    ept = urljoin(api_url, recipient_ept)

    payload = dict(
        task_id=task_id,
        category=category
    )

    r = requests.get(ept, params=payload)

    return r.json()


def get_recipient_emails(recipient_list=None, task_id=None, category=None, api_url=api_url):
    if recipient_list is None:
        recipient_list = get_recipients(task_id, category, api_url)

    # Get the emails as a dict with structure
    # send_line: [(id, email)], as needed for the Email class
    emails = dict(to=[], cc=[], bcc=[])

    for d in recipient_list:
        if d['mode'] == 'email' and d['email'] and (d['task_testing'] == d['send_testing'] or not d['task_testing']):
            emails[d['send_line']].append((d['person'], d['email']))

    return emails


def get_recipient_phones(recipient_list=None, task_id=None, category=None, api_url=api_url):
    if recipient_list is None:
        recipient_list = get_recipients(task_id, category, api_url=api_url)

    # Get the phones as a dict with structure
    # send_line: [(id, phone)], as needed for the SMS class
    phones = []

    for d in recipient_list:
        if d['mode'] == 'sms' and d['phone']:
            phones.append((d['person'], d['phone']))

    return phones


def get_recipient_attrs(attr, recipient_list=None, task_id=None, category=None, api_url=api_url):
    if recipient_list is None:
        recipient_list = get_recipients(task_id, category, api_url=api_url)

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
        server='SMTPRelay.montefiore.org'
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

    def build_and_send(self, api_url=api_url, standalone=False):
        self.build_email()
        self.send_email(api_url=api_url, standalone=standalone)

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
                    pretty_filename = os.path.basename(a)
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

    def send_email(self, msg=None, api_url=api_url, standalone=False):
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
                        if not standalone:
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
                        if not standalone:
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


class SMS:
    def __init__(
        self,
        recipients,
        body,
        sms_broker='aws',
        run=None,
        category='output',
        object='task',
    ):
        self.sms_broker = sms_broker
        self.recipients = recipients
        self.msg = body
        self.run = run
        self.category = category
        self.object = object
        self.mode = 'sms'

    def send(self):
        if self.sms_broker == 'aws':
            self.send_sms_aws()

    def send_sms_aws(self, msg=None):
        if msg is None:
            msg = self.msg

        ept = urljoin(api_url, notification_ept)
        # Send a POST to the API recording the send
        for sendto in set(self.recipients):
            payload = dict(
                run=self.run,
                person=sendto[0],
                category=self.category,
                object=self.object,
                mode=self.mode,
                body=self.msg,
                return_code=0
            )

        requests.post(ept, data=payload)

        aws_access_key_id = get_secret_by_key(
            'aws_access_key_id', api_url='http://10.16.8.20:1592/api/v1/')
        aws_secret_access_key = get_secret_by_key(
            'aws_secret_access_key', api_url='http://10.16.8.20:1592/api/v1/')

        # Create an SNS client
        client = boto3.client(
            "sns",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name="us-east-1"
        )

        # Send your sms message.
        for recipient in self.recipients:
            print(recipient[1])
            client.publish(
                PhoneNumber="+1{}".format(recipient[1]),
                Message=self.msg
            )
