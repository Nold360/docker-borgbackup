FROM debian:stretch

RUN echo 'deb http://ftp.debian.org/debian/ stretch-backports main' >> /etc/apt/sources.list && \
	apt-get update && \
	apt-get -yq --no-install-recommends -t stretch-backports install \
		borgbackup \
 		python3-docker && \
	apt-get clean

ENV BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK yes
ENV BORG_RELOCATED_REPO_ACCESS_IS_OK yes

COPY ./backup.py /backup.py
CMD [ "backup" ]
ENTRYPOINT [ "/backup.py" ]
