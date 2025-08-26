import yaml
import os

def get_product_config(product_config_folder: str, product_name: str):
    """
    Reads the data_products.yml file and returns the configuration for the specified product.
    """
    # The working directory is .../src/engine, so we need to go up two levels
    # to the project root to find the 'config' directory.
    # __file__ gives the path to the current file (utils.py).
    config_path = os.path.join(product_config_folder, f'{product_name}.yml')
    print(f"Loading configuration from: {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    for product in config.get("data_products", []):
        if product.get("product_name") == product_name:
            return product
            
    raise ValueError(f"Product '{product_name}' not found in configuration.")
