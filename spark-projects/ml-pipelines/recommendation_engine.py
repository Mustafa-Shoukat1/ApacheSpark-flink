#!/usr/bin/env python3
"""
Spark ML Pipeline Example
User behavior analysis and recommendation engine
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import BinaryClassificationEvaluator, RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_spark_session(app_name="SparkMLPipeline"):
    """Create Spark session with ML libraries"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config("spark.ml.cache.enabled", "true") \
        .getOrCreate()


def create_sample_user_behavior_data(spark):
    """Create sample user behavior data for ML training"""
    try:
        logger.info("Creating sample user behavior data")
        
        # User demographics and behavior data
        user_data = [
            (1, 25, "M", "Engineer", 5, 120, 15, 1),
            (2, 32, "F", "Teacher", 8, 95, 12, 1),
            (3, 28, "M", "Designer", 3, 200, 25, 1),
            (4, 45, "F", "Manager", 12, 80, 8, 0),
            (5, 35, "M", "Developer", 7, 150, 18, 1),
            (6, 29, "F", "Analyst", 4, 110, 14, 1),
            (7, 38, "M", "Consultant", 10, 90, 10, 0),
            (8, 26, "F", "Student", 2, 180, 22, 1),
            (9, 42, "M", "Director", 15, 70, 6, 0),
            (10, 31, "F", "Researcher", 6, 130, 16, 1),
            # Add more diverse data
            (11, 23, "M", "Developer", 1, 250, 30, 1),
            (12, 55, "F", "Executive", 20, 60, 4, 0),
            (13, 27, "M", "Designer", 3, 190, 24, 1),
            (14, 33, "F", "Manager", 8, 100, 11, 1),
            (15, 39, "M", "Analyst", 11, 85, 9, 0),
            (16, 24, "F", "Engineer", 2, 220, 28, 1),
            (17, 41, "M", "Teacher", 13, 75, 7, 0),
            (18, 30, "F", "Consultant", 5, 140, 17, 1),
            (19, 36, "M", "Student", 9, 105, 13, 1),
            (20, 48, "F", "Director", 18, 65, 5, 0)
        ]
        
        user_schema = StructType([
            StructField("user_id", IntegerType(), True),
            StructField("age", IntegerType(), True),
            StructField("gender", StringType(), True),
            StructField("occupation", StringType(), True),
            StructField("experience_years", IntegerType(), True),
            StructField("monthly_sessions", IntegerType(), True),
            StructField("avg_session_duration", IntegerType(), True),
            StructField("is_premium", IntegerType(), True)  # Target variable
        ])
        
        user_df = spark.createDataFrame(user_data, user_schema)
        
        # Product interaction data for recommendation system
        interaction_data = []
        import random
        random.seed(42)
        
        products = list(range(1, 51))  # 50 products
        
        for user_id in range(1, 21):
            # Each user interacts with 10-30 products
            num_interactions = random.randint(10, 30)
            user_products = random.sample(products, num_interactions)
            
            for product_id in user_products:
                rating = random.choice([3.0, 3.5, 4.0, 4.5, 5.0])
                interaction_data.append((user_id, product_id, rating))
        
        interaction_schema = StructType([
            StructField("user_id", IntegerType(), True),
            StructField("product_id", IntegerType(), True),
            StructField("rating", FloatType(), True)
        ])
        
        interaction_df = spark.createDataFrame(interaction_data, interaction_schema)
        
        logger.info(f"Created user data with {user_df.count()} users")
        logger.info(f"Created interaction data with {interaction_df.count()} interactions")
        
        return user_df, interaction_df
        
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        raise


