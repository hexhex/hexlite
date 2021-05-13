FROM debian:buster as builder

ARG PYTHON=python3.7
ARG HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG=1.4.0
ARG HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH=/opt/hexlite/java-api/target/hexlite-java-plugin-api-${HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG}.jar

RUN mkdir -p /opt/lib/$PYTHON/site-packages/

RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends \
    wget git ca-certificates \
    build-essential $PYTHON python3-setuptools python3-dev python3-pip lua5.3 \
    openjdk-11-jre-headless openjdk-11-jdk-headless

RUN set -ex ; \
  $PYTHON -m pip install --upgrade pip ; \
  $PYTHON -m pip install clingo==5.5.0.post3 jpype1==1.2.1 cffi==1.14.4

# install maven for building hexlite Java API
# (not the one shipped with buster, because it does not work with openjdk-11)
RUN set -ex ; \
  cd /opt ; \
  wget https://downloads.apache.org/maven/maven-3/3.8.1/binaries/apache-maven-3.8.1-bin.tar.gz ; \
  tar xvf apache-maven-3.8.1-bin.tar.gz ; \
  mv apache-maven-3.8.1 /opt/maven

ENV MAVEN_HOME /opt/maven
ENV PATH /opt/bin:/opt/maven/bin:$PATH
ENV PYTHONPATH /opt/lib/$PYTHON/site-packages/:$PYTHONPATH

COPY . /opt/hexlite

# RUN set -ex ; \
#   cd /opt ; \
#   git clone https://github.com/hexhex/hexlite.git --branch master

RUN set -ex ; \
  cd /opt/hexlite ; \
  python3 setup.py install --prefix=/opt ; \
  mvn compile package install

# run tests (optional)
RUN set -ex ; \
  cd /opt/hexlite/tests ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH} \
  ./run-tests.sh
