FROM debian:buster

RUN apt-get update && \
	apt-get -yq --no-install-recommends install \
		borgbackup \
 		python3-docker && \
	apt-get clean && \
	rm -rf /var/tmp/* /tmp/* /var/lib/apt/lists/* && \
	mkdir -p /borg/ssh && \
	ln -s /root/.ssh /borg/ssh

ENV BORG_BASE_DIR /borg
ENV BORG_CONFIG_DIR /borg/config
ENV BORG_CACHE_DIR /borg/cache
ENV BORG_SECURITY_DIR /borg/config/security
ENV BORG_KEYS_DIR /borg/config/keys

ENV BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK yes
ENV BORG_RELOCATED_REPO_ACCESS_IS_OK yes

VOLUME /borg

COPY ./backup.py /backup.py
ENTRYPOINT [ "/backup.py" ]
CMD [ "backup" ]
