A static load balancer based on HAProxy
=======================================

launch 2 whoami instances:
  docker run -d -p :8000 --name whoami-2 -t jwilder/whoami
  docker run -d -p :8000 --name whoami-1 -t jwilder/whoami

build and launch HAProxy:
  docker build -t myhaproxy .
  docker run -d --name haproxy -p 80:8000 -p 1936:1936 myhaproxy

access server:
  curl localhost
  curl localhost
  ...
