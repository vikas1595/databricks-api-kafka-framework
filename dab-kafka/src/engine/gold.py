
from delta.tables import DeltaTable
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr, window
from pyspark.sql.types import StructType,ArrayType,StringType,TimestampType
from engine.utils import get_product_config
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GoldUpserter:
    """
    A class that encapsulates the logic for writing to the Gold table.
    It now uses the Spark Catalog to check for table existence.
    """
    def __init__(self, spark: SparkSession, config: dict):
        self.spark = spark
        self.config = config

    def __call__(self, micro_batch_df, epoch_id: int):
        """
        This method is executed by foreachBatch for each micro-batch.
        It checks if the target table exists and decides whether to create it or merge into it.
        """
        gold_table = self.config["gold"]["table"]
        
        # CORRECTED LOGIC: Use spark.catalog.tableExists, which is more reliable for managed tables.
        if not self.spark.catalog.tableExists(gold_table):
            logging.info(f"Epoch {epoch_id}: Gold table '{gold_table}' not found in catalog. Creating it now.")
            (micro_batch_df.write
             .format("delta")
             .mode("overwrite")
             .option("overwriteSchema", "true")
             .saveAsTable(gold_table))
        else:
            logging.info(f"Epoch {epoch_id}: Gold table '{gold_table}' found. Merging data.")
            
            delta_target = DeltaTable.forName(self.spark, gold_table)
            agg_config = self.config["gold"]["aggregation"]
            group_by_cols = agg_config["group_by"]
            window_config = agg_config.get("window")

            merge_keys = group_by_cols
            if window_config:
                merge_keys = ["window"] + merge_keys
            
            merge_condition = " AND ".join([f"target.{key} = source.{key}" for key in merge_keys])

            (delta_target.alias("target")
             .merge(micro_batch_df.alias("source"), condition=merge_condition)
             .whenMatchedUpdateAll()
             .whenNotMatchedInsertAll()
             .execute())

def run_gold(spark: SparkSession, config: dict):
    """
    Main function to run the Gold layer processing.
    """
    logging.info("Starting Gold step...")
    silver_table = config["silver"]["table"]
    checkpoint_path = config["gold"]["checkpoint_path"]
    
    df = spark.readStream.format("delta").table(silver_table)
    
    agg_config = config["gold"]["aggregation"]
    group_by_cols = agg_config["group_by"]
    window_config = agg_config.get("window")
    agg_exprs = [expr(e) for e in agg_config["expressions"]]

    if window_config:
        aggregated_df = (df
            .groupBy(
                window(col(window_config["time_column"]), window_config["duration"]),
                *[col(c) for c in group_by_cols]
            ).agg(*agg_exprs)
        )
    else:
        aggregated_df = df.groupBy(*[col(c) for c in group_by_cols]).agg(*agg_exprs)

    upserter = GoldUpserter(spark, config)
    
    query = (aggregated_df.writeStream
             .foreachBatch(upserter)
             .outputMode("update")
             .option("checkpointLocation", checkpoint_path)
             .trigger(availableNow=True)
             .start())
             
    query.awaitTermination()
    logging.info("Gold step finished.")
    return query