import requests

url = "http://127.0.0.1:8000/mcp"

header = {
    "Accept":"application/json,text/event-stream"
}
# body = {
#     "jsonrpc": "2.0",
#     "method": "tools/list",
#     "id":1,
#     "params": {}
# }
body = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id":1,
    "params": {
        "name":"get_weather",
        "arguments":{
            "city":"Lahore"
        }
    }
}

response = requests.post(url,headers=header,json=body)
print(response.text)