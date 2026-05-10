ARG ALPINE_VERSION=3.23
FROM alpine:${ALPINE_VERSION}

ARG FIREBIRD_VERSION=5.0.4
ARG FIREBIRD_BUILD=1812-0
ARG FIREBIRD_URL=https://github.com/FirebirdSQL/firebird/releases/download/v${FIREBIRD_VERSION}/Firebird-${FIREBIRD_VERSION}.${FIREBIRD_BUILD}-source.tar.xz

RUN apk add --no-cache \
    autoconf \
    automake \
    bash \
    build-base \
    cmake \
    curl \
    file \
    findutils \
    icu-dev \
    libedit-dev \
    libtool \
    linux-headers \
    ncurses-dev \
    pax-utils \
    tar \
    xz \
    zlib-dev

WORKDIR /build

RUN curl -fsSL "${FIREBIRD_URL}" -o firebird-source.tar.xz \
    && mkdir src \
    && tar -xf firebird-source.tar.xz -C src --strip-components=1

WORKDIR /build/src

RUN ./autogen.sh \
      --prefix=/opt/firebird \
      --with-system-editline=yes \
      --with-builtin-tommath \
      --with-builtin-tomcrypt \
    && make -j"$(nproc)"

RUN set -eux; \
    src=/build/src/gen/Release/firebird; \
    out=/out/firebird; \
    mkdir -p "$out/lib" "$out/plugins" "$out/intl" "$out/doc"; \
    cp -a "$src/firebird.conf" "$src/databases.conf" "$src/plugins.conf" "$out/"; \
    cp -a "$src/lib"/*.so* "$out/lib/"; \
    cp -a "$src/plugins/libEngine13.so" "$out/plugins/"; \
    cp -a "$src/plugins/libSrp.so" "$out/plugins/"; \
    cp -a "$src/intl/libfbintl.so" "$out/intl/"; \
    cp -a "$src/intl/fbintl.conf" "$out/intl/"; \
    export LD_LIBRARY_PATH="$out/lib:$out/plugins:$out/intl:$src/lib:$src/plugins:$src/intl"; \
    for so in \
      "$out/lib/libfbclient.so" \
      "$out/plugins/libEngine13.so" \
      "$out/plugins/libSrp.so" \
      "$out/intl/libfbintl.so"; do \
        ldd "$so" | awk '/=>/ { print $3 } /^\// { print $1 }' \
          | while read -r dep; do \
              case "$dep" in \
                ""|/lib/ld-musl-*|/lib/libc.musl-*) continue ;; \
              esac; \
              cp -L "$dep" "$out/lib/" || true; \
            done; \
    done; \
    find "$out" -type f -name '*.so*' -exec strip --strip-unneeded {} + || true; \
    scanelf -n "$out/lib/libfbclient.so" "$out/plugins/libEngine13.so" > "$out/doc/needed.txt"; \
    find "$out" -maxdepth 3 -type f | sort > "$out/doc/manifest.txt"
