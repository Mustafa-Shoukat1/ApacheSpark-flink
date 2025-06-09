# Production Apache Spark Cluster with Jupyter Support
FROM apache/spark:3.5.0

# Metadata
LABEL maintainer="Mustafa Shoukat <mustafa.shoukat.dev@gmail.com>"
LABEL version="1.0.0"
LABEL description="Production Apache Spark with Python, Scala, and ML support"

# Set environment variables
USER root
ENV PYTHON_VERSION=3.10.11
ENV SCALA_VERSION=2.12.17
ENV HADOOP_VERSION=3.3.4
ENV SPARK_HOME=/opt/spark
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

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
    openjdk-11-jdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-spark.txt /tmp/requirements-spark.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements-spark.txt --no-cache-dir && \
    rm /tmp/requirements-spark.txt

# Download and install Spark connectors
RUN mkdir -p $SPARK_HOME/jars/connectors && \
    # Kafka connector
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar && \
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar && \
    # JDBC connectors
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar && \
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar && \
    # Delta Lake
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.4.0/delta-core_2.12-2.4.0.jar && \
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/io/delta/delta-storage/2.4.0/delta-storage-2.4.0.jar && \
    # AWS S3 support
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    wget -P $SPARK_HOME/jars/ https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar

# Create application directories
RUN mkdir -p /opt/spark-apps/src /opt/spark-apps/config /opt/spark-apps/logs /opt/spark-apps/data

# Copy application code
COPY spark-projects/ /opt/spark-apps/src/
COPY config/ /opt/spark-apps/config/

# Set up Spark configuration
COPY docker/spark/spark-defaults.conf $SPARK_HOME/conf/spark-defaults.conf
COPY docker/spark/log4j2.properties $SPARK_HOME/conf/log4j2.properties

# Create non-root user
RUN groupadd -r spark && useradd -r -g spark spark && \
    chown -R spark:spark /opt/spark* && \
    chmod +x /opt/spark-apps/src/**/*.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:4040 || exit 1

# Switch to non-root user
USER spark

# Set working directory
WORKDIR /opt/spark-apps

# Expose Spark ports
EXPOSE 4040 7077 8080 8081 18080

# Default command
CMD ["/opt/spark/bin/spark-submit", "--master", "local[*]", "src/batch-processing/main.py"]