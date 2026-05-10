# Firebird 5 Embedded Bundle for Alpine/musl

This project can use Firebird Embedded on Alpine without installing system packages by carrying a
musl-built x86_64 Firebird runtime next to the application.

Do not use the official Linux x64 binary tarball as this bundle for Alpine. It is intended for
glibc-based Linux distributions; this builder compiles Firebird inside Alpine so the produced shared
libraries target musl.

Build the bundle from the repository root:

```bash
scripts/build-firebird-musl-bundle.sh
```

Defaults:

- Firebird `5.0.4.1812-0`
- Alpine `3.23`
- Output directory: `dist/firebird-5.0.4-musl-x86_64`
- Archive: `dist/firebird-5.0.4-musl-x86_64.tar.gz`

Override versions when needed:

```bash
FIREBIRD_VERSION=5.0.4 FIREBIRD_BUILD=1812-0 ALPINE_VERSION=3.23 \
  scripts/build-firebird-musl-bundle.sh
```

Runtime layout:

```text
firebird-5.0.4-musl-x86_64/
  firebird.conf
  databases.conf
  plugins.conf
  lib/
    libfbclient.so
    libfbclient.so.*
    libib_util.so
    libgcc_s.so.1
    libtomcrypt.so.1
    libtommath.so.0
  plugins/
    libEngine13.so
    libSrp.so
  intl/
    libfbintl.so
    fbintl.conf
  doc/
    manifest.txt
    needed.txt
```

The bundle carries Firebird libraries and non-musl shared dependencies. It assumes the target host is
Alpine x86_64 and already has the normal musl loader from the base OS.

Use it in Alpine:

```bash
export FIREBIRD=/app/firebird
export LD_LIBRARY_PATH="$FIREBIRD/lib:$FIREBIRD/plugins:$FIREBIRD/intl"
```

For Python `firebird-driver` through SQLAlchemy, pass the client library path in the connection URL:

```text
?charset=UTF8&fb_client_library=/app/firebird/lib/libfbclient.so
```

Embedded database paths must be local file paths. A network DSN like `localhost:/db/file.fdb`
will use the remote provider instead of the embedded engine.
