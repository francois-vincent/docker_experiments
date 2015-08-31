A dynamic load balancer based on HAProxy
========================================


courtesy of: http://jasonwilder.com/blog/2014/07/15/docker-service-discovery/


launch etcd image:
  docker run -d --name etcd -p 4001:4001 -p 7001:7001 coreos/etcd

get etcd image's ip in env var ETCD_IP:
  export ETCD_IP=$(docker inspect --format '{{ .NetworkSettings.IPAddress }}' etcd)
  export ETCD_HOST=$ETCD_IP:4001

launch docker-register:
  docker run --name docker-register -d -e HOST_IP=127.0.0.1 -e ETCD_HOST=$ETCD_HOST -v /var/run/docker.sock:/var/run/docker.sock -t jwilder/docker-register

launch docker-discover:
  docker run -d --net host --name docker-discover -e ETCD_HOST=$ETCD_HOST -p 127.0.0.1:1936:1936 -t jwilder/docker-discover

launch some service instances:
  docker run -d -p :8000 -t jwilder/whoami
  docker run -d -p :8000 -t jwilder/whoami
  ...

access server:
  curl localhost
  curl localhost
  ...
