#!/bin/bash

# Script to run example data processing jobs
# Usage: ./run-example.sh [spark-batch|spark-streaming|flink-streaming|all]

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

# Check if Docker containers are running
check_services() {
    log "Checking if services are running..."
    
    if ! docker-compose ps | grep -q "Up"; then
        error "Services are not running. Please start with: docker-compose up -d"
    fi
    
    log "Services are running ✓"
}

# Create sample data
create_sample_data() {
    log "Creating sample data..."
    
    # Create text data for Spark batch processing
    mkdir -p data/raw/text
    cat > data/raw/text/sample.txt << 'EOF'
Apache Spark is a unified analytics engine for large-scale data processing.
Apache Flink is a framework and distributed processing engine for stateful computations.
Both are powerful tools for big data processing and analytics.
Spark excels at batch processing while Flink is optimized for stream processing.
Together they provide comprehensive data processing capabilities.
EOF

    # Create sample events for Kafka
    docker-compose exec -T kafka kafka-topics --create \
        --topic user-events \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 || true

    docker-compose exec -T kafka kafka-topics --create \
        --topic processed-events \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 || true

    # Send sample events to Kafka
    for i in {1..10}; do
        echo "{\"user_id\":\"user_$i\",\"event_type\":\"page_view\",\"timestamp\":$(date +%s)000,\"page\":\"/home\"}" | \
        docker-compose exec -T kafka kafka-console-producer \
            --topic user-events \
            --bootstrap-server localhost:9092
    done

    log "Sample data created ✓"
}

# Run Spark batch processing example
run_spark_batch() {
    log "Running Spark batch processing example..."
    
    docker-compose exec spark-master spark-submit \
        --master spark://spark-master:7077 \
        --deploy-mode client \
        --class org.apache.spark.examples.SparkPi \
        /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 10
    
    log "Spark batch job completed ✓"
}

# Run Spark streaming example
run_spark_streaming() {
    log "Running Spark streaming example..."
    
    docker-compose exec spark-master spark-submit \
        --master spark://spark-master:7077 \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
        /opt/spark-apps/src/streaming/kafka_stream_processor.py
    
    log "Spark streaming job started ✓"
}

# Run Flink streaming example
run_flink_streaming() {
    log "Running Flink streaming example..."
    
    docker-compose exec flink-jobmanager flink run \
        -py /opt/flink-apps/src/stream-processing/kafka_processor.py
    
    log "Flink streaming job submitted ✓"
}

# Run ML pipeline example
run_ml_pipeline() {
    log "Running ML pipeline example..."
    
    docker-compose exec spark-master spark-submit \
        --master spark://spark-master:7077 \
        --packages org.apache.spark:spark-mllib_2.12:3.5.0 \
        /opt/spark-apps/src/ml-pipelines/recommendation_engine.py
    
    log "ML pipeline completed ✓"
}

# Monitor jobs
monitor_jobs() {
    log "Monitoring running jobs..."
    
    echo "Flink Jobs:"
    docker-compose exec flink-jobmanager flink list || true
    
    echo ""
    echo "Spark Applications:"
    curl -s http://localhost:8080/json | jq '.activeapps[]? | {id: .id, name: .name, state: .state}' || true
    
    echo ""
    echo "Access UIs:"
    echo "- Flink Dashboard: http://localhost:8081"
    echo "- Spark Master UI: http://localhost:8080"
    echo "- Grafana Dashboards: http://localhost:3000"
}

# Main function
main() {
    local example_type=${1:-"help"}
    
    case $example_type in
        "spark-batch")
            check_services
            create_sample_data
            run_spark_batch
            ;;
        "spark-streaming")
            check_services
            create_sample_data
            run_spark_streaming
            ;;
        "flink-streaming")
            check_services
            create_sample_data
            run_flink_streaming
            ;;
        "ml-pipeline")
            check_services
            create_sample_data
            run_ml_pipeline
            ;;
        "all")
            check_services
            create_sample_data
            run_spark_batch
            run_spark_streaming
            run_flink_streaming
            run_ml_pipeline
            monitor_jobs
            ;;
        "monitor")
            monitor_jobs
            ;;
        "help"|*)
            echo "Usage: $0 [spark-batch|spark-streaming|flink-streaming|ml-pipeline|all|monitor]"
            echo ""
            echo "Examples:"
            echo "  $0 spark-batch      # Run Spark batch processing example"
            echo "  $0 spark-streaming  # Run Spark streaming example"
            echo "  $0 flink-streaming  # Run Flink streaming example"
            echo "  $0 ml-pipeline      # Run ML pipeline example"
            echo "  $0 all              # Run all examples"
            echo "  $0 monitor          # Monitor running jobs"
            ;;
    esac
}

main "$@"