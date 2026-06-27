import requests

url = "https://reddit3.p.rapidapi.com/v1/search"
headers = {
    "X-RapidAPI-Key": "b3a3472908msh0619bdf2c51af7ap120ee5jsna88435723379",
    "X-RapidAPI-Host": "reddit3.p.rapidapi.com"
}
params = {"search": "investing"}

res = requests.get(url, headers=headers, params=params)
print(res.status_code)
print(res.text[:500])

url2 = "https://reddit3.p.rapidapi.com/"
res2 = requests.get(url2, headers=headers, params=params)
print("Root:", res2.status_code)
print(res2.text[:500])

