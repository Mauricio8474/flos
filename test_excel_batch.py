"""Test batch Excel endpoint."""
import json, urllib.request, io, http.client, uuid, os

BASE = "http://localhost:8000"
r = urllib.request.urlopen(urllib.request.Request(f"{BASE}/auth/login",
    data=json.dumps({"username":"admin","password":"123456789"}).encode(),
    headers={"Content-Type":"application/json"}))
token = json.loads(r.read())["access_token"]

boundary = str(uuid.uuid4())
buf = io.BytesIO()

# File only (use default column indices)
buf.write(f"--{boundary}\r\n".encode())
buf.write(b'Content-Disposition: form-data; name="archivo"; filename="ejemplo_batch.xlsx"\r\n')
buf.write(b"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n")
with open("ejemplo_batch.xlsx", "rb") as f:
    buf.write(f.read())
buf.write(b"\r\n")
buf.write(f"--{boundary}--\r\n".encode())
body = buf.getvalue()

conn = http.client.HTTPConnection("localhost", 8000)
conn.request("POST", "/produccion/calcular-explosion/batch/excel", body=body,
    headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
resp = conn.getresponse()
d = resp.read().decode()
print(f"Status: {resp.status}")
print(f"Body: {d[:1000]}")
conn.close()
