import requests

headers = {
    "X-RapidAPI-Key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379",
    "X-RapidAPI-Host": "reddit3.p.rapidapi.com"
}

# From the user's screenshot, the sidebar shows these endpoints:
endpoints = [
    ("/v1/reddit/search", {"search": "investing"}),
    ("/v1/reddit/posts", {"subreddit": "SaaS"}),
    ("/v1/reddit/post-details (incl. comments)", {"post_id": "test"}),
    ("/v1/reddit/subreddit/popular", {"name": "SaaS"}),
    ("/v1/reddit/subreddit/info", {"name": "SaaS"}),
    ("/v1/reddit/subreddit/new", {"name": "SaaS"}),
    ("/v1/reddit/subreddit/comments", {"name": "SaaS"}),
    ("/v1/reddit/user-stats", {"username": "test"}),
    ("/v1/reddit/user-data", {"username": "test"}),
]

for ep, params in endpoints:
    try:
        url = f"https://reddit3.p.rapidapi.com{ep}"
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            keys = list(data.keys()) if isinstance(data, dict) else f"[array of {len(data)}]"
            body = data.get("body", "")
            body_info = f" body_type={type(body).__name__}"
            if isinstance(body, list):
                body_info += f" body_len={len(body)}"
            print(f"✅ {ep}: 200 keys={keys}{body_info}")
        else:
            print(f"❌ {ep}: {res.status_code} - {res.text[:80]}")
    except Exception as e:
        print(f"💥 {ep}: {e}")
