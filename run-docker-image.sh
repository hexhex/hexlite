#!/bin/bash

echo
echo "useful commands:"
echo
echo "$ docker stop hexlite"
echo "$ docker start hexlite"
echo "$ docker exec -it hexlite bash"
echo "$ docker rm hexlite"
echo
echo "http://dockerlabs.collabnix.com/docker/cheatsheet/"
echo
docker run --name hexlite -it hexlite:dev
