FROM debian:buster as builder

RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends \
    git ca-certificates \
    g++ binutils re2c bison cmake make python3 python3-setuptools python3-dev lua5.3
  
RUN set -ex ; \
  cd /opt ; \
  git clone https://github.com/potassco/clingo.git --branch v5.4.0 ; \
  cd clingo ; \
  git submodule update --init --recursive

ENV PATH /opt/bin:$PATH
ENV PYTHONPATH /opt/lib/python3.7/site-packages/:$PYTHONPATH

RUN mkdir -p /opt/lib/python3.7/site-packages/

RUN set -ex ; \
  cd /opt/clingo ; \
  mkdir build ; \
  cmake -H. -Bbuild \
    -DCLINGO_REQUIRE_PYTHON=ON \
    -DPYCLINGO_USER_INSTALL=OFF \
    -DPYTHON_EXECUTABLE:FILEPATH=/usr/bin/python3 \
    -DCMAKE_BUILD_TYPE=Release \
    -DPYCLINGO_USE_INSTALL_PREFIX=/opt \
    -DCMAKE_INSTALL_PREFIX:PATH=/opt; \
  cmake --build build

RUN set -ex ; \
  cd /opt/clingo ; \
  cmake --build build --target install

RUN set -ex ; \
  cd /opt ; \
  git clone https://github.com/hexhex/hexlite.git --branch master

RUN set -ex ; \
  cd /opt/hexlite ; \
  python3 setup.py install --prefix=/opt

FROM debian:buster-slim

ENV PATH /opt/bin:$PATH
ENV PYTHONPATH /opt/lib/python3.7/site-packages/:$PYTHONPATH

RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends \
    python3-dev python3-setuptools lua5.3

WORKDIR /opt
COPY --from=builder /opt .

RUN set -ex ; \
  apt autoremove --purge -y ; \
  apt clean ; \
  apt autoclean

