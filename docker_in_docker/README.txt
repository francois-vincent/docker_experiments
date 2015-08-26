Docker Image
============


An generic empty Docker image designed to be able to run images from its host.
Once launched, containers inside the image are not visible from outside host,
except for their published ports and volumes if these ports and volumes are also
published by the containing image.

build image:
  docker build -t mydocker .

run image:
  docker run -d -p 80:8000 -v /var/run/docker.sock:/var/run/docker.sock -v /var/lib/docker/aufs:/var/lib/docker/aufs --name mydocker mydocker
