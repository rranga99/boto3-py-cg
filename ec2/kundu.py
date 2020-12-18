import boto3
import botocore
import click
from datetime import datetime
import pytz


session = boto3.Session(profile_name='cguru')
ec2 = session.resource('ec2')


def filter_instances(project):
    instances = []

    if project:
        filters = [{'Name': 'tag:Project', 'Values': [project]}]
        print(filters)
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()

    return instances


def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'


def has_older_snapshot(volume, age):
    IST = pytz.timezone('Asia/Kolkata')

    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'completed' and ((datetime.now(IST).date() - snapshots[0].start_time.date()).days > int(age))


@ click.group()
@ click.option('--profile', default='cguru',
               help="AWS profile to be used for working with EC2 instances")
def cli(profile):
    """kundu manages EC2 snapshots"""
    try:
        session = boto3.Session(profile_name=profile)
    except botocore.exceptions.ProfileNotFound as e:
        print("Unable to use profile {0}. ".format(profile) + str(e) + ".")
        exit(1)
    else:
        ec2 = session.resource('ec2')


@ cli.group('volumes')
def volumes():
    """Commands for volumes"""


@ volumes.command('list')
@ click.option('--project', default=None,
               help="Only volumes for the project (tag Project: <name>)")
@ click.option('--instance', default=None,
               help="Only for a specific instance (Instance ID)")
def list_volumes(project, instance):
    "List EC2 volumes"

    print("Instance provided is {0}". format(instance))
    instances = filter_instances(project)

    for i in instances:
        if (i.id == instance) or (not instance):
            for v in i.volumes.all():
                print(','.join((
                    v.id,
                    i.id,
                    v.state,
                    str(v.size) + 'GiB',
                    v.encrypted and "Encrypted" or "Not Encyprted"
                )))
            if i.id == instance:
                break

    return


@ cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""


@ snapshots.command('list')
@ click.option('--project', default=None,
               help="Only snapshots for the project (tag Project: <name>)")
@ click.option('--all', 'list_all', default=False, is_flag=True,
               help="List all snapshots for each volume, including oldest")
@ click.option('--instance', default=None,
               help="Only snapshots for the instance (InstanceID)")
def list_snapshots(project, list_all, instance):
    "List EC2 snapshots"

    instances = filter_instances(project)

    for i in instances:
        if (i.id == instance) or (not instance):
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

                    if s.state == "completed" and not list_all:
                        break
        if i.id == instance:
            break

    return


@ cli.group('instances')
def instances():
    """Commands for instances"""


@ instances.command('snapshot', help="Create Snapshot of all volumes")
@ click.option('--age', default=None,
               help="Create snapshots only if last snapshot is greater than age (in days)")
@ click.option('--project', default=None,
               help="Only instances for the project (tag Project: <name>)")
@ click.option('--force', "force", default=False, is_flag=True,
               help="Force action when needed for all instances")
def create_snapshots(age, project, force):
    "Create Snapshot for all volumes of an EC2 instance"

    if project:
        instances = filter_instances(project)
    else:
        if force:
            instances = filter_instances(project)
        else:
            print("Project not specificed. Use --force and reissue command.")
            return

    for i in instances:
        wasRunning = False

        for v in i.volumes.all():
            selectedForSnapShot = False

            if has_pending_snapshot(v):
                print("Skipping {0}".format(v.id))
                continue
            elif not has_older_snapshot(v, age):
                print("Skipping {0}".format(v.id))
                continue
            else:
                selectedForSnapshot = True

            if not wasRunning:
                if (selectedForSnapshot) and (i.state['Name'] == 'running'):
                    wasRunning = True
                    i.stop()
                    i.wait_until_stopped()

            print("Creating snapshot of {0}".format(v.id))
            try:
                v.create_snapshot(Description="Created by Kundu")
            except botocore.exceptions.ClientError as e:
                print("Unable to create snapshot for volume {0}. ".format(
                    v.id) + str(e))
                continue

        if wasRunning:
            print("Starting {0}".format(i.id))

            i.start()
            i.wait_until_running()

    print("All done!")

    return


@ instances.command('list')
@ click.option('--project', default=None,
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


@ instances.command('start')
@ click.option('--project', default=None,
               help="Only instances belonging to this project (tag Project: <name>)")
@ click.option('--force', "force", default=False, is_flag=True,
               help="Force action when needed for all instances")
def start_instances(project, force):
    "Start EC2 instances"

    if project:
        instances = filter_instances(project)
    else:
        if force:
            instances = filter_instances(project)
        else:
            print("Project not specificed. Use --force and reissue command.")
            return

    for i in instances:
        print('Starting {}'.format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not start {0}".format(i.id) + str(e))
            continue

    return


@ instances.command('stop')
@ click.option('--project', default=None,
               help="Only instances belonging to this project (tag Project: <name>)")
@ click.option('--force', "force", default=False, is_flag=True,
               help="Force action when needed for all instances")
def stop_instances(project, force):
    "Stop EC2 instances"

    if project:
        instances = filter_instances(project)
    else:
        if force:
            instances = filter_instances(project)
        else:
            print("Project not specificed. Use --force and reissue command.")
            return

    for i in instances:
        print('Stopping {}'.format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not stop {0}".format(i.id) + str(e))
            continue
    return


@ instances.command('reboot')
@ click.option('--project', default=None,
               help="Only instances belonging to this project (tag Project: <name>")
@ click.option('--force', "force", default=False, is_flag=True,
               help="Force action when needed for all instances")
def reboot_instances(project, force):
    "Reboot EC2 instances"

    if project:
        instances = filter_instances(project)
    else:
        if force:
            instances = filter_instances(project)
        else:
            print("Project not specificed. Use --force and reissue command.")
            return

    for i in instances:
        print('Rebooting {0}'.format(i.id))
        try:
            i.reboot()
        except botocore.exceptions.ClientError as e:
            print("Could not reboot{0}".format(i.id) + str(e))
            continue

    return


if __name__ == '__main__':
    cli()
