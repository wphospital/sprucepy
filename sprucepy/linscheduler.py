from crontab import CronTab
from datetime import datetime
import subprocess
import pytz
import time
import re
import pretty_cron
from croniter import croniter


def _get_tz_offset(
    cron_timezone : str = 'UTC',
    target_timezone : str = 'America/New_York'
):
    """
    Calculates the time difference in hours between two timezones.

    Args:
        cron_timezone (str): Timezone name (e.g., 'UTC', 'America/Los_Angeles').
        target_timezone (str): Timezone name (e.g., 'Australia/Sydney').

    Returns:
        float: Time difference in hours between cron_timezone and target_timezone.
    """
    tz1 = pytz.timezone(target_timezone)
    tz2 = pytz.timezone(cron_timezone)

    # Use a fixed datetime to avoid ambiguity
    dt = datetime(2025, 3, 15, 12, 0, 0)  

    dt_tz1 = tz1.localize(dt)
    dt_tz2 = tz2.localize(dt)

    offset_seconds = (dt_tz2 - dt_tz1).total_seconds()
    offset_hours = offset_seconds / 3600

    return int(offset_hours)


def _get_python_path():
    return '/usr/local/bin/python3.9'


def find_job(name):
    c = CronTab(user='root')
    matches = list(c.find_comment(name))

    return matches[0] if len(matches) > 0 else None


def _convert_cron_hour(
    sched,
    cron_timezone : str = 'UTC',
    target_timezone : str = 'America/New_York'
):
    if re.search(re.compile('([A-z0-9/,*]+ ){4}([A-z0-9/,*]+ ?)'), sched):
        TZ_OFFSET = _get_tz_offset(
            cron_timezone=cron_timezone,
            target_timezone=target_timezone
        )

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

        if hour_component + TZ_OFFSET < 0:
            new_hour = (hour_component + 24 + TZ_OFFSET).__str__()
        elif hour_component + TZ_OFFSET > 23:
            new_hour = (hour_component - 24 + TZ_OFFSET).__str__()
        else:
            new_hour = (hour_component + TZ_OFFSET).__str__()

        sched_first = sched[:match.span()[0]]
        sched_last = sched[match.span()[1]:]

        return f'{sched_first} {new_hour} {sched_last}'.replace('  ', ' ')

    return sched


def get_current_schedule(
    name,
    prettify : bool = True,
    cron_timezone : str = 'UTC',
    target_timezone : str = 'America/New_York'
):
    job = find_job(name)

    if job is None:
        return 'Not scheduled'

    sched_pat = re.compile('((?<=@)\w+)|(([A-z0-9/,*]+ ){4}([A-z0-9/,*]+ ?))')

    sched_str = re.search(sched_pat, job.__str__()).group(0).strip()

    if prettify:
        sched_str = _convert_cron_hour(
            sched_str,
            cron_timezone=cron_timezone,
            target_timezone=target_timezone
        )

        return pretty_cron.prettify_cron(sched_str).capitalize()
    else:
        return sched_str.title()


def get_next_run(
    name,
    check_cron_status : bool = False,
    cron_timezone : str = 'UTC',
    target_timezone : str = 'America/New_York'
):
    if check_cron_status:
        # Check if the cron service is running
        res = subprocess.run(
            'service cron status',
            shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if 'failed' in res.stdout.decode():
            return 'Cron is not running!'

    sched = get_current_schedule(
        name,
        prettify=False,
        cron_timezone=cron_timezone,
        target_timezone=target_timezone
    )

    target_now = datetime.now(tz=pytz.timezone(target_timezone))

    if sched and sched != 'Not scheduled':
        if re.search(re.compile('([A-z0-9/,*]+ ){4}([A-z0-9/,*]+ ?)'), sched):
            c = croniter(sched, target_now)
            return c.get_next(datetime).astimezone(
                pytz.timezone(cron_timezone)
            )

        job = find_job(name)

        return job.schedule(date_from=target_now).get_next(datetime)


def remove_job(name):
    job = find_job(name)

    if job:
        with CronTab(user='root') as cron:
            cron.remove(job)


def create_task(
    name,
    task_id,
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

    task = python_path + ' -m ' + 'sprucepy.api execute {}'.format(task_id)

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
