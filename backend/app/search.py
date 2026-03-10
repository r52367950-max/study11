import httpx


async def web_search(query: str, timeout_s: int = 20) -> list[dict]:
    """Simple web search via DuckDuckGo instant answer API.
    Returns a list of {'title','snippet','url'}.
    """
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    results: list[dict] = []
    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        results.append(
            {
                "title": data.get("Heading") or "参考摘要",
                "snippet": abstract,
                "url": data.get("AbstractURL") or "",
            }
        )

    for item in data.get("RelatedTopics", [])[:5]:
        if isinstance(item, dict) and item.get("Text"):
            results.append(
                {
                    "title": "相关结果",
                    "snippet": item.get("Text", ""),
                    "url": item.get("FirstURL", ""),
                }
            )

    return results[:5]
