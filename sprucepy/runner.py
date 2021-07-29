#import yaml
import subprocess
from subprocess import PIPE
from subprocess import CompletedProcess
import threading
import time
import os
import requests
import click
from urllib.parse import urljoin
from datetime import datetime, timezone
import pytz
from .constants import api_url, app_url

from .notifier import Email, get_recipient_emails, get_recipients, get_recipient_phones, SMS

run_ept = 'runs'
recipient_ept = 'recipients'
task_ept = 'tasks'

DEFAULT_USER = 1


class Runner:
    def __init__(self, **kwargs):
        self.target = kwargs.get('target')
        self.task_id = kwargs.get('task_id')
        self.user = kwargs.get('user', DEFAULT_USER)
        self.start_dir = kwargs.get('start_dir', os.getcwd())
        self.script_args = kwargs.get('script_args')
        self.status_running = False

        self.valid = os.path.exists(os.path.join(self.start_dir, self.target))

        # TODO make a config file for extensions
        self.ext = os.path.splitext(
            self.target)[-1] if os.path.splitext(self.target)[-1] in ['.py', '.R'] else None

    def validate_path(self, path, target):
        pass

    def heartbeat(self, frequency=10):
        """Sends a heartbeat while running

        Args:
            frequency (int, optional): [description]. Defaults to 10.
        """

        ept = urljoin(api_url, run_ept) + '/' + self.run_id.__str__()
        while self.status_running == True:
            payload = dict(
                heartbeat=datetime.now(timezone.utc)
            )
            requests.patch(ept, data=payload)
            time.sleep(frequency)

    def start_heartbeat(self, frequency=10):
        """Send a heartbeat to the API

        Args:
            frequency (int, optional): number of seconds between heartbeats. Defaults to 10.
        """

        sub_env = os.environ.copy()
        sub_env['TASK_ID'] = self.task_id.__str__()
        sub_env['RUN_ID'] = self.run_id.__str__()

        threadname = 'heartbeat_run_{}'.format(self.run_id.__str__())
        thread = threading.Thread(
            name=threadname, target=self.heartbeat)
        thread.start()

    def _get_python_path(self):
        return '/usr/local/bin/python3.9'

    def custom_error(self, returncode, error):
        return CompletedProcess(args=[], returncode=returncode, stderr=error)

    # Create the Spruce Run
    def create_run(self):
        """Creates a new run from Spruce API and sets the class variable run ID
        """

        ept = urljoin(api_url, run_ept)

        self.run_start = datetime.now(timezone.utc)

        data = dict(
            task=self.task_id,
            start_time=self.run_start,
            created_by=self.user,
            status='in progress'
        )

        r = requests.post(ept, data=data)
        # set status to running
        self.status_running = True
        self.run_id = r.json()['id']
        self.start_heartbeat()

    # Complete the run
    def complete_run(self, res):
        """Kicks off failure notification if necessary and sends a PATCH
        to Spruce API with the run status and end time
        """

        # TODO: change API to query params like Recipients??
        ept = urljoin(api_url, run_ept) + '/' + self.run_id.__str__()

        status = 'fail' if res.returncode > 0 else 'success'

        if status == 'fail':
            self.notify_failure(res)

        error = res.stderr
        output = res.stdout

        payload = dict(
            end_time=datetime.now(timezone.utc),
            status=status,
            error_text=error,
            output_text=output,
            return_code=res.returncode,
        )
        self.status_running = False
        requests.patch(ept, data=payload)

    def notify_failure(self, res):
        """In the event of a run failure, retrieves a list of individuals
        subscribed to receive error notifications and sends via the
        relevant modes (email or SMS)
        """

        recipient_list = get_recipients(self.task_id, 'error')
        emails = get_recipient_emails(recipient_list)
        #phones = get_recipient_phones(recipient_list)

        # If there are no recipients, do nothing
        if len(recipient_list) == 0:
            return

        # Get the phones as (id, phone) tuples needed for the SMS class
        phones = [(d['person'], d['phone'])
                  for d in recipient_list if d['mode'] == 'sms']

        # Retrieves the error message template
        with open('templates/error_email.html', 'r') as file:
            template = file.read()

        # Task and run metadata
        task_title = recipient_list[0]['task_name']
        run_start = self.run_start.astimezone(pytz.timezone(
            'America/New_York')).strftime('%m/%d/%Y %H:%M:%S')

        # Formats the error message template with run-specific strings
        run_url = urljoin(app_url, 'tasks/runs/') + self.run_id.__str__()
        task_url = urljoin(app_url, 'tasks/') + self.task_id.__str__()
        body = template.format(
            run_url=run_url,
            task_url=task_url,
            task=task_title,
            task_start_time=run_start,
            error=res.stderr.decode('ascii').replace('\n', '<br>')
        )

        sms_body = "Spruce Error in {task}: {task_url}: {run_url}. {task_start_time}".format(
            task=task_title, run_url=run_url, task_url=task_url, task_start_time=run_start)

        # Send emails via the Email class in notifier module
        e = Email(
            recipients=emails,
            body=body,
            from_email='noreply@wphospital.org',
            subject='Run Failure',
            run=self.run_id,
            category='error',
            object='task'
        ).build_and_send()

        # Send texts
        try:
            t = SMS(
                recipients=phones,
                body=sms_body,
                sms_broker='aws',
                run=self.run_id,
                category='error',
                object='task').send()
        except:
            txt_error = Email(
                recipients=emails,
                body="SMS Failed to Send on Error",
                from_email='noreply@wphospital.org',
                subject='Notifcation Failure',
                run=self.run_id,
                category='error',
                object='task'
            ).build_and_send()

    # Run the target script
    def run(self):
        """Runs the script and communicates run info to Spruce API
        """

        # POST new run to API
        self.create_run()

        # Get the interpreter from the file extension
        # TODO: this should work off the config file (see above)
        if self.ext == '.py':
            interpreter = self._get_python_path()
        elif self.ext == '.R':
            interpreter = 'RScript'
        elif self.ext == None:
            res = self.custom_error(
                returncode=99, error=b"Check your Spruce Task administrator. The script file type is not supported.")
            self.complete_run(res)
            return

        if interpreter == '':
            res = self.custom_error(
                returncode=99, error=b"The scheduler could not locate a Python path")
            self.complete_run(res)
            return

        full_target = f'{self.target} {self.script_args}' if self.script_args else self.target

        sub_env = os.environ.copy()
        sub_env['TASK_ID'] = self.task_id.__str__()
        sub_env['RUN_ID'] = self.run_id.__str__()

        res = subprocess.run('cd {} && {} {}'.format(self.start_dir, interpreter, full_target),
                             stdout=PIPE, stderr=PIPE, shell=True, env=sub_env)

        # os.chdir(original_dir)
        self.complete_run(res)


@click.command()
@click.argument('target')
@click.argument('task_id')
@click.argument('user')
@click.argument('start_dir')
@click.option('--script_args', default=None)
def main(target, task_id, user, start_dir, script_args):
    """Run an arbitrary task in an arbitrary place and tell Spruce about it

    TARGET is the filename (with extension) of the script to run
    TASK_ID is the ID of the task this run is associated with
    USER is the Spruce user ID who kicked off this run
    START_DIR is the working directory containing the script to run
    SCRIPT_ARGS is a single string with any arguments to pass to the script
    """

    runner = Runner(
        target=target,  # target is script to run
        task_id=task_id,
        user=user,
        start_dir=start_dir,  # start_dir is project directory
        script_args=script_args
    )

    result = runner.run()


if __name__ == '__main__':
    main()
