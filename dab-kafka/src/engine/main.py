import argparse
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr, window
from pyspark.sql.types import StructType,ArrayType,StringType,TimestampType
from engine.utils import get_product_config
import logging
from engine.gold import run_gold
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_bronze(spark: SparkSession, config: dict):
    """Reads from Kafka and writes to the Bronze table."""
    logging.info("Starting Bronze step...")
    bronze_table = config["bronze"]["table"]
    checkpoint_path = config["bronze"]["checkpoint_path"]
    topic = config["source"]["topic"]
    schema_string = config["bronze"]["schema_string"]
    
    logging.info(f"Source topic: {topic}")
    logging.info(f"Bronze table: {bronze_table}")
    logging.info(f"Checkpoint path: {checkpoint_path}")

    # Define schema for parsing JSON from Kafka
    schema = StructType.fromDDL(schema_string)
    KAFKA_BOOTSTRAP_SERVERS = "ehns-data-platform-dev.servicebus.windows.net:9093"
    
    # --- Integration of your Databricks Secret ---

    # Securely fetch the connection string from the Databricks secret scope
    connection_string = dbutils.secrets.get('data_products','orders-connection-string')

    # This string configures the SASL PLAIN mechanism for authentication.
    sasl_jaas_config = f'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="$ConnectionString" password="{connection_string}";'

    # Read from Kafka with the necessary authentication options
    df = (spark.readStream
          .format("kafka")
          .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
          .option("subscribe", topic)
          .option("kafka.security.protocol", "SASL_SSL")
          .option("kafka.sasl.mechanism", "PLAIN")
          .option("kafka.sasl.jaas.config", sasl_jaas_config)
          .option("startingOffsets", "earliest")
          .load())

    # --- End of Changes ---

    # Deserialize JSON and select columns
    json_df = df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")  # type: ignore

    # Write to Bronze table with schema evolution
    logging.info("Writing to Bronze table with schema evolution enabled.")
    query = (json_df.writeStream
     .format("delta")
     .outputMode("append")
     .option("checkpointLocation", checkpoint_path)
     .option("mergeSchema", "true")
     .trigger(availableNow=True)
     .toTable(bronze_table))
    
    return query

def run_silver(spark: SparkSession, config: dict):
    """Reads from Bronze, applies transformations, and writes to Silver."""
    logging.info("Starting Silver step...")
    bronze_table = config["bronze"]["table"]
    silver_table = config["silver"]["table"]
    checkpoint_path = config["silver"]["checkpoint_path"]
    
    logging.info(f"Reading from Bronze table: {bronze_table}")
    df = spark.readStream.format("delta").table(bronze_table)

    # Apply transformations
    transformations = config["silver"]["transformations"]
    logging.info(f"Applying transformations: {transformations}")
    for transformation in transformations:
        parts = transformation.split(" as ")
        df = df.withColumn(parts[1].strip(), expr(parts[0].strip()))

    # Apply enrichments
    enrichments = config["silver"]["enrichments"]
    logging.info(f"Applying enrichments: {enrichments}")
    for enrichment in enrichments:
        parts = enrichment.split(" AS ")
        df = df.withColumn(parts[1].strip(), expr(parts[0].strip()))

    # Apply filters
    if "filters" in config["silver"]:
        filters = config["silver"]["filters"]
        logging.info(f"Applying filters: {filters}")
        for filter_cond in filters:
            df = df.filter(filter_cond)

    logging.info(f"Writing to Silver table: {silver_table}")
    query = (df.writeStream
     .format("delta")
     .outputMode("append")
     .option("checkpointLocation", checkpoint_path)
     .trigger(availableNow=True)
     .toTable(silver_table))
     
     
    return query


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-config-folder", required=True, help="Path to the folder containing data_products.yml")
    parser.add_argument("--product-name", required=True, help="Name of the data product to process.")
    parser.add_argument("--step", choices=["bronze", "silver", "gold"], required=True, help="The processing step to run.")
    args = parser.parse_args()

    logging.info(f"Loading configuration for product: {args.product_name}")
    product_config = get_product_config(product_config_folder=args.product_config_folder,product_name=args.product_name)
    
    spark = SparkSession.builder.appName(f"{args.product_name} - {args.step}").getOrCreate()

    query = None
    logging.info(f"Executing step: {args.step}")
    if args.step == "bronze":
        query = run_bronze(spark, product_config)
    elif args.step == "silver":
        query = run_silver(spark, product_config)
    elif args.step == "gold":
        query = run_gold(spark, product_config)
    
    if query:
        logging.info("Awaiting stream termination...")
        query.awaitTermination()
        logging.info("Stream terminated.")