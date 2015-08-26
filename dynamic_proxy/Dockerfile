FROM ubuntu:14.04

RUN apt-get update
RUN apt-get install -y supervisor dnsutils python-pip
RUN apt-get remove -y systemd

WORKDIR /root
COPY dynaproxy.py ./dynaproxy.py
COPY requirements.txt ./requirements.txt
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN pip install -r requirements.txt

RUN touch /var/log/dynaproxy.log
RUN chmod 666 /var/log/dynaproxy.log

EXPOSE 8000

CMD ["/usr/bin/supervisord"]
