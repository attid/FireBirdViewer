FROM firebirdsql/firebird:5.0.3

COPY databases.conf /opt/firebird/databases.conf
COPY employee.fdb /seed/employee.fdb
COPY --chmod=0755 reset.sh /reset.sh
COPY --chmod=0755 entrypoint.sh /usr/local/bin/firebirdviewer-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/firebirdviewer-entrypoint.sh"]
CMD ["firebird"]
