#!/usr/bin/env python3
"""
Spark Streaming with Kafka Example
Real-time processing of user events from Kafka
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spark_session(app_name="SparkKafkaStreaming"):
    """Create Spark session with Kafka support"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.streaming.checkpointLocation", "/opt/spark-apps/checkpoints") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()

def process_kafka_stream(spark):
    """Process Kafka stream data"""
    try:
        logger.info("Starting Kafka stream processing")
        
        # Define schema for incoming JSON data
        event_schema = StructType([
            StructField("user_id", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("timestamp", LongType(), True),
            StructField("page", StringType(), True),
            StructField("properties", MapType(StringType(), StringType()), True)
        ])
        
        # Read from Kafka
        kafka_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "kafka:29092") \
            .option("subscribe", "user-events") \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()
        
        # Parse JSON data
        parsed_df = kafka_df.select(
            col("key").cast("string").alias("key"),
            from_json(col("value").cast("string"), event_schema).alias("data"),
            col("timestamp").alias("kafka_timestamp"),
            col("partition"),
            col("offset")
        ).select("key", "data.*", "kafka_timestamp", "partition", "offset")
        
        # Add processing timestamp and derived fields
        enriched_df = parsed_df \
            .withColumn("processing_time", current_timestamp()) \
            .withColumn("event_date", to_date(from_unixtime(col("timestamp") / 1000))) \
            .withColumn("event_hour", hour(from_unixtime(col("timestamp") / 1000))) \
            .withColumn("is_weekend", 
                       when(dayofweek(from_unixtime(col("timestamp") / 1000)).isin([1, 7]), True)
                       .otherwise(False))
        
        # Real-time aggregations - events per minute
        events_per_minute = enriched_df \
            .withWatermark("processing_time", "2 minutes") \
            .groupBy(
                window(col("processing_time"), "1 minute"),
                col("event_type")
            ).count() \
            .select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("event_type"),
                col("count").alias("event_count")
            )
        
        # User activity aggregations - events per user per 5-minute window
        user_activity = enriched_df \
            .withWatermark("processing_time", "5 minutes") \
            .groupBy(
                window(col("processing_time"), "5 minutes"),
                col("user_id")
            ).agg(
                count("*").alias("total_events"),
                countDistinct("event_type").alias("unique_event_types"),
                countDistinct("page").alias("unique_pages"),
                collect_list("event_type").alias("event_sequence")
            ).select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("user_id"),
                col("total_events"),
                col("unique_event_types"),
                col("unique_pages"),
                col("event_sequence")
            )
        
        # Page popularity - most visited pages in 10-minute windows
        page_popularity = enriched_df \
            .filter(col("event_type") == "page_view") \
            .withWatermark("processing_time", "10 minutes") \
            .groupBy(
                window(col("processing_time"), "10 minutes"),
                col("page")
            ).count() \
            .select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("page"),
                col("count").alias("page_views")
            )
        
        # Output sinks
        
        # Console output for debugging
        console_query = enriched_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .option("numRows", 10) \
            .trigger(processingTime="30 seconds") \
            .start()
        
        # Events per minute to console
        events_per_minute_query = events_per_minute.writeStream \
            .outputMode("complete") \
            .format("console") \
            .option("truncate", "false") \
            .trigger(processingTime="1 minute") \
            .queryName("events_per_minute") \
            .start()
        
        # User activity to console
        user_activity_query = user_activity.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .trigger(processingTime="1 minute") \
            .queryName("user_activity") \
            .start()
        
        # Write processed events back to Kafka
        kafka_output_query = enriched_df.select(
            col("user_id").alias("key"),
            to_json(struct(
                col("user_id"),
                col("event_type"),
                col("timestamp"),
                col("page"),
                col("processing_time"),
                col("event_date"),
                col("event_hour"),
                col("is_weekend")
            )).alias("value")
        ).writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "kafka:29092") \
            .option("topic", "processed-events") \
            .option("checkpointLocation", "/opt/spark-apps/checkpoints/kafka-output") \
            .trigger(processingTime="30 seconds") \
            .start()
        
        logger.info("Streaming queries started successfully")
        
        # Wait for termination
        console_query.awaitTermination()
        
    except Exception as e:
        logger.error(f"Error in Kafka stream processing: {str(e)}")
        raise

def main():
    """Main function"""
    spark = None
    try:
        logger.info("Starting Spark Kafka Streaming Job")
        
        # Create Spark session
        spark = create_spark_session("ProductionSparkStreaming")
        
        # Set log level
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"Spark version: {spark.version}")
        logger.info(f"Spark UI: {spark.sparkContext.uiWebUrl}")
        
        # Process Kafka stream
        process_kafka_stream(spark)
        
        logger.info("Streaming job completed")
        
    except Exception as e:
        logger.error(f"Streaming job failed: {str(e)}")
        sys.exit(1)
    finally:
        if spark:
            spark.stop()

if __name__ == "__main__":
    main()
