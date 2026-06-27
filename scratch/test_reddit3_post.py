import requests

headers = {
    "X-RapidAPI-Key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379",
    "X-RapidAPI-Host": "reddit3.p.rapidapi.com"
}

endpoints = [
    ("/v1/reddit/post-details", {"post_id": "1exrtz2"}),
]

for ep, params in endpoints:
    url = f"https://reddit3.p.rapidapi.com{ep}"
    res = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"{ep}: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"Keys: {list(data.keys())}")
        body = data.get("body", {})
        if isinstance(body, dict):
            print(f"Body keys: {list(body.keys())}")
            comments = body.get("comments", [])
            print(f"Comments count: {len(comments)}")
    else:
        print(res.text[:100])
