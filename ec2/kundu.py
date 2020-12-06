import boto3
import botocore
import click

session = boto3.Session(profile_name='cguru')
ec2 = session.resource('ec2')


def filter_instances(project):
    instances = []

    if project:
        filters = [{'Name': 'tag:Project', 'Values': [project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()

    return instances


@click.group()
def cli():
    """kundu manages EC2 snapshots"""


@cli.group('volumes')
def volumes():
    """Commands for volumes"""


@volumes.command('list')
@click.option('--project', default=None,
              help="Only volumes for the project (tag Project: <name>)")
def list_volumes(project):
    "List EC2 volumes"

    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            print(','.join((
                v.id,
                i.id,
                v.state,
                str(v.size) + 'GiB',
                v.encrypted and "Encrypted" or "Not Encyprted"
            )))

    return


@cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""


@snapshots.command('list')
@click.option('--project', default=None,
              help="Only snapshots for the project (tag Project: <name>)")
def list_snapshots(project):
    "List EC2 snapshots"

    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(','.join((
                    s.id,
                    i.id,
                    v.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c")
                )))

    return


@cli.group('instances')
def instances():
    """Commands for instances"""


@instances.command('snapshot', help="Create Snapshot of all volumes")
@click.option('--project', default=None,
              help="Only instances for the project (tag Project: <name>)")
def create_snapshots(project):
    "Create Snapshot for all volumes of an EC2 instance"

    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            i.stop()
            i.wait_until_stopped()
            print("Creating snapshot of {0}".format(v.id))
            v.create_snapshot(Description="Created by Kundu")
        print("Starting {0}".format(i.id))

        i.start()
        i.wait_until_running()

    print("All done!")

    return


@instances.command('list')
@click.option('--project', default=None,
              help="Only instances for the project (tag Project: <name>)")
def list_instances(project):
    "List EC2 instances"

    instances = filter_instances(project)

    for i in instances:
        tags = {t['Key']: t['Value'] for t in i.tags or []}
        print(','.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name,
            tags.get('Project', '<no project>')
        )))

    return


@instances.command('start')
@click.option('--project', default=None,
              help="Only instances belonging to this project (tag Project: <name>)")
def start_instances(project):
    "Start EC2 instances"

    instances = instances = filter_instances(project)

    for i in instances:
        print('Starting {}'.format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not start {0}".format(i.id) + str(e))
            continue

    return


@instances.command('stop')
@click.option('--project', default=None,
              help="Only instances belonging to this project (tag Project: <name>)")
def start_instances(project):
    "Stop EC2 instances"

    instances = filter_instances(project)

    for i in instances:
        print('Stopping {}'.format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not stop {0}".format(i.id) + str(e))
            continue
    return


if __name__ == '__main__':
    cli()
