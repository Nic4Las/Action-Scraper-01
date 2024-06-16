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
MAX_PAGE = 1000
CHUNK_SIZE = 250
INDEX_CHUNK_SIZE = 25000

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


    time = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    db_folder = os.path.join(OUTPUT_DIR, time)

    os.makedirs(db_folder, exist_ok=True)

    # create cunks of CHUNK_SIZE rows and writhe them to json files
    for i, chunk in enumerate(df.groupby(df.index // CHUNK_SIZE)):
        outPath = os.path.join(db_folder, f"scrape_{time}_chunk_{i}")
        chunk[1].to_json(f"{outPath}.json", orient="records")
    
    # dropt the description column and create several index files that contain the index of the json files
    for i, chunk in enumerate(df.groupby(df.index // INDEX_CHUNK_SIZE)):
        outPath = os.path.join(db_folder, f"index_{i}")
        chunkDF = chunk[1].drop(columns=["description"])
        chunkDF["file"] = [f"scrape_{time}_chunk_{i}.json" for i in range(len(chunkDF))]
        chunkDF.to_json(f"{outPath}.json", orient="records")
