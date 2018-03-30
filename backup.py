#!/usr/bin/env python3

import docker
import subprocess
import argparse
from sys import exit
from os import environ

print("-------- Borg Docker Backup --------")
parser = argparse.ArgumentParser(description='Awesome Borg-Backup for Docker made simple!')
#parser.add_argument("action", choices=['backup', 'list'], help="What are we going to do?")

subparsers = parser.add_subparsers(help='Sub-Commands', dest='action')
restore_parser = subparsers.add_parser('restore', help='Restore Container from Backup')
restore_parser.add_argument("archive", help='Archive to Restore container from')

list_parser = subparsers.add_parser('list', help='List archives / files in archive')
list_parser.add_argument("archive", nargs='?', default=None, help='Name of the archive')

backup_parser = subparsers.add_parser('backup', help='Backup all / a single container')
backup_parser.add_argument("container", nargs='?', default=None, help='Name of the Container to backup (default: all)')

info_parser = subparsers.add_parser('info', help="Show infos about repo / archive")
info_parser.add_argument("archive", nargs='?', default=None, help='Archive to show')

args = parser.parse_args()

# Connect to Docker Socket
client = docker.from_env()

# Read Environemtn Configuration
# This should never fail anyways...
my_hostname = environ["HOSTNAME"]

try:
    if environ["BORG_REPO"]:
        pass
except:
    print("ERROR: Environment Variable BORG_REPO must be configured!")
    exit(1)

# Borg INIT options
global borg_init_options
try:
    if environ["BORG_INIT_OPTIONS"]:
        borg_init_options = environ["BORG_INIT_OPTIONS"].split(' ')
except:
    print("Environment variable BORG_INIT_OPTIONS unconfigured.")
    print(" --> Borg will create repositories without encryption!")
    borg_init_options = ['--encryption=none']

try:
    if environ["BORG_CREATE_OPTIONS"]:
        borg_create_options = environ["BORG_CREATE_OPTIONS"].split(' ')
        print("Global BORG_CREATE_OPTIONS: %s" % environ["BORG_CREATE_OPTIONS"])
except:
    print("Environment variable BORG_CREATE_OPTIONS unconfigured.")
    print(" --> Borg will create backups with default settings.")
    borg_create_options = ['--stats']

try:
    if environ["BORG_SKIP_VOLUME_SOURCES"]:
        global_skip_volumes = environ["BORG_SKIP_VOLUME_SOURCES"].split(',')
        print("Global BORG_SKIP_VOLUME_SOURCES: %s" % environ["BORG_SKIP_VOLUME_SOURCES"])
except:
    global_skip_volumes = [ '/proc', '/sys', '/var/run', '/var/cache', '/var/tmp' ]
global_skip_volumes.append('/var/run/docker.sock')

# Will we backup every container? 
# If "False" only backup containers by Label-Config
try:
    if "False" in environ["BORG_BACKUP_ALL"]:
        backup_enabled = False
except:
    backup_enabled = True

class borg:
    def cmd(params):
        command = ["borg"] + params
        proc = subprocess.Popen(command,stdout=subprocess.PIPE)
        for line in proc.stdout:
            print("> %s" % line.rstrip())

    @staticmethod
    def create(options, name, volumes):
        borg.cmd(['create'] + options + ["::" + name + '+{now:%Y-%m-%d_%H:%M}' ] + volumes)

    @staticmethod
    def init(options):
        borg.cmd(['init'] + options)

    @staticmethod
    def list(archive=None):
        options = []
        if archive != None:
            options = ["::" + archive]
        borg.cmd(['list'] + options) 

    @staticmethod
    def restore(archive):
        borg.cmd(["extract", archive]) 

    @staticmethod
    def break_lock():
        borg.cmd(["break-lock"])

    @staticmethod
    def info(archive=None):
        options = []
        if archive != None:
            options = ["::" + archive]
        borg.cmd(['info'] + options) 

# Force Lock-break
# Warning! Only use if BORG_REPO is exclusvily used by this container!
try:
    if not "False" in environ["BORG_BREAK_LOCK"]:
        borg_break_lock()
except:
    borg.break_lock()

def backup(container_name=None):
    borg.init(borg_init_options)

    print("Starting backup of container volumes- this could take a while...")
    for container in client.containers.list():
        if container_name != None and container_name != container.name:
            continue

        # Skip containers on unsupported driver
        # Supported:
        #  - local
        try:
            if not 'local' in container.volume_driver:
                print("Skipping Container '%s', because of unsupported driver '%s'!" % \
                    (container_name, container.volume_driver))
                continue
        except:
            pass

        # FIXME: Skip myself
        # Will use label ATM
        try:
            if 'False' in container.labels["one.gnu.docker.backup"]:
                print("Skipping backup of '%s', because of label configuration!" % name)
                continue
        except:
            pass

        print("---------------------------------------")
        print("Backing up: '%s'..." % container.name)
        print("Volumes:")
        volumes=[]
        for volume_src in container.volumes:
            volume = container.volumes[volume_src]

            # Skip volume by label
            # Syntax: one.gnu.docker.backup.skip: "/mountpoint1, /mountpoint2, ..."
            try:
                if container.labels["one.gnu.docker.backup.skip"]:
                    skip = container.labels["one.gnu.docker.backup.skip"].split(",")
            except:
                skip = []

            if volume["bind"] in skip:
                print(" - '%s' (skipped by label)" % volume["bind"])
                continue

            # FIXME: Skip volume, if not mounted to this container
            if not volume_src in global_skip_volumes:
                volumes.append(volume_src)
                print(" - %s [%s]" % (volume["bind"], volume_src))

            # Borg-Parameters
            #  - From Environment of this container
            #  - Override by Container-Labels
            try:
                if container.labels["one.gnu.docker.backup.options"]:
                    borg_create_options = container.labels["one.gnu.docker.backup.options"]
            except:
                borg_create_options = ['-s', '--progress']

            # Let's do it!
            borg.create(borg_create_options, container.name, volumes)

def list_backups(archive):
    borg.list(archive)

def restore(archive):
    container_name = archive.split('+')[0]

    print(" ----> Starting Restore Of Containter %s" % container_name)
    container = client.containers.get(container_name)

    print(" -> Pausing Container...")
    container.pause()
    
    print(" -> Restoring Archive '%s'..." % archive)
    borg.restore("::" + archive)

    print(" -> Restarting Container...")
    container.restart()

    print("-> Restore Done!")

def info(archive):
    borg.info(archive)

if args.action == "backup":
    backup(args.container)
elif args.action == "list":
    list_backups(args.archive)
elif args.action == "restore":
    restore(args.archive)
elif args.action == "info":
    info(args.archive)

exit(0)
