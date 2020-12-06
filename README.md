# boto3-py-cg
First Real world Python Project with Cloud Guru

#About

This project is use boto3 to manage AWS EC2 instance snapshots.

#Configuring

Kundu uses the configuration created by AWS CLI. e.g.

`aws configure --profile cguru`

#Running

`pipenv run python ec2/kundu.py <command> <sub-command>
<--project=PROJECT>`

*command* is instances, volumes or snapshots
*subcommand* depends on command
        is list, start, stop or snapshot for instances
        is list for volumes
        is list for snapshots
*project* is optional
    

