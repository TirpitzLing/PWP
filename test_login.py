import requests

res = requests.post("http://127.0.0.1:5001/api/tokens/", json={"email": "admin@test.com", "pwd": "admin123"})
print(res.status_code)
print(res.text)

res2 = requests.get("http://127.0.0.1:5001/api/users/")
print(res2.status_code)
print(res2.text)