def build_classification_pipeline(user_df):
    """Build ML pipeline for premium user prediction"""
    try:
        logger.info("Building classification pipeline for premium user prediction")
        
        # Feature engineering
        gender_indexer = StringIndexer(inputCol="gender", outputCol="gender_indexed")
        occupation_indexer = StringIndexer(inputCol="occupation", outputCol="occupation_indexed")
        
        # Create feature vector
        feature_cols = ["age", "gender_indexed", "occupation_indexed", 
                       "experience_years", "monthly_sessions", "avg_session_duration"]
        vector_assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
        
        # Scale features
        scaler = StandardScaler(inputCol="features", outputCol="scaled_features")
        
        # Classifier
        rf = RandomForestClassifier(
            featuresCol="scaled_features",
            labelCol="is_premium",
            predictionCol="prediction",
            probabilityCol="probability",
            numTrees=20,
            maxDepth=5,
            seed=42
        )
        
        # Create pipeline
        pipeline = Pipeline(stages=[
            gender_indexer,
            occupation_indexer,
            vector_assembler,
            scaler,
            rf
        ])
        
        # Split data
        train_data, test_data = user_df.randomSplit([0.8, 0.2], seed=42)
        
        logger.info(f"Training data: {train_data.count()} rows")
        logger.info(f"Test data: {test_data.count()} rows")
        
        # Train model
        logger.info("Training classification model...")
        model = pipeline.fit(train_data)
        
        # Make predictions
        predictions = model.transform(test_data)
        
        # Evaluate model
        evaluator = BinaryClassificationEvaluator(
            labelCol="is_premium",
            rawPredictionCol="rawPrediction",
            metricName="areaUnderROC"
        )
        
        auc = evaluator.evaluate(predictions)
        logger.info(f"Model AUC: {auc:.3f}")
        
        # Show predictions
        predictions.select("user_id", "age", "gender", "occupation", 
                          "is_premium", "prediction", "probability").show()
        
        # Feature importance
        feature_importance = model.stages[-1].featureImportances
        feature_names = ["age", "gender", "occupation", "experience_years", 
                        "monthly_sessions", "avg_session_duration"]
        
        logger.info("Feature Importance:")
        for i, importance in enumerate(feature_importance):
            logger.info(f"{feature_names[i]}: {importance:.3f}")
        
        return model, predictions, auc
        
    except Exception as e:
        logger.error(f"Error in classification pipeline: {str(e)}")
        raise


def build_recommendation_system(interaction_df):
    """Build ALS recommendation system"""
    try:
        logger.info("Building ALS recommendation system")
        
        # Split data
        train_data, test_data = interaction_df.randomSplit([0.8, 0.2], seed=42)
        
        logger.info(f"Training interactions: {train_data.count()}")
        logger.info(f"Test interactions: {test_data.count()}")
        
        # Build ALS model
        als = ALS(
            maxIter=10,
            regParam=0.1,
            userCol="user_id",
            itemCol="product_id",
            ratingCol="rating",
            coldStartStrategy="drop",
            seed=42
        )
        
        # Hyperparameter tuning
        param_grid = ParamGridBuilder() \
            .addGrid(als.regParam, [0.01, 0.1, 0.5]) \
            .addGrid(als.rank, [10, 20, 50]) \
            .build()
        
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )
        
        # Cross validation
        cv = CrossValidator(
            estimator=als,
            estimatorParamMaps=param_grid,
            evaluator=evaluator,
            numFolds=3,
            seed=42
        )
        
        logger.info("Training recommendation model with cross-validation...")
        cv_model = cv.fit(train_data)
        
        # Best model
        best_model = cv_model.bestModel
        
        logger.info(f"Best model parameters:")
        logger.info(f"  Rank: {best_model.rank}")
        logger.info(f"  RegParam: {best_model._java_obj.regParam()}")
        
        # Make predictions on test data
        predictions = best_model.transform(test_data)
        rmse = evaluator.evaluate(predictions.filter(col("prediction") != float('nan')))
        logger.info(f"Test RMSE: {rmse:.3f}")
        
        # Generate recommendations for all users
        user_recs = best_model.recommendForAllUsers(5)
        item_recs = best_model.recommendForAllItems(5)
        
        logger.info("Sample user recommendations:")
        user_recs.show(5, truncate=False)
        
        logger.info("Sample item recommendations:")
        item_recs.show(5, truncate=False)
        
        return best_model, user_recs, item_recs, rmse
        
    except Exception as e:
        logger.error(f"Error in recommendation system: {str(e)}")
        raise


