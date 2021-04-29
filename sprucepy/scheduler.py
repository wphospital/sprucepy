import platform
# import winscheduler as ws
import ..linscheduler as ls
import os
import datetime as dt
import click

project_root = '/code'
path = 'runner.py'

system = platform.system()

def task_name(task_id):
    return f'SpruceTask_{task_id}'

def get_next(task_id):
    if system == 'Linux':
        return ls.get_next_run(task_name(task_id))

def get_current_schedule(task_id):
    if system == 'Linux':
        return ls.get_current_schedule(task_name(task_id))

class Scheduler:
    def __init__(
        self,
        task_id,
        user_id,
        target,
        start_dir,
        frequency,
        start_time,
        interval,
        script_args = ''
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.target = target
        self.start_dir = start_dir
        self.frequency = frequency
        self.start_time = start_time
        self.script_args = script_args
        self.interval = interval

    # TODO: get current schedule from cron

    def runner_args(self):
        runner_args = f'{self.target} {self.task_id} {self.user_id} {self.start_dir}'

        if self.script_args:
            runner_args = f'{runner_args} --script_args "{self.script_args}"'

        return runner_args


    def linux_scheduler(self):
        scheduled = ls.create_task(
            name = task_name(self.task_id),
            path = path,
            script_args = self.runner_args(),
            start_in=project_root,
            python_path=None,
            frequency=self.frequency,
            start=self.start_time,
            interval=self.interval
        )

        return scheduled

    def windows_scheduler(self):
        print('Windows not implemented!')
        return False

        # Discontinuing windows because of image build issues
        # scheduled=ws.create_task2(
        #     name=task_name(self.task_id),
        #     path=path,
        #     script_args=self.runner_args(),
        #     start_in=project_root,
        #     python_path=None,
        #     task_trigger=None,
        #     start=self.start_time,
        #     duration=None,
        #     repetition=None
        # )

    def mac_scheduler(self):
        print('Mac not implemented!')
        return False

    def schedule(self):
        if system == 'Windows':
            self.windows_scheduler()
        elif system == 'Linux':
            self.linux_scheduler()
        elif system == 'Darwin':
            self.mac_scheduler()
        else:
            # TODO: Return error that OS is not supported
            pass


# @click.command()
# @click.argument('task_id')
# @click.argument('user_id')
# @click.argument('target')
# @click.argument('start_dir')
# @click.argument('frequency')
# @click.argument('start_time')
# @click.option('--script_args', default=None)
# def main(task_id, user_id, target, start_dir, script_args):
#     scheduler = Scheduler(
#         task_id,
#         user_id,
#         target,
#         start_dir,
#         frequency,
#         start_time,
#         script_args
#     )
#
#     scheduler.schedule()
#
# if __name__ == '__main__':
#     main()
