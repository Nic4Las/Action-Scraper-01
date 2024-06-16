import random
import httpx
from selectolax.parser import HTMLParser
from tenacity import after_log, retry, wait_exponential, stop_after_attempt
from .DataTypes import Labels, NovelData
import logging

logger = logging.getLogger(__name__)

async def getMaxPageNr(client: httpx.AsyncClient) -> int:
    url = "https://www.royalroad.com/fictions/search?page=1&orderBy=release_date"
    response = await client.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to get First page: {response.status_code}")
        raise Exception(f"Failed to get page: {response.status_code}")
    tree = HTMLParser(response.text)
    last_page_element = tree.css_first("ul.pagination li:last-child a")
    if last_page_element:
        last_page = int(last_page_element.attributes["data-page"])
    else:
        last_page = 1
    return last_page

async def createTaskByPageNr(client: httpx.AsyncClient, pageNr: int) -> httpx.Response:
    url = (
        f"https://www.royalroad.com/fictions/search?page={pageNr}&orderBy=release_date"
    )
    response = await client.get(url)
    return response


async def parsePage(response: httpx.Response, debug=False) -> list[NovelData]:
    if response.status_code != 200:
        raise Exception(f"Failed to get page: {response.status_code}")
    tree = HTMLParser(response.text)
    novels = []

    for page_num, novel in enumerate(tree.css("div.row.fiction-list-item"), start=1):
        title_element = novel.css_first("h2.fiction-title a")
        title = title_element.text() if title_element else None
        if not title:
            title = "No Title"
            logging.debug(f"Page {page_num}: Fallback used for title: 'No Title'")

        url_element = title_element if title_element else None
        url = "https://www.royalroad.com" + url_element.attributes["href"] if url_element else "No Link"
        if url == "No Link":
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for URL: 'No Link'")

        fiction_id = url.split("/")[-2] if len(url.split("/")) > 2 else -1
        if fiction_id == -1:
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for fiction_id: -1")

        tags = [tag.text() for tag in novel.css("span.tags a")]
        if not tags:
            tags = []
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for tags: []")

        label = novel.css_first("span.label.label-default.label-sm.bg-blue-hoki")
        label_text = label.text() if label else Labels.unknown
        if label_text == Labels.unknown:
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for label: Labels.unknown")

        rating_element = novel.css_first(".star")
        rating = rating_element.attributes["title"] if rating_element else -1
        if rating == -1:
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for rating: -1")

        following_count_element = novel.css_first("i.fa.fa-users").parent.css_first("span")
        if following_count_element:
            following_count = int(following_count_element.text().replace("Followers", "").replace(",", ""))
        else:
            following_count = -1
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for following_count: -1")

        page_count_element = novel.css_first("i.fa.fa-book").parent.css_first("span")
        if page_count_element:
            page_count = int(page_count_element.text().replace("Pages", "").replace(",", ""))
        else:
            page_count = -1
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for page_count: -1")

        view_count_element = novel.css_first("i.fa.fa-eye").parent.css_first("span")
        if view_count_element:
            view_count = int(view_count_element.text().replace("Views", "").replace(",", ""))
        else:
            view_count = -1
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for view_count: -1")

        chapter_count_element = novel.css_first("i.fa.fa-list").parent.css_first("span")
        if chapter_count_element:
            chapter_count = int(chapter_count_element.text().replace("Chapters", "").replace(",", ""))
        else:
            chapter_count = -1
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for chapter_count: -1")

        last_update_element = novel.css_first("i.fa.fa-calendar").parent.css_first("time")
        if last_update_element and last_update_element.attributes.get("unixtime") is not None:
            last_update = int(last_update_element.attributes["unixtime"])
        else:
            last_update = 0
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for last_update: 0")

        description_element = novel.css_first("div.margin-top-10.col-xs-12")
        description = description_element.text().strip() if description_element else "No Description"
        if description == "No Description":
            logging.debug(f"Page {page_num}, Title '{title}': Fallback used for description: 'No Description'")

        novels.append(
            NovelData(
                title=title,
                fiction_id=fiction_id,
                link=url,
                tags=tags,
                lable=label_text,
                following_count=following_count,
                rating=rating,
                page_count=page_count,
                view_count=view_count,
                chapters_count=chapter_count,
                last_update=last_update,
                description=description,
                description_hash=hash(description),
            )
        )

    return novels

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    after=after_log(logger, logging.DEBUG),
)
async def getNovelsByPageNr(client: httpx.AsyncClient, pageNr: int) -> list[NovelData]:
    response = await createTaskByPageNr(client, pageNr)
    return await parsePage(response)
