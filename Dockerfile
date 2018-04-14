FROM debian:buster

RUN apt-get update && \
	apt-get -yq --no-install-recommends install \
		borgbackup \
		openssh-client \
 		python3-docker && \
	apt-get clean && \
	rm -rf /var/tmp/* /tmp/* /var/lib/apt/lists/* && \
	ln -s /root/.ssh /ssh

ENV BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK yes
ENV BORG_RELOCATED_REPO_ACCESS_IS_OK yes

VOLUME /ssh

COPY ./backup.py /backup.py
ENTRYPOINT [ "/backup.py" ]
CMD [ "backup" ]
