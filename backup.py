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

borg_parser = subparsers.add_parser('borg', help="Run every board-command you like")
borg_parser.add_argument("borg", nargs='+', default=None, help='Borg Parameters')

args = parser.parse_args()

###
# Global configuration class
class Config:
    # Default values
    excludes = []
    create_options = ['--stats']
    init_options = ['--encryption=none']
    backup_enabled = True
    break_lock = True
    hostname = ""

    # Connect to Docker Socket
    client = docker.from_env()

    # Read Environment Configuration
    def __init__(self):
        # This should never fail anyways...
        self.hostname = environ["HOSTNAME"]
        try:
            # $BORG_REPO will be parsed by borg directly
            if environ["BORG_REPO"]:
                pass
        except:
            print("ERROR: Environment Variable BORG_REPO must be configured!")
            exit(1)

        # Borg INIT options
        try:
            if environ["BORG_INIT_OPTIONS"]:
                self.init_options = environ["BORG_INIT_OPTIONS"].split(' ')
        except:
            print("Environment variable BORG_INIT_OPTIONS unconfigured.")
            print(" --> Borg will create repositories without encryption!")

        try:
            if environ["BORG_CREATE_OPTIONS"]:
                self.create_options = environ["BORG_CREATE_OPTIONS"].split(' ')
                print("Global BORG_CREATE_OPTIONS: %s" % environ["BORG_CREATE_OPTIONS"])
        except:
            print("Environment variable BORG_CREATE_OPTIONS unconfigured.")
            print(" --> Borg will create backups with default settings.")

        try:
            if environ["BORG_EXCLUDE_SOURCE"]:
                self.excludes = environ["BORG_EXCLUDE_SOURCE"].split(',')
                print("Global BORG_EXCLUDE_SOURCE: %s" % environ["BORG_EXCLUDE_SOURCE"])
        except:
            pass

        # Always exclude those
        self.excludes += [ '/proc', '/sys', '/var/run', '/var/cache', '/var/tmp' ]
        self.excludes.append('/var/run/docker.sock')

        # Will we backup every container? 
        # If "False" only backup containers by Label-Config
        try:
            if "False" in environ["BORG_BACKUP_ALL"]:
                self.backup_enabled = False
        except:
            pass

        # Force Lock-break
        # Warning! Only use if BORG_REPO is exclusvily used by this container!
        try:
            if not "False" in environ["BORG_BREAK_LOCK"]:
                self.break_lock = False
        except:
            pass

###
# Borg Command Class
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

###
# This class implements all the important stuff
class Action:
    @staticmethod
    def backup(config, container_name=None):
        if config.break_lock:
            borg.break_lock()

        borg.init(config.init_options)

        print("Starting backup of container volumes - this could take a while...")
        for container in config.client.containers.list():
            if container_name != None and container_name != container.name:
                continue

            # FIXME: Skip myself
            # Will use label ATM
            try:
                if 'False' == container.labels["one.gnu.docker.backup"]:
                    print("Skipping backup of '%s', because of label configuration!" % container.name)
                    continue
            except:
                pass

            # Skip if backup is disabled by default
            try:
                if not config.backup_enabled and \
                not "True" in container.labels["one.gnu.docker.backup"]:
                    continue
            except:
                pass

            print("---------------------------------------")
            print("Backing up: '%s'..." % container.name)
            print("Volumes:")

            # Only backup specified volumes/files/...?
            try:
                if container.labels["one.gnu.docker.backup.only"]:
                    volumes_only = container.labels["one.gnu.docker.backup.only"].split(',')
            except:
                volumes_only = False

            volumes=[]
            for volume in container.attrs["Mounts"]:
                volume_src = volume["Source"]
                volume_dest = volume["Destination"]
                volume_type = volume["Type"]

                # Skip containers on unsupported driver
                # Supported:
                #  - local
                try:
                    volume_driver = volume["Driver"]
                    if not 'local' in volume_driver:
                        print(" - '%s' [%s] (Skipped - Unsupported driver '%s')" % \
                            (volume_dest, volume_src, volume_driver))
                        continue
                except:
                    pass

                # Skip volume by label
                # Syntax: one.gnu.docker.backup.skip: "/mountpoint1,/mountpoint2, ..."
                try:
                    if container.labels["one.gnu.docker.backup.skip"]:
                        skip = container.labels["one.gnu.docker.backup.skip"].split(",")
                except:
                    skip = []

                if volume_src in skip:
                    print(" - %s [%s] (skipped by label)" % (volume_dest, volume_src))
                    continue

                # Skit volume if label configuration tells us to only backup
                # specified volume destinations
                if volumes_only:
                    if volume_dest not in volumes_only:
                        continue

                volumes.append(volume_src)
                print(" - %s [%s]" % (volume_dest, volume_src))

                # Borg-Parameters
                #  - From Environment of this container
                #  - Override by Container-Labels
                try:
                    if container.labels["one.gnu.docker.backup.options"]:
                        config.create_options = container.labels["one.gnu.docker.backup.options"]
                except:
                    config.create_options = ['-s', '--progress']

                # FIXME: Skip volume, if source is not mounted to this container
                # FIXME: Exclude Source & Destinations
                for exclude in config.excludes:
                    config.create_options += ['--exclude', exclude]


        # Let's do it!
            borg.create(config.create_options, container.name, volumes)

    @staticmethod
    def list_backups(archive):
        borg.list(archive)

    @staticmethod
    def restore(config,archive):
        container_name = archive.split('+')[0]

        print(" ----> Starting Restore of Containter %s" % container_name)
        container = config.client.containers.get(container_name)

        print(" -> Pausing Container...")
        if "running" in container.status: 
            container.pause()
        
        print(" -> Restoring Archive '%s'..." % archive)
        borg.restore("::" + archive)

        print(" -> Restarting Container...")
        container.restart()

        print("-> Restore Done!")

    @staticmethod
    def info(archive):
        borg.info(archive)

config = Config()

if args.action == "backup":
    Action.backup(config, args.container)
elif args.action == "list":
    Action.list_backups(args.archive)
elif args.action == "restore":
    Action.restore(config, args.archive)
elif args.action == "info":
    Action.info(args.archive)
elif args.action == "borg":
    borg.cmd(args.borg)

exit(0)
