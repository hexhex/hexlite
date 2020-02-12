# build a docker image with hexlite and examples installed
FROM gcc:9.2.0

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
  git \
  re2c bison cmake python3-dev lua5.3

RUN set -ex ; \
  cd /opt ; \
  git clone https://github.com/potassco/clingo.git --branch v5.4.0 ; \
  cd clingo ; \
  git submodule update --init --recursive

RUN set -ex ; \
  cd /opt/clingo ; \
  mkdir build ; \
  cmake -H. -Bbuild \
    -DCLINGO_REQUIRE_PYTHON=ON \
    -DPYCLINGO_USER_INSTALL=OFF \
    -DPYTHON_EXECUTABLE:FILEPATH=/usr/bin/python3 \
    -DCLINGO_PYTHON_VERSION=3 \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/local/; \
  cmake --build build

RUN set -ex ; \
  cd /opt/clingo ; \
  cmake --build build --target install

