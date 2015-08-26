A dynamic load balancer in docker
=================================

  no dynamic reverse proxy available, in the sense of:
  https://github.com/crosbymichael/skydock/pull/31
  only found this :
  see https://github.com/skynetservices/skyproxy :)
  so I created a POC in python...

References:
  https://github.com/crosbymichael/skydock
  https://github.com/skynetservices/skydns
  https://github.com/jwilder/whoami

re-launch docker daemon with dns settings:
  sudo service docker stop
  sudo docker -d --bip=172.17.42.1/16 --dns=172.17.42.1

launch skydns with 'docker' domain:
  docker run -d -p 172.17.42.1:53:53/udp --name skydns crosbymichael/skydns -nameserver 8.8.8.8:53 -domain docker

launch skydock with 'dev.docker' subdomain:
  docker run -d -v /var/run/docker.sock:/docker.sock --name skydock crosbymichael/skydock -environment dev -s /docker.sock -domain docker -name skydns

launch 2 whoami instances:
  docker run -d -p :8000 -t jwilder/whoami
  docker run -d -p :8000 -t jwilder/whoami

build and launch dynaproxy:
  docker build -t dynaproxy .
  docker run -d --name dynaproxy -p 80:8000 dynaproxy

show subdomain hosts:
  dig @172.17.42.1 dev.docker

access server:
  curl localhost
  curl localhost
  ...

launch new whoami instance, then access server:
  docker run -d -p :8000 -t jwilder/whoami
  curl localhost
  curl localhost
  ...

kill any whoami instance, then access server:
  docker ps
  docker stop xxxx
  curl localhost
  curl localhost
  ...
