FROM debian:buster

RUN apt-get update && \
	apt-get -yq --no-install-recommends install \
		locales \
		borgbackup \
 		python3-docker && \
	apt-get clean

ENV BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK yes
ENV BORG_RELOCATED_REPO_ACCESS_IS_OK yes

COPY ./backup.py /backup.py
CMD [ "backup" ]
ENTRYPOINT [ "/backup.py" ]
