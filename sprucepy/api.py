import requests
import click

spruce_api = 'https://localhost:1592/api/v1/'
execute_ept = 'execute/{}'


def run_from_api(task_id):
    requests.get(spruce_api + execute_ept.format(task_id))


@click.command()
@click.argument('endpoint')
@click.argument('task_id')
def main(endpoint, task_id):
    """Hit Spruce api endpoints
    """

    if endpoint == 'execute':
        run_from_api(task_id)


if __name__ == '__main__':
    main()
