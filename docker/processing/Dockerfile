FROM debian:jessie as essentia
# This is basically the contents of https://github.com/MTG/essentia-docker
# but it only builds the freesound extractor as a static binary

RUN apt-get update \
    && apt-get install -y \
       python libpython2.7 build-essential git wget pkg-config nasm cmake \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /essentia && cd /essentia && git clone https://github.com/MTG/essentia.git
WORKDIR /essentia/essentia
RUN git checkout -t origin/debianstatic

WORKDIR /essentia/essentia/packaging
RUN ./build_3rdparty_static_debian.sh
WORKDIR /essentia/essentia
RUN PKG_CONFIG_PATH=packaging/debian_3rdparty/lib/pkgconfig ./waf configure --with-example=streaming_extractor_freesound --with-static-examples \
    && ./waf && ./waf install

# ---

FROM debian:jessie as stereofy

RUN apt-get update && apt-get install -y build-essential libsndfile-dev

RUN mkdir /code
COPY . /code
WORKDIR /code/_sandbox/stereofy
RUN make

# ---

FROM debian:jessie

COPY --from=essentia /usr/local/bin/essentia_streaming_extractor_freesound /usr/local/bin
COPY --from=stereofy /code/_sandbox/stereofy/stereofy /usr/local/bin

RUN apt-get update \
    && apt-get install -y python wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O - https://bootstrap.pypa.io/get-pip.py | python

RUN mkdir /code
COPY . /code

WORKDIR /code
RUN pip install -r requirements_processing.txt
