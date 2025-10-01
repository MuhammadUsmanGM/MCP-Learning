from mcp.server.fastmcp import FastMCP
import json
from bson import json_util, ObjectId
from datetime import datetime
from typing import Any, Dict, List
from pymongo import MongoClient
import re
from my_secrets import Secrets


def mongo_json_encoder(obj: Any) -> Any:
    """
    Custom JSON encoder to handle MongoDB-specific data types like ObjectId and datetime.
    """
    if hasattr(obj, 'isoformat'):  # datetime objects
        return obj.isoformat()
    return json_util.default(obj)


def parse_natural_language_query(query: str, collection_type: str) -> Dict:
    """
    Parse natural language queries and convert them to MongoDB query format.
    Handles various query patterns like counting, searching by ID, filtering, etc.
    """
    query_lower = query.lower().strip()
    
    # Define field mappings for different collections
    books_fields = ['title', 'author', 'genre', 'isbn', 'published_year', 'pages']
    members_fields = ['name', 'email', 'member_id', 'phone', 'join_date']
    fields = books_fields if collection_type == 'books' else members_fields
    
    # Check for count queries
    if 'count' in query_lower or 'how many' in query_lower or 'number of' in query_lower:
        return {'operation': 'count', 'filter': extract_filter_from_query(query_lower, fields)}
    
    # Check for ID-based queries
    id_patterns = [r'id\s*[:"]?\s*([a-f0-9]{24})', r'_id\s*[:"]?\s*([a-f0-9]{24})']
    for pattern in id_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                return {'operation': 'find', 'filter': {'_id': ObjectId(match.group(1))}}
            except:
                pass
    
    # Check for specific field queries (e.g., "books by author John")
    field_patterns = {
        'author': r'(?:by author|author\s+(?:is|:)?|written by)\s+([^,]+)',
        'title': r'(?:title|book titled|named)\s+([^,]+)',
        'genre': r'(?:genre|category)\s+([^,]+)',
        'name': r'(?:member|person|user)\s+(?:named|called)?\s*([^,]+)',
        'email': r'(?:email|e-mail)\s+([^\s,]+)',
    }
    
    filter_dict = {}
    for field, pattern in field_patterns.items():
        if field in fields:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                value = match.group(1).strip().strip('"\'')
                filter_dict[field] = {'$regex': value, '$options': 'i'}
    
    # Check for year/date filters
    year_match = re.search(r'(?:year|published in|from year)\s+(\d{4})', query_lower)
    if year_match and 'published_year' in fields:
        filter_dict['published_year'] = int(year_match.group(1))
    
    # If we found specific field filters, return them
    if filter_dict:
        return {'operation': 'find', 'filter': filter_dict}
    
    # Default to text search across all relevant fields
    search_terms = extract_search_terms(query)
    if search_terms:
        or_conditions = []
        for field in fields:
            if field not in ['published_year', 'pages', 'join_date']:  # Skip numeric/date fields
                or_conditions.append({field: {'$regex': search_terms, '$options': 'i'}})
        return {'operation': 'find', 'filter': {'$or': or_conditions}}
    
    return {'operation': 'find', 'filter': {}}


def extract_filter_from_query(query: str, fields: List[str]) -> Dict:
    """
    Extract filter conditions from count/aggregation queries.
    """
    filter_dict = {}
    
    # Look for "books by author X" patterns in count queries
    author_match = re.search(r'(?:by|from)\s+author\s+([^,]+)', query, re.IGNORECASE)
    if author_match and 'author' in fields:
        author = author_match.group(1).strip().strip('"\'')
        filter_dict['author'] = {'$regex': author, '$options': 'i'}
    
    # Look for genre filters
    genre_match = re.search(r'(?:genre|category)\s+([^,]+)', query, re.IGNORECASE)
    if genre_match and 'genre' in fields:
        genre = genre_match.group(1).strip().strip('"\'')
        filter_dict['genre'] = {'$regex': genre, '$options': 'i'}
    
    return filter_dict


