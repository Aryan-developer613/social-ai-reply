import requests

endpoints = [
    "/api/v1/search",
    "/v1/reddit/search",
    "/reddit/search",
    "/api/search",
    "/reddit/v1/search"
]

for ep in endpoints:
    url = f"https://reddit3.p.rapidapi.com{ep}"
    headers = {
        "X-RapidAPI-Key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379",
        "X-RapidAPI-Host": "reddit3.p.rapidapi.com"
    }
    params = {"search": "investing"}

    res = requests.get(url, headers=headers, params=params)
    print(f"{ep}: {res.status_code} - {res.text[:100]}")

