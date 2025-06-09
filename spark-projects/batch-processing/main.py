#!/usr/bin/env python3
"""
Spark Batch Processing Example
Processes text data and performs word count analysis
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

def create_spark_session(app_name="SparkBatchProcessor"):
    """Create and configure Spark session"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.adaptive.skewJoin.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()

def process_text_data(spark, input_path="/opt/spark-apps/data/raw/text/*.txt"):
    """Process text data and perform word count"""
    try:
        logger.info(f"Reading text data from: {input_path}")
        
        # Read text files
        df = spark.read.text(input_path)
        
        # Word count processing
        words_df = df.select(
            explode(split(col("value"), "\\s+")).alias("word")
        ).filter(
            col("word") != ""
        ).select(
            lower(regexp_replace(col("word"), "[^a-zA-Z]", "")).alias("clean_word")
        ).filter(
            col("clean_word") != ""
        ).groupBy("clean_word").count().orderBy(desc("count"))
        
        logger.info("Word count processing completed")
        
        # Show results
        words_df.show(20, truncate=False)
        
        # Save results
        output_path = "/opt/spark-apps/data/processed/word_counts"
        words_df.coalesce(1).write.mode("overwrite").parquet(output_path)
        logger.info(f"Results saved to: {output_path}")
        
        return words_df
        
    except Exception as e:
        logger.error(f"Error processing text data: {str(e)}")
        raise

def process_sample_analytics_data(spark):
    """Create and process sample analytics data"""
    try:
        logger.info("Creating sample analytics data")
        
        # Create sample data
        sample_data = [
            ("user_1", "page_view", 1609459200000, "/home"),
            ("user_2", "page_view", 1609459260000, "/products"),
            ("user_1", "click", 1609459320000, "/cart"),
            ("user_3", "page_view", 1609459380000, "/home"),
            ("user_2", "purchase", 1609459440000, "/checkout"),
            ("user_1", "page_view", 1609459500000, "/profile"),
            ("user_3", "click", 1609459560000, "/products"),
            ("user_4", "page_view", 1609459620000, "/home"),
            ("user_2", "page_view", 1609459680000, "/orders"),
            ("user_4", "purchase", 1609459740000, "/checkout")
        ]
        
        schema = StructType([
            StructField("user_id", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("timestamp", LongType(), True),
            StructField("page", StringType(), True)
        ])
        
        events_df = spark.createDataFrame(sample_data, schema)
        
        # Add derived columns
        events_df = events_df.withColumn(
            "event_date", 
            to_date(from_unixtime(col("timestamp") / 1000))
        ).withColumn(
            "event_hour",
            hour(from_unixtime(col("timestamp") / 1000))
        )
        
        # User activity analysis
        user_stats = events_df.groupBy("user_id").agg(
            count("*").alias("total_events"),
            countDistinct("event_type").alias("unique_event_types"),
            countDistinct("page").alias("unique_pages_visited"),
            min("timestamp").alias("first_event"),
            max("timestamp").alias("last_event")
        )
        
        logger.info("User activity statistics:")
        user_stats.show()
        
        # Event type analysis
        event_stats = events_df.groupBy("event_type").agg(
            count("*").alias("event_count"),
            countDistinct("user_id").alias("unique_users")
        ).orderBy(desc("event_count"))
        
        logger.info("Event type statistics:")
        event_stats.show()
        
        # Hourly activity pattern
        hourly_stats = events_df.groupBy("event_hour").agg(
            count("*").alias("events_per_hour")
        ).orderBy("event_hour")
        
        logger.info("Hourly activity pattern:")
        hourly_stats.show()
        
        # Save processed data
        output_base = "/opt/spark-apps/data/processed"
        
        events_df.write.mode("overwrite").parquet(f"{output_base}/events")
        user_stats.write.mode("overwrite").parquet(f"{output_base}/user_stats")
        event_stats.write.mode("overwrite").parquet(f"{output_base}/event_stats")
        
        logger.info("Sample analytics data processing completed")
        
        return events_df, user_stats, event_stats
        
    except Exception as e:
        logger.error(f"Error processing sample analytics data: {str(e)}")
        raise

def main():
    """Main function"""
    spark = None
    try:
        logger.info("Starting Spark Batch Processing Job")
        
        # Create Spark session
        spark = create_spark_session("ProductionSparkBatch")
        
        # Set log level to reduce verbosity
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"Spark version: {spark.version}")
        logger.info(f"Spark UI: {spark.sparkContext.uiWebUrl}")
        
        # Process text data
        if os.path.exists("/opt/spark-apps/data/raw/text"):
            word_counts = process_text_data(spark)
        else:
            logger.warning("Text data directory not found, skipping text processing")
        
        # Process sample analytics data
        events_df, user_stats, event_stats = process_sample_analytics_data(spark)
        
        logger.info("Batch processing job completed successfully")
        
    except Exception as e:
        logger.error(f"Batch processing job failed: {str(e)}")
        sys.exit(1)
    finally:
        if spark:
            spark.stop()

if __name__ == "__main__":
    main()