def extract_search_terms(query: str) -> str:
    """
    Extract the main search terms from a natural language query.
    """
    # Remove common query words and patterns
    stop_words = ['find', 'search', 'get', 'show', 'me', 'the', 'a', 'an', 'is', 'are', 'of', 'for', 'with', 'about']
    words = query.lower().split()
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    return ' '.join(filtered_words) if filtered_words else query


secrets = Secrets()

mongo_client = MongoClient(secrets.mongo_uri)
db = mongo_client[secrets.mongo_db]                   
books_col = db[secrets.books_col]
members_col = db[secrets.members_col]

mcp = FastMCP(name="MCP_APP",stateless_http=True)

# --- Enhanced Books Tools ---
@mcp.tool(name="query_books",
          description="Query books using natural language. Supports searches by title, author, genre, ISBN, publication year, counting books, finding by ID, and complex queries like 'books by Stephen King' or 'count fantasy books' or 'book with id 507f1f77bcf86cd799439011'.")
def query_books(query: str) -> str:
    try:
        # First try to parse as direct JSON
        try:
            filter_dict = json.loads(query)
            parsed_query = {'operation': 'find', 'filter': filter_dict}
        except json.JSONDecodeError:
            # Parse natural language query
            parsed_query = parse_natural_language_query(query, 'books')
        
        # Execute the appropriate operation
        if parsed_query['operation'] == 'count':
            count = books_col.count_documents(parsed_query['filter'])
            filter_desc = json.dumps(parsed_query['filter']) if parsed_query['filter'] else "all books"
            return f"Found {count} books matching filter: {filter_desc}"
        
        elif parsed_query['operation'] == 'find':
            # Include _id in results for ID-based queries, exclude for others
            projection = {} if '_id' in parsed_query['filter'] else {"_id": 0}
            docs = list(books_col.find(parsed_query['filter'], projection).limit(20))
            
            if not docs:
                return "No books found matching your query."
            
            return json.dumps(docs, indent=2, default=mongo_json_encoder)
        
        return "Invalid query operation."
        
    except Exception as e:
        return f"❌ Error while querying books: {str(e)}"


@mcp.tool(name="get_book_by_id",
          description="Get a specific book by its MongoDB ObjectId. Use this when you have an exact ObjectId.")
def get_book_by_id(book_id: str) -> str:
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(book_id)
        book = books_col.find_one({"_id": obj_id})
        
        if book:
            return json.dumps(book, indent=2, default=mongo_json_encoder)
        else:
            return f"No book found with ID: {book_id}"
            
    except Exception as e:
        return f"❌ Error finding book by ID: {str(e)}"


@mcp.tool(name="count_books",
          description="Count books in the collection. Can filter by criteria like 'author: Stephen King', 'genre: fantasy', or use natural language like 'books by author Martin'.")
def count_books(filter_query: str = "") -> str:
    try:
        if not filter_query.strip():
            # Count all books
            count = books_col.count_documents({})
            return f"Total books in collection: {count}"
        
        try:
            # Try parsing as JSON first
            filter_dict = json.loads(filter_query)
        except json.JSONDecodeError:
            # Parse as natural language
            parsed = parse_natural_language_query(f"count {filter_query}", 'books')
            filter_dict = parsed['filter']
        
        count = books_col.count_documents(filter_dict)
        filter_desc = json.dumps(filter_dict) if filter_dict else "all books"
        return f"Found {count} books matching filter: {filter_desc}"
        
    except Exception as e:
        return f"❌ Error counting books: {str(e)}"

# --- Enhanced Members Tools ---
@mcp.tool(name="query_members",
          description="Query members using natural language. Supports searches by name, email, member_id, phone, counting members, finding by ID, and complex queries like 'member named Alice' or 'count all members' or 'member with id 507f1f77bcf86cd799439011'.")
