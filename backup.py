#!/usr/bin/env python3

import docker
import subprocess
import argparse
from sys import exit
from os import environ

parser = argparse.ArgumentParser(description='Awesome Borg-Backup for Docker made simple!')
parser.add_argument("action", choices=['backup', 'list', 'restore'], help="What are we going to do?")
parser.add_argument("container")
parser.add_argument("archive")

args = parser.parse_args()

# Connect to Docker Socket
client = docker.from_env()

# Read Environemtn Configuration
# This should never fail anyways...
my_hostname = environ["HOSTNAME"]

try:
    if environ["BORG_BACKUP_REPOSITORY"]:
        borg_repository = environ["BORG_BACKUP_REPOSITORY"]
except:
    print("ERROR: Environment Variable BORG_BACKUP_REPOSITORY must be configured!")
    exit(1)

# Borg INIT options
try:
    if environ["BORG_INIT_OPTIONS"]:
        borg_init_options = environ["BORG_INIT_OPTIONS"].split(' ')
except:
    print("Environment variable BORG_INIT_OPTIONS unconfigured.")
    print(" --> Borg will create repositories without encryption!")
    borg_init_options = ['--encryption=none', borg_repository]

try:
    if environ["BORG_CREATE_OPTIONS"]:
        borg_create_options = environ["BORG_CREATE_OPTIONS"].split(' ')
        print("Global BORG_CREATE_OPTIONS: %s" % environ["BORG_CREATE_OPTIONS"])
except:
    print("Environment variable BORG_CREATE_OPTIONS unconfigured.")
    print(" --> Borg will create backups with default settings.")
    borg_create_options = ['--json']

# Will we backup every container? 
# If "False" only backup containers by Label-Config
try:
    if "False" in environ["BORG_BACKUP_ALL"]:
        backup_enabled = False
except:
    backup_enabled = True




def borg(params):
    command = ["borg"] + params
    proc = subprocess.Popen(command,stdout=subprocess.PIPE)
    for line in proc.stdout:
        print("[borg]> %s" % line.rstrip())

def borg_create(options, repository, name, volumes):
    borg(['create'] + options + ["%s::%s-{now}" %(repository, name)] + volumes)

def borg_init(options):
    borg(['init'] + options)

def borg_list(repository, options=[]):
    borg(['list'] + repository) 

def borg_restore(archive):
    borg(["extract", borg_repository + "::" + archive]) 

print("-------- Borg Docker Backup --------")

def backup():
    borg_init(borg_init_options)

    print("Starting backup of container volumes- this could take a while...")
    for container in client.containers():
        name = container["Names"][0].replace('/', '')
        '''
         "Mounts": [
             {
                "Source": "/var/lib/docker/volumes/82ef....04bce232a854ff82e8c/_data",
                "Type": "volume",
                "Name": "82ef89dd1dec09f4e699d83b396184ca1beceba41b40c04bce232a854ff82e8c",
                "Propagation": "",
                "Mode": "rw",
                "RW": true,
                "Destination": "/var/spool/squid3",
                "Driver": "local"
             }
             "labels": {"label1": "value1", "label2": "value2"}
        '''

        # FIXME: Skip myself
        # Will use label ATM

        try:
            if container["Labels"]["one.gnu.docker.backup"] == "False":
                print("Skipping backup of '%s', because of label configuration!" % name)
                continue
        except:
            pass

        print("Backing up: '%s'..." % name)
        print("Volumes:")
        volumes=[]
        for volume in container["Mounts"]:
            # Skip volume by label
            # Syntax: one.gnu.docker.backup.skip: "/mountpoint1, /mountpoint2, ..."
            try:
                if container["Labels"]["one.gnu.docker.backup.skip"]:
                    skip = container["Labels"]["one.gnu.docker.backup.skip"].split(",")
            except:
                skip = []

            if volume["Destination"] in skip:
                print("Skipping Volume '%s', because of label configuration!" % volume["Destination"])
                continue

            # Skip volume on unsupported driver
            # Supported:
            #  - local
            try:
                if volume["Driver"] != "local":
                    print("Skipping Volume '%s', because of unsupported driver '%s'!" % \
                        (volume["Destination"], volume["Driver"]))
                    continue
            except:
                pass


            # FIXME: Skip volume, if not mounted to this container
            volumes.append(volume["Source"])
            print(" - %s [%s]" % (volume["Destination"], volume["Source"]))

            # Borg-Parameters
            #  - From Environment of this container
            #  - Override by Container-Labels
            try:
                if container["Labels"]["one.gnu.docker.backup.options"]:
                    borg_create_options = container["Labels"]["one.gnu.docker.backup.options"]
            except:
                pass

            # Let's do it!
            borg_create(borg_create_options, borg_repository, name, volumes)

def list_backups():
    borg_list([borg_repository])


def restore(container, timestamp):
#    container = client.containers.get(container)
#    container.pause()
    borg_restore(container + "-" + timestamp)
#    container.restart()

if args.action == "backup":
    backup()
elif args.action == "list":
    list_backups()
elif args.action == "restore":
    restore(args.container, args.archive)

exit(0)
