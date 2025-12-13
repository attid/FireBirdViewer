#!/usr/bin/env bash
set -euo pipefail

: "${FIREBIRD_ROOT_PASSWORD:?FIREBIRD_ROOT_PASSWORD is required}"

RESET_EVERY_SECONDS="${RESET_EVERY_SECONDS:-3600}"
DB_ALIAS_RAW="${DB_ALIAS:-employee}"
DB_ALIAS="$(printf '%s' "$DB_ALIAS_RAW" | tr -cd 'A-Za-z0-9_.$-')"
DB_CONN="${DB_CONN:-firebird5:${DB_ALIAS}}"
SERVICE_MGR="${SERVICE_MGR:-firebird5:service_mgr}"

DBFILE="${DBFILE:-/var/lib/firebird/data/${DB_ALIAS}.fdb}"
BASELINE="${BASELINE:-/var/lib/firebird/data/${DB_ALIAS}.baseline.fbk}"

# Seed (эталонная) БД для инициализации. Монтируется read-only в reset-контейнер.
# Пример: /apps/firebirdviewer/employee.fdb:/seed/employee.fdb:ro
SEED_DB="${SEED_DB:-/seed/employee.fdb}"

# (employee.sql нам больше не нужен)

# Простое логирование (обязательно определяем ДО использования)
log() {
  # В Portainer часто не видно времени, поэтому добавляем timestamp.
  # Формат ISO-8601 с TZ.
  echo "[reset] $(date -Is) $*"
}

# Значения по умолчанию для demo
DEMO_USER="${DEMO_USER:-demo}"
DEMO_PASS="${DEMO_PASS:-demo}"

# FULL_RESET: true/1/yes/on → удаляем DB и baseline при старте
FULL_RESET_RAW="${FULL_RESET:-false}"
FULL_RESET="$(printf '%s' "$FULL_RESET_RAW" | tr '[:upper:]' '[:lower:]')"

full_reset_if_requested() {
  case "$FULL_RESET" in
    1|true|yes|y|on)
      log "FULL_RESET enabled: deleting $DBFILE and $BASELINE"
      rm -f "$DBFILE" "$BASELINE" "${BASELINE}.tmp" || true
      ;;
    *)
      :
      ;;
  esac
}

ensure_demo_access() {
  # 1) гарантируем, что пользователь demo существует в security.db
  # (ошибку "already exists" игнорируем)
  log "ensuring user ${DEMO_USER} exists"
  tmp="/tmp/ensure_demo_user.sql"
  printf "CREATE USER %s PASSWORD '%s';
COMMIT;
" "$DEMO_USER" "$DEMO_PASS" > "$tmp"
  isql -q -u SYSDBA -p "$FIREBIRD_ROOT_PASSWORD" "$DB_CONN" -i "$tmp" >/dev/null 2>&1 || true
  rm -f "$tmp" || true

  # 2) гарантируем права demo в текущей БД
  log "ensuring ${DEMO_USER} has admin rights in ${DB_CONN}"
  tmp="/tmp/ensure_demo_privs.sql"
  # ВАЖНО: для PSQL-блоков в isql надёжнее менять терминатор
  printf "CONNECT '%s' USER SYSDBA PASSWORD '%s';

-- 1) System privileges: позволяют делать DDL без указания ROLE (в отличие от RDB\$ADMIN, которая является ролью)
GRANT CREATE TABLE TO USER %s;
GRANT ALTER ANY TABLE TO USER %s;
GRANT DROP ANY TABLE TO USER %s;
GRANT CREATE VIEW TO USER %s;
GRANT ALTER ANY VIEW TO USER %s;
GRANT DROP ANY VIEW TO USER %s;
GRANT CREATE PROCEDURE TO USER %s;
GRANT ALTER ANY PROCEDURE TO USER %s;
GRANT DROP ANY PROCEDURE TO USER %s;
GRANT CREATE FUNCTION TO USER %s;
GRANT ALTER ANY FUNCTION TO USER %s;
GRANT DROP ANY FUNCTION TO USER %s;
GRANT CREATE SEQUENCE TO USER %s;
GRANT ALTER ANY SEQUENCE TO USER %s;
GRANT DROP ANY SEQUENCE TO USER %s;

-- 2) Админ-роль (даёт DDL/DML в рамках БД; некоторые клиенты требуют указать ROLE=RDB\$ADMIN)
GRANT RDB\$ADMIN TO USER %s WITH ADMIN OPTION;

-- 2) Явные гранты, чтобы GUI показывали права (и чтобы можно было работать без ROLE)
SET TERM ^;
EXECUTE BLOCK AS
  DECLARE VARIABLE n VARCHAR(63);