def query_members(query: str) -> str:
    try:
        # First try to parse as direct JSON
        try:
            filter_dict = json.loads(query)
            parsed_query = {'operation': 'find', 'filter': filter_dict}
        except json.JSONDecodeError:
            # Parse natural language query
            parsed_query = parse_natural_language_query(query, 'members')
        
        # Execute the appropriate operation
        if parsed_query['operation'] == 'count':
            count = members_col.count_documents(parsed_query['filter'])
            filter_desc = json.dumps(parsed_query['filter']) if parsed_query['filter'] else "all members"
            return f"Found {count} members matching filter: {filter_desc}"
        
        elif parsed_query['operation'] == 'find':
            # Include _id in results for ID-based queries, exclude for others
            projection = {} if '_id' in parsed_query['filter'] else {"_id": 0}
            docs = list(members_col.find(parsed_query['filter'], projection).limit(20))
            
            if not docs:
                return "No members found matching your query."
            
            return json.dumps(docs, indent=2, default=mongo_json_encoder)
        
        return "Invalid query operation."
        
    except Exception as e:
        return f"❌ Error while querying members: {str(e)}"


@mcp.tool(name="get_member_by_id",
          description="Get a specific member by their MongoDB ObjectId. Use this when you have an exact ObjectId.")
def get_member_by_id(member_id: str) -> str:
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(member_id)
        member = members_col.find_one({"_id": obj_id})
        
        if member:
            return json.dumps(member, indent=2, default=mongo_json_encoder)
        else:
            return f"No member found with ID: {member_id}"
            
    except Exception as e:
        return f"❌ Error finding member by ID: {str(e)}"


@mcp.tool(name="count_members",
          description="Count members in the collection. Can filter by criteria or use natural language like 'members with gmail email'.")
def count_members(filter_query: str = "") -> str:
    try:
        if not filter_query.strip():
            # Count all members
            count = members_col.count_documents({})
            return f"Total members in collection: {count}"
        
        try:
            # Try parsing as JSON first
            filter_dict = json.loads(filter_query)
        except json.JSONDecodeError:
            # Parse as natural language
            parsed = parse_natural_language_query(f"count {filter_query}", 'members')
            filter_dict = parsed['filter']
        
        count = members_col.count_documents(filter_dict)
        filter_desc = json.dumps(filter_dict) if filter_dict else "all members"
        return f"Found {count} members matching filter: {filter_desc}"
        
    except Exception as e:
        return f"❌ Error counting members: {str(e)}"


# --- Comprehensive Search Tool ---
@mcp.tool(name="smart_search",
          description="Intelligent search across both books and members collections. Use natural language queries like 'find all books by Stephen King', 'count members with gmail', 'get book with title Clean Code', 'members named Alice', etc.")
def smart_search(query: str) -> str:
    try:
        query_lower = query.lower()
        
        # Determine which collection(s) to search based on keywords
        book_keywords = ['book', 'books', 'author', 'title', 'isbn', 'genre', 'published', 'pages']
        member_keywords = ['member', 'members', 'user', 'users', 'email', 'phone', 'join']
        
        is_book_query = any(keyword in query_lower for keyword in book_keywords)
        is_member_query = any(keyword in query_lower for keyword in member_keywords)
        
        # If query mentions specific names that might be authors or member names, be more intelligent
        if not is_book_query and not is_member_query:
            # Try to infer from context
            if any(word in query_lower for word in ['named', 'called', 'name', 'who is']):
                # Could be either, search both
                is_book_query = is_member_query = True
            else:
                # Default to searching both
                is_book_query = is_member_query = True
        
        results = []
        
        if is_book_query:
            try:
                book_result = query_books(query)
                if "No books found" not in book_result and "❌ Error" not in book_result:
                    results.append(f"=== BOOKS RESULTS ===")
                    results.append(book_result)
            except Exception as e:
                results.append(f"Books search error: {str(e)}")
        
        if is_member_query:
            try:
                member_result = query_members(query)
                if "No members found" not in member_result and "❌ Error" not in member_result:
                    results.append(f"=== MEMBERS RESULTS ===")
                    results.append(member_result)
            except Exception as e:
                results.append(f"Members search error: {str(e)}")
        
        if results:
            return "\n\n".join(results)
        else:
            return "No results found in books or members collections."
            
    except Exception as e:
        return f"❌ Error in smart search: {str(e)}"