def analyze_model_performance(classification_model, recommendation_model, user_df, interaction_df):
    """Analyze and report model performance"""
    try:
        logger.info("Analyzing model performance")
        
        # Classification model analysis
        test_predictions = classification_model.transform(user_df)
        
        # Confusion matrix data
        confusion_data = test_predictions.groupBy("is_premium", "prediction").count().collect()
        
        logger.info("Classification Results Summary:")
        logger.info("Confusion Matrix:")
        for row in confusion_data:
            actual = "Premium" if row.is_premium == 1 else "Basic"
            predicted = "Premium" if row.prediction == 1.0 else "Basic"
            logger.info(f"  Actual: {actual}, Predicted: {predicted}, Count: {row['count']}")
        
        # Recommendation model analysis
        all_users = interaction_df.select("user_id").distinct()
        all_items = interaction_df.select("product_id").distinct()
        
        logger.info(f"Recommendation System Coverage:")
        logger.info(f"  Total users: {all_users.count()}")
        logger.info(f"  Total products: {all_items.count()}")
        logger.info(f"  Total interactions: {interaction_df.count()}")
        
        # User behavior insights
        user_stats = interaction_df.groupBy("user_id").agg(
            count("*").alias("total_interactions"),
            avg("rating").alias("avg_rating"),
            min("rating").alias("min_rating"),
            max("rating").alias("max_rating")
        )
        
        logger.info("User Behavior Statistics:")
        user_stats.describe().show()
        
        # Product popularity
        product_stats = interaction_df.groupBy("product_id").agg(
            count("*").alias("interaction_count"),
            avg("rating").alias("avg_rating")
        ).orderBy(desc("interaction_count"))
        
        logger.info("Top 10 Most Popular Products:")
        product_stats.show(10)
        
        return test_predictions, user_stats, product_stats
        
    except Exception as e:
        logger.error(f"Error in performance analysis: {str(e)}")
        raise


def save_models_and_results(spark, classification_model, recommendation_model, 
                           user_recs, item_recs, predictions):
    """Save models and results"""
    try:
        logger.info("Saving models and results")
        
        base_path = "/opt/spark-apps/data/ml-output"
        
        # Save models
        classification_model.write().overwrite().save(f"{base_path}/classification_model")
        recommendation_model.write().overwrite().save(f"{base_path}/recommendation_model")
        
        # Save recommendations
        user_recs.write.mode("overwrite").parquet(f"{base_path}/user_recommendations")
        item_recs.write.mode("overwrite").parquet(f"{base_path}/item_recommendations")
        
        # Save predictions
        predictions.write.mode("overwrite").parquet(f"{base_path}/premium_predictions")
        
        logger.info(f"Models and results saved to {base_path}")
        
    except Exception as e:
        logger.error(f"Error saving models: {str(e)}")
        raise


def main():
    """Main ML pipeline function"""
    spark = None
    try:
        logger.info("Starting Spark ML Pipeline Job")
        
        # Create Spark session
        spark = create_spark_session("ProductionSparkML")
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"Spark version: {spark.version}")
        logger.info(f"Spark UI: {spark.sparkContext.uiWebUrl}")
        
        # Create sample data
        user_df, interaction_df = create_sample_user_behavior_data(spark)
        
        # Build and train classification model
        classification_model, class_predictions, auc = build_classification_pipeline(user_df)
        
        # Build and train recommendation system
        recommendation_model, user_recs, item_recs, rmse = build_recommendation_system(interaction_df)
        
        # Analyze performance
        test_predictions, user_stats, product_stats = analyze_model_performance(
            classification_model, recommendation_model, user_df, interaction_df
        )
        
        # Save models and results
        save_models_and_results(
            spark, classification_model, recommendation_model,
            user_recs, item_recs, class_predictions
        )
        
        logger.info("ML Pipeline completed successfully")
        logger.info(f"Classification AUC: {auc:.3f}")
        logger.info(f"Recommendation RMSE: {rmse:.3f}")
        
    except Exception as e:
        logger.error(f"ML Pipeline failed: {str(e)}")
        sys.exit(1)
    finally:
        if spark:
            spark.stop()


if __name__ == "__main__":
    main()
