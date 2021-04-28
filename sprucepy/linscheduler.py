from crontab import CronTab
from datetime import datetime, timezone
import subprocess
import pytz
import time
import re
import pretty_cron
from croniter import croniter

# TODO: calculate this from system timezone
TZ_OFFSET = 4

def _get_python_path():
    return '/usr/local/bin/python3.9'

def find_job(name):
    c = CronTab(user='root')
    matches = list(c.find_comment(name))

    return matches[0] if len(matches) > 0 else None

def _convert_cron_hour(sched):
    if re.search(re.compile('([A-z0-9/,*]+ ){4}([A-z0-9/,*]+ ?)'), sched):
        counter = 0
        for r in re.finditer('[A-z0-9/,*]+ ', sched):
            match = r
            counter += 1
            if counter > 1:
                break

        try:
            hour_component = int(match.group(0).strip())
        except ValueError as err:
            return sched

        if hour_component < TZ_OFFSET:
            new_hour = (hour_component + 24 - TZ_OFFSET).__str__()
        else:
            new_hour = (hour_component - TZ_OFFSET).__str__()

        sched_first = sched[:match.span()[0]]
        sched_last = sched[match.span()[1]:]

        return f'{sched_first} {new_hour} {sched_last}'.replace('  ', ' ')

    return sched

def get_current_schedule(name, prettify = True):
    job = find_job(name)

    if job is None:
         return 'Not scheduled'

    sched_pat = re.compile('((?<=@)\w+)|(([A-z0-9/,*]+ ){4}([A-z0-9/,*]+ ?))')

    sched_str = re.search(sched_pat, job.__str__()).group(0).strip()

    if prettify:
        sched_str = _convert_cron_hour(sched_str)

        return pretty_cron.prettify_cron(sched_str).capitalize()
    else:
        return sched_str.title()

def get_next_run(name):
    # Check if the cron service is running
    res = subprocess.run(
        'service cron status',
        shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if 'failed' in res.stdout.decode():
        return 'Cron is not running!'

    sched = get_current_schedule(name, prettify = False)

    utc_now = datetime.now(tz=timezone.utc)

    if sched and sched != 'Not scheduled':
        if re.search(re.compile('([A-z0-9/,*]+ ){4}([A-z0-9/,*]+ ?)'), sched):
            c = croniter(sched, utc_now)
            return c.get_next(datetime).replace(tzinfo=timezone.utc)

        job = find_job(name)

        return job.schedule(date_from=utc_now).get_next(datetime)

    return

def remove_job(name):
    job = find_job(name)

    if job:
        with CronTab(user='root') as cron:
            cron.remove(job)

def create_task(
    name,
    path,
    script_args = None,
    start_in = None,
    python_path=None,
    frequency=None,
    start=None,
    interval=None
):
    if python_path is None:
        python_path = _get_python_path()

    # Remove the job if it exists
    remove_job(name)

    if frequency is None:
        return

    # Combine task and arguments
    task = 'cd ' + start_in + \
        ' && ' + \
        python_path + ' ' \
        + path + ' ' + \
        script_args if script_args else None

    with CronTab(user='root') as cron:
        # Check if a job for this task already exists
        m = list(cron.find_comment(name))
        job = m[0] if len(m) > 0 else cron.new(command=task, comment=name)

        # Clear any previous restrictions
        job.clear()

        # Set the job's frequency
        if frequency == 'minutely':
            job.minute.every(interval)
        elif frequency == 'hourly':
            job.hour.every(interval)
            job.minute.on(0)
        elif frequency == 'daily':
            job.day.every(interval)
        elif frequency == 'monthly':
            job.month.every(interval)

        # Set the job's start time
        if start:
            if frequency not in ['hourly', 'minutely']:
                job.hour.on(start.hour)
                job.minute.on(start.minute)

            if frequency == 'hourly':
                job.minute.on(start.minute)
            if frequency == 'weekly':
                job.dow.on(start.weekday() + 1)
            if frequency == 'monthly':
                job.day.on(start.day)
        else:
            if frequency == 'weekly':
                job.dow.on(0)
            if frequency == 'monthly':
                job.day.on(1)

            if frequency not in ['hourly', 'minutely']:
                job.hour.on(0)
                job.minute.on(0)
