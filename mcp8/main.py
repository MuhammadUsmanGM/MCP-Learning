from mcp.server.fastmcp import FastMCP
import json
from bson import json_util
from datetime import datetime
from typing import Any
from pymongo import MongoClient
from my_secrets import Secrets


def mongo_json_encoder(obj: Any) -> Any:
    """
    Custom JSON encoder to handle MongoDB-specific data types like ObjectId and datetime.
    """
    if hasattr(obj, 'isoformat'):  # datetime objects
        return obj.isoformat()
    return json_util.default(obj)


secrets = Secrets()

mongo_client = MongoClient(secrets.mongo_uri)
db = mongo_client[secrets.mongo_db]                   
books_col = db[secrets.books_col]
members_col = db[secrets.members_col]

mcp = FastMCP(name="MCP_APP",stateless_http=True)

# --- Books Tool ---
@mcp.tool(name="search_books",
            description="Search documents in the Books collection to get the info about any of the books that is in the collection.")
def search_books(query: str) -> str:
    try:
        # Try to parse as JSON first
        try:
            filter_dict = json.loads(query)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat it as a simple text search query
            # Create a case-insensitive search across common fields
            filter_dict = {
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"author": {"$regex": query, "$options": "i"}},
                    {"genre": {"$regex": query, "$options": "i"}},
                    {"isbn": {"$regex": query, "$options": "i"}}
                ]
            }
        
        docs = list(books_col.find(filter_dict, {"_id": 0}).limit(10))
        # Use the custom encoder to handle MongoDB-specific data types
        return json.dumps(docs, indent=2, default=mongo_json_encoder) if docs else "No books found."
    except Exception as e:
        return f"❌ Error while searching Books: {str(e)}"

# --- Members Tool ---
@mcp.tool(name="search_members",
          description="Search documents in the Members collection to get the info about any of the member that is in the collection.")
def search_members(query: str) -> str:
    try:
        # Try to parse as JSON first
        try:
            filter_dict = json.loads(query)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat it as a simple text search query
            # Create a case-insensitive search across common fields
            filter_dict = {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}},
                    {"member_id": {"$regex": query, "$options": "i"}},
                    {"phone": {"$regex": query, "$options": "i"}}
                ]
            }
        
        docs = list(members_col.find(filter_dict, {"_id": 0}).limit(10))
        # Use the custom encoder to handle MongoDB-specific data types
        return json.dumps(docs, indent=2, default=mongo_json_encoder) if docs else "No members found."
    except Exception as e:
        return f"❌ Error while searching Members: {str(e)}"


@mcp.prompt(name="instructions")
def instructions():
    """
    You can pass MongoDB queries as JSON strings to search_books or search_members.
    If you pass a simple text string instead of JSON, it will be converted to a 
    case-insensitive search across relevant fields (title, author, genre for books; 
    name, email, member_id for members).
    """

mcp_app = mcp.streamable_http_app()