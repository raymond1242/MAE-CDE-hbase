# Local single-node HBase (standalone mode) with the Thrift server, to practice
# and test the scripts for free before using the EMR cluster.
FROM eclipse-temurin:11-jre

ARG HBASE_VERSION=2.6.4
ENV HBASE_HOME=/opt/hbase
ENV PATH=/opt/hbase/bin:$PATH

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL "https://archive.apache.org/dist/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-bin.tar.gz" \
    | tar -xz -C /opt \
 && mv "/opt/hbase-${HBASE_VERSION}" "$HBASE_HOME"

COPY hbase-site.xml /opt/hbase/conf/hbase-site.xml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 9090: Thrift server (happybase) · 16010: HBase Master web UI
EXPOSE 9090 16010
ENTRYPOINT ["/entrypoint.sh"]
