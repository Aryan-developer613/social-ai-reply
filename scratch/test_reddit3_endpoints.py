import requests

headers = {
    "X-RapidAPI-Key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379",
    "X-RapidAPI-Host": "reddit3.p.rapidapi.com"
}

endpoints = [
    ("/v1/reddit/search", {"search": "investing"}),
    ("/v1/reddit/subreddit", {"name": "SaaS"}),
    ("/v1/reddit/post-details", {"post_id": "test"}),
    ("/v1/reddit/subreddit/comments", {"name": "SaaS"}),
    ("/v1/reddit/subreddit/new", {"name": "SaaS"}),
]

for ep, params in endpoints:
    url = f"https://reddit3.p.rapidapi.com{ep}"
    res = requests.get(url, headers=headers, params=params)
    print(f"{ep}: {res.status_code} - keys={list(res.json().keys()) if res.status_code == 200 else res.text[:80]}")
