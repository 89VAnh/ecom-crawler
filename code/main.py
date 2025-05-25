from crawler.playwright_crawler import Crawler
import json
import os
import asyncio
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def read_config(path: str) -> dict:
    """Read and parse a JSON config file."""
    try:
        with open(path, mode="r") as f:
            return json.load(f)  # Use json.load for direct file parsing
    except FileNotFoundError:
        logging.error(f"Config file not found: {path}")
        raise
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in config file: {path}")
        raise
    except Exception as e:
        logging.error(f"Error reading config {path}: {str(e)}")
        raise


async def run(pipeline_name: str) -> dict:
    """Run the crawler with the given config file."""
    try:
        config = read_config(pipeline_name)
        crawler = Crawler(config["pipeline"])  # Fixed: config["pipeline"]
        results = await crawler.run()
        return {"message": "Crawler executed successfully", "results": results}
    except Exception as e:
        logging.error(f"Error running crawler for {pipeline_name}: {str(e)}")
        raise


async def main():
    """Run the crawler for all config files in the directory."""
    path = "./config/generator/result/"
    try:
        files = os.listdir(path)
        for i, file in enumerate(files, start=1):
            config_path = os.path.join(path, file)  # Robust path construction
            try:
                result = await run(config_path)
                logging.info(
                    f"Success {i}/{len(files)}: {config_path} - {result['message']}"
                )
            except Exception as e:
                logging.error(f"Error {i}/{len(files)}: {config_path} - {str(e)}")
    except Exception as e:
        logging.error(f"Error accessing directory {path}: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())  # Run the async main function
