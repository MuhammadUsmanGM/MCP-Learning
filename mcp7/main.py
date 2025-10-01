from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
import requests
from my_secrets import Secrets

secrets = Secrets()


mcp = FastMCP(name="Agent_SDK",
            stateless_http=True)

@mcp.tool(name="Get_weather",
            description="Get weather for any specific location")
def get_weeather(location:str)->str:
    result = requests.get(
        f"{secrets.weather_base_url}/current.json?key={secrets.weather_api}&q={location}"
    )
    if result.status_code == 200:
        data = result.json()
        return f"Current weather in {data['location']['name']}, {data['location']['region']}, {data['location']['country']} as of {data['location']['localtime']} is {data['current']['temp_c']}°C ({data['current']['condition']['text']}), feels like {data['current']['feelslike_c']}°C, wind {data['current']['wind_kph']} km/h {data['current']['wind_dir']}, humidity {data['current']['humidity']}% and UV index is {data['current']['uv']}."
    else:
        return "Sorry, I couldn't fetch the weather data. Please try again later"

@mcp.tool(name="gte_location",
            description="get location for any ip address")
def get_location(ip_address: str)->str:
    api_token = secrets.ip_api
    try:
        response = requests.get(f"https://ipinfo.io/{ip_address}/json?token={api_token}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            location = f"{data.get('city', 'Unknown city')}, {data.get('region', 'Unknown region')}"
            return (
                f"📍 IP **{ip_address}** is located in **{location}**, **{data.get('country', 'Unknown')}**.\n"
                f"🏢 ISP: {data.get('org', 'N/A')}\n"
                f"🕒 Timezone: {data.get('timezone', 'N/A')}"
            )
        else:
            return f"❌ API request failed with status code {response.status_code}."
    except Exception as e:
        return f"❌ An error occurred while retrieving IP data: {str(e)}"


@mcp.prompt(name="instructions")
def instructions():
    return "You are a helpful assistant have access to tools for getting weather for any location and searching address by any ip."

mcp_app = mcp.streamable_http_app()