# Docker-BorgBackup
Full Automated Container-Backup - Docker Style!

**WARNING: This image is in ALPHA/POC-State! Don't rely your production backup on it!**
**Also, since this Container could be EXTREMLY destructive, don't keep it running in background!**

## ToDo's/Limitations/...: 
 - Implement Pruning / Repo Cleanup methods
 - Pre-/Post-Commands f.e. to dump a Database before Backup
 - Only "local"-Volumes supported
 - Restore whole containers only 
 	- also still needs a "prune before restore" method
 - ... (much more)

## Features
 - Full automated [BorgBackup](https://borgbackup.readthedocs.io/en/stable/) of all volumes of all running containers
 - Full automated restore of whole containers to a given backup-state
 - Flexible configuration using Environment-Variables & Labels

## Building / Installation
### Using Docker-Hub Image
```
docker run -ti --rm -v $(pwd)/backup:/backup -e BORG_REPO=/backup nold360/docker-backup
```

### Self-Building
Clone git & build using docker/-compose:
```
git clone https://git.nold.in/nold/docker-borgbackup
cd docker-borgbackup
docker build .
```

## Docker-Compose Configuration
Example:
```
version: "3"
services:
 backup:
  image: nold360/docker-backup
  labels:
   # Don't backup your backup...
   one.gnu.docker.backup: "False"
  environment:
   BORG_REPO: "/backup"
   BORG_INIT_OPTIONS: "--encryption=none"
   BORG_CREATE_OPTIONS: "-s --progress"
   BORG_SKIP_VOLUME_SOURCES: "/proc,/sys,/var/run,/var/cache,/var/tmp"
   BORG_BACKUP_ALL: "True"
   BORG_BREAK_LOCK: "True"
  volumes:
   # needed for SSH-BORG_REPO:
   - "./ssh:/root/.ssh:ro"

   # needed for local BORG_REPO:
   - "./backup:/backup"

   # needed for connecting the Docker-API
   - "/var/run/docker.sock:/var/run/docker.sock"

   # Include every volume-Path you might want to backup!
   - "/srv/:/srv/:ro"
   - "/var/lib/docker/:/var/lib/docker:ro"

```

## Global-/ Borg-Configuration (using Environment)
#### BORG_REPO
Path/Definition of the Borg-Repository. Can be a local path to a container volume (f.e. "/backup") or an SSH-Borg-Server (f.e. "borg@backup.domain:myRepo").

**Note:** When using SSH-Repo make sure to setup "/ssh" with ssh-key (and maybe known_hosts/config)!

**Default:** None (**Must be configured!**)

#### BORG_INIT_OPTIONS
Options to pass to "borg init" when creating a new BORG_REPO
**Default:** "--encryption=none"

#### BORG_CREATE_OPTIONS
Options to pass to "borg create"
**Default:** "-s --progress"

#### BORG_SKIP_VOLUME_SOURCES
List of Volume-Pathes to exclude globaly from backup.
**Default:** "/proc,/sys,/var/run,/var/cache,/var/tmp"

#### BORG_BACKUP_ALL
Backup every container?
**Default:** "True"

#### BORG_BREAK_LOCK
Forces "borg break-lock" before backing up; Helps recovering from aborted backups
**Warning:** Can be **ultimate destructive**, when more then one borg-process is using the same BORG_REPO!

**Default:** "True"


## Client Configuration (using labels)
### one.gnu.docker.backup
Backup this container?
**Values:** "True|False"

### one.gnu.docker.backup.only
Only backup volumes specified in this comma-separated list:
**Example:** "/data/foo,/bar"

### one.gnu.docker.backup.skip
Skip volumes specified in this comma-seperated list:
**Example:** "/skip/me,/too"

### one.gnu.docker.backup.options
Options/Parameters to pass to "borg create"
**Example:** "-v --stats"


## Using this Container
Included in this container is a Python-Wrapper script called just "backup".
It implements the main backup/restore tasks.

### Overview
```
docker-compose run backup --help

-------- Borg Docker Backup --------
usage: backup.py [-h] {restore,list,backup,info,borg} ...

Awesome Borg-Backup for Docker made simple!

positional arguments:
  {restore,list,backup,info,borg}
                        Sub-Commands
    restore             Restore Container from Backup
    list                List archives / files in archive
    backup              Backup all / a single container
    info                Show infos about repo / archive
    borg                Run every board-command you like (not yet working)

optional arguments:
  -h, --help            show this help message and exit

```

### Backup
The wrapper will collect all volumes mapped to a container and create a single backup archive for every container.
The archives will be named like this: `my_container_name+2018-04-14_08:42`

#### Help
```
# docker-compose run backup backup -h
-------- Borg Docker Backup --------
usage: backup.py backup [-h] [container]

positional arguments:
  container   Name of the Container to backup (default: all)

```

#### Backing up all Containers
Simply run the container without any arguments:
``` 
docker-compose run backup
```

#### Backing up single container
```
docker-compose run backup my_container_name
```

### Restore
Restoring a whole container is as simple as backing it up. You just need the name the the backup archive (see "list" subcommand).

```
docker-compose run backup restore my_container_name+2018-04-14_08:42
```

The wrapper will automatically:
 - Pause the running container
 - Restore the backup from BORG_REPO
 - Restart the container



#### Help
```
# docker-compose run backup restore -h
-------- Borg Docker Backup --------
usage: backup.py restore [-h] archive

positional arguments:
  archive     Archive to Restore container from

optional arguments:
  -h, --help  show this help message and exit
```


### List Backup-Archives
```
docker-compose run backup list
```

