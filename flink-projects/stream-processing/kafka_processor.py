#!/usr/bin/env python3
"""
Flink Kafka Stream Processing Example
Real-time event processing with Flink PyFlink
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

from pyflink.common import Configuration, Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.datastream.functions import MapFunction, FilterFunction, ReduceFunction
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.common.time import Time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventParser(MapFunction):
    """Parse JSON events from Kafka"""
    
    def map(self, value: str) -> Dict[str, Any]:
        try:
            event = json.loads(value)
            event['processing_time'] = datetime.now().isoformat()
            event['timestamp_dt'] = datetime.fromtimestamp(event['timestamp'] / 1000).isoformat()
            return event
        except Exception as e:
            logger.error(f"Error parsing event: {e}")
            return {"error": str(e), "original": value}


class EventFilter(FilterFunction):
    """Filter out invalid events"""
    
    def filter(self, event: Dict[str, Any]) -> bool:
        return 'error' not in event and 'user_id' in event


class EventEnricher(MapFunction):
    """Enrich events with additional metadata"""
    
    def map(self, event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Add session information
            event['session_id'] = f"{event['user_id']}_{datetime.now().strftime('%Y%m%d_%H')}"
            
            # Add event category
            if event['event_type'] in ['page_view', 'scroll', 'hover']:
                event['category'] = 'engagement'
            elif event['event_type'] in ['click', 'submit', 'download']:
                event['category'] = 'action'
            elif event['event_type'] in ['purchase', 'cart_add', 'checkout']:
                event['category'] = 'conversion'
            else:
                event['category'] = 'other'
            
            # Add page category
            page = event.get('page', '')
            if '/product' in page or '/shop' in page:
                event['page_category'] = 'product'
            elif '/cart' in page or '/checkout' in page:
                event['page_category'] = 'transaction'
            elif '/home' in page or page == '/':
                event['page_category'] = 'landing'
            else:
                event['page_category'] = 'other'
            
            return event
        except Exception as e:
            logger.error(f"Error enriching event: {e}")
            event['enrichment_error'] = str(e)
            return event


class EventCounter(ReduceFunction):
    """Count events in windows"""
    
    def reduce(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> Dict[str, Any]:
        count1 = event1.get('count', 1)
        count2 = event2.get('count', 1)
        
        return {
            'event_type': event1.get('event_type', 'unknown'),
            'category': event1.get('category', 'unknown'),
            'count': count1 + count2,
            'window_start': min(
                event1.get('processing_time', ''),
                event2.get('processing_time', '')
            ),
            'last_updated': datetime.now().isoformat()
        }


class UserActivityAggregator(MapFunction):
    """Aggregate user activity"""
    
    def map(self, events: list) -> Dict[str, Any]:
        if not events:
            return {}
        
        user_id = events[0].get('user_id')
        unique_pages = set()
        unique_event_types = set()
        categories = set()
        
        for event in events:
            unique_pages.add(event.get('page', ''))
            unique_event_types.add(event.get('event_type', ''))
            categories.add(event.get('category', ''))
        
        return {
            'user_id': user_id,
            'event_count': len(events),
            'unique_pages': len(unique_pages),
            'unique_event_types': len(unique_event_types),
            'categories': list(categories),
            'pages_visited': list(unique_pages),
            'session_start': min(e.get('processing_time', '') for e in events),
            'session_end': max(e.get('processing_time', '') for e in events),
            'processing_time': datetime.now().isoformat()
        }


def create_kafka_consumer():
    """Create Kafka consumer for input events"""
    properties = {
        'bootstrap.servers': 'kafka:29092',
        'group.id': 'flink-processor',
        'auto.offset.reset': 'latest'
    }
    
    return FlinkKafkaConsumer(
        topics='user-events',
        deserialization_schema=SimpleStringSchema(),
        properties=properties
    )


def create_kafka_producer(topic: str):
    """Create Kafka producer for output"""
    properties = {
        'bootstrap.servers': 'kafka:29092'
    }
    
    return FlinkKafkaProducer(
        topic=topic,
        serialization_schema=SimpleStringSchema(),
        producer_config=properties
    )


def setup_environment():
    """Setup Flink execution environment"""
    # Configuration
    config = Configuration()
    config.set_string("parallelism.default", "2")
    config.set_string("pipeline.auto-watermark-interval", "1000")
    config.set_string("state.backend", "filesystem")
    config.set_string("state.checkpoints.dir", "file:///opt/flink-apps/checkpoints")
    config.set_string("execution.checkpointing.interval", "60000")  # 1 minute
    config.set_string("execution.checkpointing.min-pause", "30000")  # 30 seconds
    
    # Create environment
    env = StreamExecutionEnvironment.get_execution_environment(config)
    env.set_parallelism(2)
    env.enable_checkpointing(60000)  # Checkpoint every minute
    
    # Add Kafka connector JAR
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-1.17.1.jar")
    
    return env


def main():
    """Main Flink streaming job"""
    try:
        logger.info("Starting Flink Kafka Stream Processing Job")
        
        # Setup environment
        env = setup_environment()
        
        # Create Kafka consumer
        kafka_consumer = create_kafka_consumer()
        
        # Create main data stream
        raw_stream = env.add_source(kafka_consumer)
        
        # Parse and filter events
        parsed_stream = raw_stream.map(EventParser()) \
                                 .filter(EventFilter())
        
        # Enrich events
        enriched_stream = parsed_stream.map(EventEnricher())
        
        # Stream 1: Real-time event counts per type (1-minute tumbling windows)
        event_counts = enriched_stream \
            .key_by(lambda event: event['event_type']) \
            .window(TumblingProcessingTimeWindows.of(Time.minutes(1))) \
            .reduce(EventCounter()) \
            .map(lambda event: json.dumps(event))
        
        # Output event counts to Kafka
        event_counts_producer = create_kafka_producer('event-counts')
        event_counts.add_sink(event_counts_producer)
        
        # Stream 2: User activity aggregation (5-minute tumbling windows)
        user_activity = enriched_stream \
            .key_by(lambda event: event['user_id']) \
            .window(TumblingProcessingTimeWindows.of(Time.minutes(5))) \
            .apply(UserActivityAggregator()) \
            .map(lambda activity: json.dumps(activity))
        
        # Output user activity to Kafka
        user_activity_producer = create_kafka_producer('user-activity')
        user_activity.add_sink(user_activity_producer)
        
        # Stream 3: Processed events for downstream consumption
        processed_events = enriched_stream.map(lambda event: json.dumps(event))
        processed_events_producer = create_kafka_producer('processed-events')
        processed_events.add_sink(processed_events_producer)
        
        # Stream 4: Print to console for monitoring
        enriched_stream.print("Processed Event")
        
        # Execute the job
        logger.info("Submitting Flink job...")
        env.execute("ProductionFlinkKafkaProcessor")
        
    except Exception as e:
        logger.error(f"Flink job failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
