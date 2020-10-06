import requests


# curl 'http://localhost:8080/corpUsers?action=ingest' -X POST -H 'X-RestLi-Protocol-Version:2.0.0'
# --data '{"snapshot": {"aspects": [{"com.linkedin.identity.CorpUserInfo":{"active": true, "displayName": "Foo Bar", "fullName": "Foo Bar", "email": "fbar@linkedin.com"}}, {"com.linkedin.identity.CorpUserEditableInfo":{}}], "urn": "urn:li:corpuser:fbar"}}'

protocol = "http"
url = "localhost:8080"
endpoint = "corpUsers?action=ingest"

users = [
    {
        "ID": "samtest2",
        "DisplayName": "SamTestDisplay",
        "FullName": "SamTestFull",
        "Email": "notarealemail@linkedin.com",
    }
]

for user in users:
    response = requests.post(
        f"{protocol}://{url}/{endpoint}",
        data='{"snapshot": {"aspects": [{"com.linkedin.identity.CorpUserInfo":{"active": true, "displayName": "'
        + user["DisplayName"]
        + '", "fullName": "'
        + user["FullName"]
        + '", "email": "'
        + user["Email"]
        + '"}}, {"com.linkedin.identity.CorpUserEditableInfo":{}}], "urn": "urn:li:corpuser:'
        + user["ID"]
        + '"}}',
        headers={"X-RestLi-Protocol-Version": "2.0.0"},
    )

print("Done")
