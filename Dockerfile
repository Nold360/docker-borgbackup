FROM debian:stretch

RUN echo 'deb http://ftp.debian.org/debian/ stretch-backports main' >> /etc/apt/sources.list && \
	apt-get update && \
	apt-get -yq --no-install-recommends -t stretch-backports install \
		borgbackup \
 		python3-docker && \
	apt-get clean

COPY ./backup.py /backup.py
CMD '/usr/bin/python3' '/backup.py' 'backup'
