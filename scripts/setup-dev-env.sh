#!/bin/bash

# Production Data Platform Setup Script
# This script sets up the complete development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command_exists docker; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command_exists docker-compose; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    if ! command_exists python3; then
        error "Python 3 is not installed. Please install Python 3.8+ first."
    fi
    
    if ! command_exists java; then
        warn "Java is not found in PATH. Some features may not work."
    fi
    
    log "Prerequisites check completed ✓"
}

# Create project directories
create_directories() {
    log "Creating project directories..."
    
    directories=(
        "spark-projects/batch-processing"
        "spark-projects/streaming"
        "spark-projects/ml-pipelines"
        "spark-projects/optimization"
        "flink-projects/stream-processing"
        "flink-projects/complex-events"
        "flink-projects/state-management"
        "flink-projects/windowing"
        "infrastructure/docker"
        "infrastructure/kubernetes"
        "infrastructure/terraform"
        "infrastructure/helm-charts"
        "monitoring/prometheus"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/provisioning/datasources"
        "monitoring/grafana/provisioning/dashboards"
        "monitoring/elasticsearch"
        "monitoring/alerting"
        "data-governance/data-quality"
        "data-governance/lineage"
        "data-governance/privacy"
        "data-governance/compliance"
        "testing/unit-tests"
        "testing/integration-tests"
        "testing/performance-tests"
        "testing/e2e-tests"
        "docs/api"
        "docs/architecture"
        "docs/deployment"
        "docs/configuration"
        "docs/troubleshooting"
        "examples/spark"
        "examples/flink"
        "examples/patterns"
        "examples/production"
        "examples/optimization"
        "utils/shared"
        "config"
        "sql"
        "notebooks"
        "data/raw"
        "data/processed"
        "data/output"
        "logs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log "Created directory: $dir"
    done
    
    log "Project directories created ✓"
}

# Setup Python virtual environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log "Created Python virtual environment"
    fi
    
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log "Installed Flink dependencies"
    fi
    
    if [ -f "requirements-spark.txt" ]; then
        pip install -r requirements-spark.txt
        log "Installed Spark dependencies"
    fi
    
    log "Python environment setup completed ✓"
}

