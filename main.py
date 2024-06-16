import asyncio
import functools
import aiometer
import httpx
import pandas as pd
from scraper import getNovelsByPageNr, getMaxPageNr
from tqdm.asyncio import tqdm
import logging
import logging.config
import json
import os

OUTPUT_DIR = "outputs"
MAX_PAGE = 100

def setup_logging(path='logger_config.json'):
    with open(path, 'rt') as f:
        config = json.load(f)
    logging.config.dictConfig(config)

async def main(client: httpx.AsyncClient, pageNrs: list[int] = [1]):

    novels = list()

    async with aiometer.amap(
        functools.partial(getNovelsByPageNr, client),
        tqdm(pageNrs),
        max_at_once=5,
        max_per_second=3,
    ) as res:
        async for r in res:
            novels.extend(r)

    return novels

if __name__ == "__main__":
    setup_logging()

    client = httpx.AsyncClient()

    max_page = asyncio.run(getMaxPageNr(client))
    print(f"Max page number: {max_page}")

    novels = asyncio.run(main(client, pageNrs=list(range(1, MAX_PAGE+1))))
    df = pd.DataFrame([novel.dict() for novel in novels])

    # make sure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fileName = f"scrape_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    outPath = os.path.join(OUTPUT_DIR, fileName)
    df.to_csv(outPath, index=False)
    