BEGIN
  -- Tables
  FOR SELECT TRIM(rdb\$relation_name)
      FROM rdb\$relations
      WHERE COALESCE(rdb\$system_flag, 0) = 0 AND rdb\$view_blr IS NULL
      INTO :n
  DO
    EXECUTE STATEMENT 'GRANT ALL ON ' || n || ' TO USER %s';

  -- Views
  FOR SELECT TRIM(rdb\$relation_name)
      FROM rdb\$relations
      WHERE COALESCE(rdb\$system_flag, 0) = 0 AND rdb\$view_blr IS NOT NULL
      INTO :n
  DO
    EXECUTE STATEMENT 'GRANT SELECT ON ' || n || ' TO USER %s';

  -- Procedures
  FOR SELECT TRIM(rdb\$procedure_name)
      FROM rdb\$procedures
      WHERE COALESCE(rdb\$system_flag, 0) = 0
      INTO :n
  DO
    EXECUTE STATEMENT 'GRANT EXECUTE ON PROCEDURE ' || n || ' TO USER %s';

  -- Sequences / Generators
  FOR SELECT TRIM(rdb\$generator_name)
      FROM rdb\$generators
      WHERE COALESCE(rdb\$system_flag, 0) = 0
      INTO :n
  DO
    EXECUTE STATEMENT 'GRANT USAGE ON SEQUENCE ' || n || ' TO USER %s';
END^
SET TERM ;^

COMMIT;
" \
    "$DB_CONN" "$FIREBIRD_ROOT_PASSWORD" \
    "$DEMO_USER" \
    "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" \
    "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" \
    "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" \
    "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" \
    "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" \
    "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" "$DEMO_USER" > "$tmp"
  isql -q -u SYSDBA -p "$FIREBIRD_ROOT_PASSWORD" -i "$tmp" >/dev/null
  rm -f "$tmp" || true
}


wait_server() {
  # isql не умеет "подключаться" к service_mgr, поэтому проверяем готовность сервера по TCP-порту.
  log "waiting for Firebird TCP port on firebird5:3050..."
  while true; do
    # bash builtin TCP check (работает в /bin/bash)
    if (echo > /dev/tcp/firebird5/3050) >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  log "server port is open"
}


wait_db() {
  log "waiting for ${DB_CONN}..."
  local n=0
  while true; do
    # захватываем stderr, чтобы иногда показывать причину ожидания
    out="$(echo "quit;" | isql -q -u SYSDBA -p "$FIREBIRD_ROOT_PASSWORD" "$DB_CONN" 2>&1)" && break
    n=$((n+1))
    if [ $((n % 10)) -eq 0 ]; then
      log "still waiting (${n} tries). last error: ${out//$'
'/ }"
    fi
    sleep 2
  done
  log "db reachable"
}


# IMPORTANT:
# Firebird SQL syntax requires the database name after CREATE DATABASE to be a string literal.
# So we MUST write: CREATE DATABASE 'employee' ...  (not CREATE DATABASE employee ...)
# With DatabaseAccess=None this only works if 'employee' is an alias defined in databases.conf.
create_db_if_missing() {
  if [ -f "$DBFILE" ]; then
    log "db file exists: $DBFILE"
    return 0
  fi

  # Инициализируем БД копированием эталонного employee.fdb в общий volume.
  if [ ! -f "$SEED_DB" ]; then
    log "ERROR: seed DB not found at $SEED_DB"
    exit 1
  fi

  log "db file missing, seeding from read-only $SEED_DB -> $DBFILE"
  cp -f "$SEED_DB" "$DBFILE"
  chmod 0660 "$DBFILE" || true

  # Дождаться, пока сервер увидит БД через alias и сможет открыть
  wait_db

  # Права demo добавляем/фиксируем поверх seed
  ensure_demo_access
}


ensure_baseline() {
  # baseline должен соответствовать текущему employee, включая права demo.
  if [ -s "$BASELINE" ]; then
    log "baseline exists: $BASELINE"
    return 0
  fi

  log "baseline missing, creating: $BASELINE"
  wait_db
  ensure_demo_access

  tmpbk="${BASELINE}.tmp"
  rm -f "$tmpbk"

  gbak -b -user SYSDBA -pas "$FIREBIRD_ROOT_PASSWORD" \
    -se "$SERVICE_MGR" \
    "$DB_ALIAS" "$tmpbk"

  if [ ! -s "$tmpbk" ]; then
    log "ERROR: baseline not created or empty: $tmpbk"
    exit 1
  fi

  mv -f "$tmpbk" "$BASELINE"
  log "baseline created"
}



shutdown_db() {
  log "shutdown ${DB_CONN}"
  # Корректный shutdown перед удалением файла БД
  gfix -shut full -force 0 \
    -user SYSDBA -pas "$FIREBIRD_ROOT_PASSWORD" \
    "$DB_CONN" || true
}



restore_from_baseline() {
  log "removing existing database file before restore"
  rm -f "$DBFILE"

  log "restore baseline -> ${DBFILE}"
  gbak -c -user SYSDBA -pas "$FIREBIRD_ROOT_PASSWORD" \
    -se "$SERVICE_MGR" \
    "$BASELINE" "$DBFILE"

  # После restore гарантируем, что demo есть и имеет права (на случай старого baseline)
  wait_db
  ensure_demo_access
}




online_db() {
  # НИЧЕГО НЕ ДЕЛАЕМ
  # После gbak -c база уже online, вызывать gfix -online нельзя
  :
}



main() {
  log "started; interval=${RESET_EVERY_SECONDS}s; alias=${DB_ALIAS}"
  full_reset_if_requested
  wait_server

  # 1) Create DB (if missing), then load employee.sql
  create_db_if_missing

  # 2) Create baseline (if missing)
  ensure_baseline

  # 3) Periodic restore
  while true; do
    shutdown_db
    restore_from_baseline
    sleep "$RESET_EVERY_SECONDS"
  done
}

main "$@"
