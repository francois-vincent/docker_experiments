FROM ubuntu:14.04

RUN groupadd haproxy
RUN useradd -m -s /bin/bash -g haproxy haproxy && echo "haproxy:haproxy" | chpasswd

RUN apt-get update
RUN apt-get install -y wget make gcc binutils libssl-dev libffi-dev

WORKDIR /root

RUN wget http://www.haproxy.org/download/1.5/src/haproxy-1.5.1.tar.gz
RUN tar -zxvf haproxy-1.5.1.tar.gz

RUN cd haproxy-1.5.1 && make TARGET=generic && make install

RUN touch /var/run/haproxy.pid
COPY haproxy.cfg /etc/haproxy.cfg

EXPOSE 1936 8000

CMD ["/usr/local/sbin/haproxy", "-f", "/etc/haproxy.cfg"]
