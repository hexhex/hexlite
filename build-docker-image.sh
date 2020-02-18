#!/bin/bash

docker image build --squash --file Dockerfile -t hexlite:dev .