# --- Aggregation Tools ---
@mcp.tool(name="aggregate_books",
          description="Perform aggregation queries on books collection. Examples: 'group by author', 'count by genre', 'books per year', etc.")
def aggregate_books(query: str) -> str:
    try:
        query_lower = query.lower()
        pipeline = []
        
        # Group by author
        if 'author' in query_lower and ('group' in query_lower or 'by author' in query_lower):
            pipeline = [
                {"$group": {"_id": "$author", "count": {"$sum": 1}, "titles": {"$push": "$title"}}},
                {"$sort": {"count": -1}}
            ]
        
        # Group by genre
        elif 'genre' in query_lower and ('group' in query_lower or 'by genre' in query_lower):
            pipeline = [
                {"$group": {"_id": "$genre", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
        
        # Group by year
        elif 'year' in query_lower and ('group' in query_lower or 'by year' in query_lower or 'per year' in query_lower):
            pipeline = [
                {"$group": {"_id": "$published_year", "count": {"$sum": 1}}},
                {"$sort": {"_id": -1}}
            ]
        
        # Average pages
        elif 'average' in query_lower and 'pages' in query_lower:
            pipeline = [
                {"$group": {"_id": None, "avg_pages": {"$avg": "$pages"}, "total_books": {"$sum": 1}}}
            ]
        
        else:
            return "Aggregation query not recognized. Try: 'group by author', 'group by genre', 'group by year', or 'average pages'."
        
        if pipeline:
            results = list(books_col.aggregate(pipeline))
            return json.dumps(results, indent=2, default=mongo_json_encoder) if results else "No aggregation results."
        
    except Exception as e:
        return f"❌ Error in book aggregation: {str(e)}"


@mcp.tool(name="get_database_stats",
          description="Get general statistics about the database collections.")
def get_database_stats() -> str:
    try:
        stats = {
            "database_name": db.name,
            "collections": {
                "books": {
                    "count": books_col.count_documents({}),
                    "sample_fields": list(books_col.find_one({}, {"_id": 0}).keys()) if books_col.find_one() else []
                },
                "members": {
                    "count": members_col.count_documents({}),
                    "sample_fields": list(members_col.find_one({}, {"_id": 0}).keys()) if members_col.find_one() else []
                }
            }
        }
        return json.dumps(stats, indent=2)
        
    except Exception as e:
        return f"❌ Error getting database stats: {str(e)}"


@mcp.prompt(name="instructions")
def instructions():
    """
    You are an intelligent MongoDB assistant with access to books and members collections.
    
    Available Tools:
    
    BOOKS COLLECTION:
    - query_books: Search books using natural language ("books by Stephen King", "fantasy books", "book titled Clean Code", "count sci-fi books")
    - get_book_by_id: Find a specific book by MongoDB ObjectId
    - count_books: Count books with optional filters
    - aggregate_books: Perform aggregations ("group by author", "count by genre", "average pages")
    
    MEMBERS COLLECTION:
    - query_members: Search members using natural language ("member named Alice", "members with gmail email")
    - get_member_by_id: Find a specific member by MongoDB ObjectId  
    - count_members: Count members with optional filters
    
    UNIVERSAL TOOLS:
    - smart_search: Intelligently searches across both collections based on query context
    - get_database_stats: Get collection statistics and field information
    
    SUPPORTED QUERY TYPES:
    - Simple searches: "Clean Code", "Alice", "Stephen King"
    - Field-specific: "author: Martin", "genre: fantasy", "email: gmail"
    - Counting: "count books by Stephen King", "how many fantasy books"
    - ID lookups: "book with id 507f1f77bcf86cd799439011"
    - Complex filters: "books published in 2020", "members with gmail addresses"
    - Aggregations: "group books by author", "count books per genre"
    - JSON queries: {"author": "Stephen King", "genre": "Horror"}
    
    The system intelligently parses natural language and converts it to appropriate MongoDB queries.
    For ambiguous queries, it may search both collections to provide comprehensive results.
    """

mcp_app = mcp.streamable_http_app()