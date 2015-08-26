FROM ubuntu:14.04

RUN mkdir -p /var/lib/docker
COPY /var/lib/docker/repositories-aufs /var/lib/docker/repositories-aufs

# share images folder
VOLUME ["/var/lib/docker/aufs"]

EXPOSE 8000

# Do nothing
CMD ["/bin/cat"]
