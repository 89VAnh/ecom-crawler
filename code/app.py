import asyncio
import logging
import time
from typing import Dict
import aiohttp
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from crawler.playwright_crawler import Crawler
import asyncpg

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),  # Log to a file
        logging.StreamHandler(),  # Log to console
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global dictionary to track running crawler tasks
crawler_tasks: Dict[int, asyncio.Task] = {}


class CrawlerConfig(BaseModel):
    crawlerId: int
    metadata: dict


async def run_crawler_in_background(crawlerId: int, metadata: dict):
    pool = await asyncpg.create_pool(
        host="postgres_db",
        port="5432",
        database="ecom",
        user="user",
        password="password",
    )

    try:
        if metadata["engine"] == "playwright-crawler":
            crawler = Crawler(metadata["pipeline"])
            results = await crawler.run()
            logger.info(f"Results : {results}")
            logger.info("Call glue-dev api")
            # Call the FastAPI job sequence endpoint
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        "http://glue-dev:8010/run-etl-jobs"
                    ) as response:
                        if response.status == 200:
                            api_result = await response.json()
                            logger.info(
                                "ETL job sequence triggered successfully: %s",
                                api_result,
                            )
                            status = "success"
                        else:
                            logger.error(
                                "ETL job sequence failed with status %s: %s",
                                response.status,
                                await response.text(),
                            )
                            status = "failed"
                except aiohttp.ClientError as e:
                    logger.error("Failed to call ETL job sequence API: %s", str(e))
                    status = "failed"

            if asyncio.current_task().cancelled():
                raise asyncio.CancelledError("Crawler task cancelled")
            logger.info("Crawler executed successfully")
            status = "success"
        else:
            logger.error(f"Unsupported engine: {metadata['engine']}")
            status = "failed"

        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE crawlers SET status = $1, last_run = CURRENT_TIMESTAMP
                WHERE crawler_id = $2
                """,
                status,
                crawlerId,
            )
            logger.info(
                f"Successfully saved result to PostgreSQL for crawler {crawlerId}"
            )
    except asyncio.CancelledError:
        logger.info(f"Crawler {crawlerId} was cancelled")
        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE crawlers SET status = $1, last_run = CURRENT_TIMESTAMP
                WHERE crawler_id = $2
                """,
                "paused",
                crawlerId,
            )
            logger.info(
                f"Successfully saved cancellation to PostgreSQL for crawler {crawlerId}"
            )
        raise  # Re-raise to ensure task cleanup
    except Exception as e:
        logger.error(f"Crawler failed: {str(e)}", exc_info=True)
        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE crawlers SET status = $1, last_run = CURRENT_TIMESTAMP
                WHERE crawler_id = $2
                """,
                "failed",
                crawlerId,
            )
            logger.info(
                f"Successfully saved failure to PostgreSQL for crawler {crawlerId}"
            )
    finally:
        await pool.close()
        # Remove task from tracking after completion or cancellation
        if crawlerId in crawler_tasks:
            del crawler_tasks[crawlerId]


@app.post("/run-crawler")
async def run_crawler(config: CrawlerConfig, background_tasks: BackgroundTasks):
    try:
        logger.debug(f"Received data: {config.metadata}, {config.crawlerId}")
        # Create and track the task
        task = asyncio.create_task(
            run_crawler_in_background(config.crawlerId, config.metadata)
        )
        crawler_tasks[config.crawlerId] = task
        background_tasks.add_task(lambda: None)  # Dummy task to satisfy BackgroundTasks
        return {
            "message": "Crawler task accepted and is running in the background",
            "status_code": 202,
        }
    except Exception as e:
        logger.error(f"Failed to start crawler: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start crawler: {str(e)}"
        )


@app.post("/stop-crawler/{crawlerId}")
async def stop_crawler(crawlerId: int):
    try:
        if crawlerId not in crawler_tasks:
            raise HTTPException(
                status_code=404, detail=f"Crawler {crawlerId} not found or not running"
            )

        task = crawler_tasks[crawlerId]
        task.cancel()
        try:
            await task  # Wait for the task to complete cancellation
        except asyncio.CancelledError:
            pass  # Expected behavior on cancellation

        return {
            "message": f"Crawler {crawlerId} stop request accepted",
            "status_code": 200,
        }
    except Exception as e:
        logger.error(f"Failed to stop crawler {crawlerId}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to stop crawler {crawlerId}: {str(e)}"
        )


@app.get("/status")
async def get_status():
    try:
        status = {
            "running_crawlers": [
                {"crawlerId": crawlerId, "status": task.get_name()}
                for crawlerId, task in crawler_tasks.items()
            ]
        }
        return status
    except Exception as e:
        logger.error(f"Failed to retrieve status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve status")


if __name__ == "__main__":
    config = uvicorn.Config("app:app", host="0.0.0.0", port=5000, log_level="info")
    server = uvicorn.Server(config)
    server.run()
