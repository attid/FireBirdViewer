#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

firebird_version="${FIREBIRD_VERSION:-5.0.4}"
firebird_build="${FIREBIRD_BUILD:-1812-0}"
alpine_version="${ALPINE_VERSION:-3.23}"
image="firebirdviewer-firebird-musl:${firebird_version}-${firebird_build}-alpine${alpine_version}"
out_dir="${OUT_DIR:-${repo_root}/dist/firebird-${firebird_version}-musl-x86_64}"
tarball="${TARBALL:-${out_dir}.tar.gz}"

docker build \
  --platform linux/amd64 \
  --build-arg "ALPINE_VERSION=${alpine_version}" \
  --build-arg "FIREBIRD_VERSION=${firebird_version}" \
  --build-arg "FIREBIRD_BUILD=${firebird_build}" \
  -f "${repo_root}/docker/firebird-musl/Dockerfile" \
  -t "${image}" \
  "${repo_root}"

container_id="$(docker create "${image}")"
trap 'docker rm -f "${container_id}" >/dev/null 2>&1 || true' EXIT

rm -rf "${out_dir}"
mkdir -p "$(dirname "${out_dir}")"
docker cp "${container_id}:/out/firebird" "${out_dir}"

tar -C "$(dirname "${out_dir}")" -czf "${tarball}" "$(basename "${out_dir}")"

printf 'Bundle: %s\n' "${out_dir}"
printf 'Tarball: %s\n' "${tarball}"
printf 'Client: %s/lib/libfbclient.so\n' "${out_dir}"
printf 'Engine13: %s/plugins/libEngine13.so\n' "${out_dir}"