# Generate configuration files
generate_configs() {
    log "Generating configuration files..."
    
    # Prometheus configuration
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'flink-jobmanager'
    static_configs:
      - targets: ['flink-jobmanager:9249']

  - job_name: 'flink-taskmanager'
    static_configs:
      - targets: ['flink-taskmanager:9249']

  - job_name: 'spark-master'
    static_configs:
      - targets: ['spark-master:4040']

  - job_name: 'spark-worker'
    static_configs:
      - targets: ['spark-worker:4041']

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka:9308']
EOF

    # Grafana datasource configuration
    cat > monitoring/grafana/provisioning/datasources/datasources.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Elasticsearch
    type: elasticsearch
    access: proxy
    url: http://elasticsearch:9200
    database: logs-*
    interval: Daily
    timeField: "@timestamp"
EOF

    # Database initialization script
    cat > sql/init.sql << 'EOF'
-- Create databases
CREATE DATABASE IF NOT EXISTS analytics;
CREATE DATABASE IF NOT EXISTS monitoring;
CREATE DATABASE IF NOT EXISTS metadata;

-- Create tables for analytics
\c analytics;

CREATE TABLE IF NOT EXISTS user_events (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    properties JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_user_events_user_id ON user_events(user_id);
CREATE INDEX idx_user_events_timestamp ON user_events(timestamp);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_status ON transactions(status);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
EOF

    log "Configuration files generated ✓"
}

# Setup Git hooks
setup_git_hooks() {
    log "Setting up Git hooks..."
    
    if [ -d ".git" ]; then
        # Pre-commit hook
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run code quality checks before commit

echo "Running pre-commit checks..."

# Check Python code style
if command -v black >/dev/null 2>&1; then
    echo "Running black formatter..."
    black --check . || exit 1
fi

if command -v flake8 >/dev/null 2>&1; then
    echo "Running flake8 linter..."
    flake8 . || exit 1
fi

# Check for secrets
if command -v git-secrets >/dev/null 2>&1; then
    echo "Checking for secrets..."
    git secrets --scan || exit 1
fi

echo "Pre-commit checks passed ✓"
EOF
        
        chmod +x .git/hooks/pre-commit
        log "Git pre-commit hook installed"
    else
        warn "Not a Git repository. Skipping Git hooks setup."
    fi
}

# Create example files
create_examples() {
    log "Creating example files..."
    
    # Spark batch processing example
    cat > spark-projects/batch-processing/word_count.py << 'EOF'
"""
Production Spark Batch Processing Example
Word Count with optimizations and monitoring
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, split, lower, regexp_replace, col
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spark_session(app_name="WordCount"):
    """Create optimized Spark session"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

def process_text_data(spark, input_path, output_path):
    """Process text data and count words"""
    logger.info(f"Reading data from {input_path}")
    
    # Read text files
    df = spark.read.text(input_path)
    
    # Clean and split text into words
    words_df = df.select(
        explode(
            split(
                regexp_replace(
                    lower(col("value")), 
                    "[^a-z\\s]", 
                    ""
                ), 
                "\\s+"
            )
        ).alias("word")
    ).filter(col("word") != "")
    
    # Count words
    word_counts = words_df.groupBy("word").count() \
        .orderBy(col("count").desc())
    
    logger.info(f"Writing results to {output_path}")
    
    # Write results
    word_counts.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv(output_path)
    
    return word_counts

def main():
    spark = create_spark_session()
    
    try:
        input_path = "/opt/spark-apps/data/raw/text/*.txt"
        output_path = "/opt/spark-apps/data/output/word_count"
        
        result = process_text_data(spark, input_path, output_path)
        
        logger.info("Top 10 words:")
        result.show(10)
        
    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
EOF

    # Flink streaming example
    cat > flink-projects/stream-processing/kafka_processor.py << 'EOF'
"""
Production Flink Streaming Example
Real-time Kafka stream processing with state management
"""

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_kafka_source():
    """Create Kafka source connector"""
    return FlinkKafkaConsumer(
        topics="user-events",
        deserialization_schema=SimpleStringSchema(),
        properties={
            "bootstrap.servers": "kafka:9092",
            "group.id": "flink-consumer-group",
            "auto.offset.reset": "latest"
        }
    )

def create_kafka_sink():
    """Create Kafka sink connector"""
    return FlinkKafkaProducer(
        topic="processed-events",
        serialization_schema=SimpleStringSchema(),
        producer_config={
            "bootstrap.servers": "kafka:9092"
        }
    )

def process_event(event_json):
    """Process individual event"""
    try:
        event = json.loads(event_json)
        
        # Add processing timestamp
        event["processed_at"] = int(time.time() * 1000)
        
        # Enrich event data
        if event.get("event_type") == "purchase":
            event["category"] = "transaction"
        elif event.get("event_type") == "page_view":
            event["category"] = "engagement"
        else:
            event["category"] = "other"
        
        return json.dumps(event)
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        return None

def main():
    # Create execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)
    
    # Enable checkpointing
    env.enable_checkpointing(60000)  # 60 seconds
    
    # Create Kafka source
    kafka_source = create_kafka_source()
    
    # Create stream from Kafka
    stream = env.add_source(kafka_source)
    
    # Process events
    processed_stream = stream.map(
        process_event,
        output_type=Types.STRING()
    ).filter(lambda x: x is not None)
    
    # Create Kafka sink
    kafka_sink = create_kafka_sink()
    
    # Write to Kafka
    processed_stream.add_sink(kafka_sink)
    
    # Execute
    env.execute("Kafka Stream Processor")

if __name__ == "__main__":
    main()
EOF

    log "Example files created ✓"
}

# Main execution
main() {
    log "Starting production data platform setup..."
    
    check_prerequisites
    create_directories
    setup_python_env
    generate_configs
    setup_git_hooks
    create_examples
    
    log ""
    log "🎉 Production data platform setup completed successfully!"
    log ""
    log "Next steps:"
    log "1. Review configuration files in config/ directory"
    log "2. Start the platform: docker-compose up -d"
    log "3. Access services:"
    log "   - Flink Dashboard: http://localhost:8081"
    log "   - Spark Master UI: http://localhost:8080"
    log "   - Grafana: http://localhost:3000 (admin/admin123)"
    log "   - Jupyter: http://localhost:8888 (token: admin123)"
    log "   - Kafka UI: Use kafka-topics commands"
    log "4. Run example jobs: ./scripts/run-example.sh"
    log ""
}

# Run main function
main "$@"