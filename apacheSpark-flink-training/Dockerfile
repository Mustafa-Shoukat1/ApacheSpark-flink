# Production-ready Apache Flink with Python support
FROM --platform=linux/amd64 flink:1.17.1-scala_2.12-java11

# Metadata
LABEL maintainer="Mustafa Shoukat <mustafa.shoukat.dev@gmail.com>"
LABEL version="1.0.0"
LABEL description="Production Apache Flink with Python support and connectors"

# Set environment variables
ENV PYTHON_VERSION=3.10.11
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV FLINK_HOME=/opt/flink
ENV PATH=$PATH:$FLINK_HOME/bin
ENV PYTHONPATH=$FLINK_HOME/opt/python

# Install system dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    curl \
    wget \
    git \
    vim \
    procps \
    net-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.10 from source (PyFlink supports 3.8+)
RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz && \
    tar -xvf Python-${PYTHON_VERSION}.tgz && \
    cd Python-${PYTHON_VERSION} && \
    ./configure --enable-optimizations --enable-shared && \
    make -j$(nproc) && \
    make altinstall && \
    ldconfig /usr/local/lib && \
    cd .. && \
    rm -f Python-${PYTHON_VERSION}.tgz && \
    rm -rf Python-${PYTHON_VERSION} && \
    ln -sf /usr/local/bin/python3.10 /usr/local/bin/python3 && \
    ln -sf /usr/local/bin/python3.10 /usr/local/bin/python && \
    ln -sf /usr/local/bin/pip3.10 /usr/local/bin/pip

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt --no-cache-dir && \
    rm /tmp/requirements.txt

# Download and install Flink connectors and dependencies
RUN mkdir -p $FLINK_HOME/lib/connectors && \
    # Kafka connector
    wget -P $FLINK_HOME/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/1.17.1/flink-sql-connector-kafka-1.17.1.jar && \
    # JDBC connector
    wget -P $FLINK_HOME/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.0-1.17/flink-connector-jdbc-3.1.0-1.17.jar && \
    # PostgreSQL driver
    wget -P $FLINK_HOME/lib/ https://repo1.maven.org/maven2/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar && \
    # MySQL driver
    wget -P $FLINK_HOME/lib/ https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar && \
    # Elasticsearch connector
    wget -P $FLINK_HOME/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-elasticsearch7/1.17.1/flink-sql-connector-elasticsearch7-1.17.1.jar && \
    # Filesystem connector
    wget -P $FLINK_HOME/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-filesystem/1.17.1/flink-sql-connector-filesystem-1.17.1.jar && \
    # Hadoop dependencies for S3
    wget -P $FLINK_HOME/lib/ https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    wget -P $FLINK_HOME/lib/ https://repo.maven.apache.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar

# Create application directories
RUN mkdir -p /opt/flink-apps/src /opt/flink-apps/config /opt/flink-apps/logs /opt/flink-apps/checkpoints

# Copy application code
COPY src/ /opt/flink-apps/src/
COPY config/ /opt/flink-apps/config/

# Set up Flink configuration for production
COPY docker/flink/flink-conf.yaml $FLINK_HOME/conf/flink-conf.yaml
COPY docker/flink/log4j-console.properties $FLINK_HOME/conf/log4j-console.properties

# Create non-root user for security
RUN groupadd -r flink && useradd -r -g flink flink && \
    chown -R flink:flink /opt/flink* && \
    chmod +x /opt/flink-apps/src/**/*.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/overview || exit 1

# Switch to non-root user
USER flink

# Set working directory
WORKDIR /opt/flink-apps

# Expose Flink ports
EXPOSE 8081 6123 6124 6125

# Default command
CMD ["flink", "run", "-py", "src/main.py"]
