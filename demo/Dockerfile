FROM firebirdsql/firebird:5.0.3

COPY databases.conf /opt/firebird/databases.conf
COPY employee.fdb /seed/employee.fdb
COPY --chmod=0755 reset.sh /reset.sh

