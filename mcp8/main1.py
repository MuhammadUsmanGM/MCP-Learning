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


def parse_natural_language_filter(query: str) -> Dict:
    """
    Parse natural language queries and convert them to MongoDB filter format.
    More generic approach that works with any collection.
    """
    query_lower = query.lower().strip()
    
    # Check for count queries
    if 'count' in query_lower or 'how many' in query_lower or 'number of' in query_lower:
        return {'operation': 'count', 'filter': extract_generic_filter(query_lower)}
    
    # Check for ID-based queries
    id_patterns = [r'id\s*[:\"]?\s*([a-f0-9]{24})', r'_id\s*[:\"]?\s*([a-f0-9]{24})']
    for pattern in id_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                return {'operation': 'find', 'filter': {'_id': ObjectId(match.group(1))}}
            except:
                pass
    
    # Generic field:value pattern matching
    filter_dict = extract_generic_filter(query)
    if filter_dict:
        return {'operation': 'find', 'filter': filter_dict}
    
    # Default to text search if no specific patterns found
    search_terms = extract_search_terms(query)
    if search_terms:
        # Generic text search - will search common text fields
        text_search = {
            "$text": {"$search": search_terms}
        }
        return {'operation': 'find', 'filter': text_search}
    
    return {'operation': 'find', 'filter': {}}


def extract_generic_filter(query: str) -> Dict:
    """
    Extract filter conditions from generic queries using field:value patterns.
    """
    filter_dict = {}
    
    # Look for field:value patterns
    field_value_patterns = [
        r'(\w+):\s*([^,\s]+)',  # field:value
        r'(\w+)\s*=\s*([^,\s]+)',  # field=value
        r'(\w+)\s+is\s+([^,\s]+)',  # field is value
    ]
    
    for pattern in field_value_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for field, value in matches:
            # Clean the value
            value = value.strip().strip('\'"')
            
            # Try to convert to appropriate type
            if value.isdigit():
                filter_dict[field] = int(value)
            elif value.replace('.', '').isdigit():
                filter_dict[field] = float(value)
            elif value.lower() in ['true', 'false']:
                filter_dict[field] = value.lower() == 'true'
            else:
                # Use regex for string fields
                filter_dict[field] = {'$regex': value, '$options': 'i'}
    
    return filter_dict


def extract_search_terms(query: str) -> str:
    """
    Extract the main search terms from a natural language query.
    """
    # Remove common query words and patterns
    stop_words = ['find', 'search', 'get', 'show', 'me', 'the', 'a', 'an', 'is', 'are', 'of', 'for', 'with', 'about', 'where']
    words = query.lower().split()
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    return ' '.join(filtered_words) if filtered_words else query


def parse_document_input(text: str) -> Dict:
    """
    Parse natural language document input and convert to document format.
    Generic parser that works with any field names.
    """
    doc = {}
    
    # Look for field:value patterns
    patterns = [
        r'(\w+):\s*([^,]+)',  # field: value
        r'(\w+)\s*=\s*([^,]+)',  # field = value
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for field, value in matches:
            value = value.strip().strip('\'"')
            
            # Try to convert to appropriate type
            if value.isdigit():
                doc[field] = int(value)
            elif value.replace('.', '').isdigit():
                doc[field] = float(value)
            elif value.lower() in ['true', 'false']:
                doc[field] = value.lower() == 'true'
            else:
                doc[field] = value
    
    return doc if doc else None


secrets = Secrets()

mongo_client = MongoClient(secrets.mongo_uri)

mcp = FastMCP(name="UNIVERSAL_MCP_APP", stateless_http=True)

# --- Universal Database Operations ---
@mcp.tool(name="list_databases",
          description="List all available databases in the MongoDB instance.")
def list_databases() -> str:
    try:
        dbs = mongo_client.list_database_names()
        # Filter out system databases
        user_dbs = [db for db in dbs if db not in ['admin', 'config', 'local']]
        return json.dumps({"databases": user_dbs}, indent=2)
    except Exception as e:
        return f"❌ Error listing databases: {str(e)}"


@mcp.tool(name="list_collections",
          description="List all collections in a specific database.")
def list_collections(database_name: str) -> str:
    try:
        db = mongo_client[database_name]
        collections = db.list_collection_names()
        return json.dumps({"database": database_name, "collections": collections}, indent=2)
    except Exception as e:
        return f"❌ Error listing collections: {str(e)}"


@mcp.tool(name="get_collection_info",
          description="Get information about a specific collection including sample documents and field types.")
def get_collection_info(database_name: str, collection_name: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # Get collection stats
        stats = {
            "database": database_name,
            "collection": collection_name,
            "document_count": collection.count_documents({}),
        }
        
        # Get sample document to show structure
        sample_doc = collection.find_one({}, {"_id": 0})
        if sample_doc:
            stats["sample_fields"] = list(sample_doc.keys())
            stats["sample_document"] = sample_doc
        else:
            stats["sample_fields"] = []
            stats["sample_document"] = None
        
        return json.dumps(stats, indent=2, default=mongo_json_encoder)
    except Exception as e:
        return f"❌ Error getting collection info: {str(e)}"


# --- Universal Query Operations ---
@mcp.tool(name="query_collection",
          description="Query any collection using natural language or JSON. Supports searches, filters, counting. Examples: 'status: active', 'count all documents', 'price > 100'")
def query_collection(database_name: str, collection_name: str, query: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # First try to parse as direct JSON
        try:
            filter_dict = json.loads(query)
            parsed_query = {'operation': 'find', 'filter': filter_dict}
        except json.JSONDecodeError:
            # Parse natural language query
            parsed_query = parse_natural_language_filter(query)
        
        # Execute the appropriate operation
        if parsed_query['operation'] == 'count':
            count = collection.count_documents(parsed_query['filter'])
            filter_desc = json.dumps(parsed_query['filter']) if parsed_query['filter'] else "all documents"
            return f"Found {count} documents in {database_name}.{collection_name} matching filter: {filter_desc}"
        
        elif parsed_query['operation'] == 'find':
            # Include _id in results for ID-based queries, exclude for others
            projection = {} if '_id' in parsed_query['filter'] else {"_id": 0}
            docs = list(collection.find(parsed_query['filter'], projection).limit(20))
            
            if not docs:
                return f"No documents found in {database_name}.{collection_name} matching your query."
            
            return json.dumps({
                "database": database_name,
                "collection": collection_name,
                "results": docs
            }, indent=2, default=mongo_json_encoder)
        
        return "Invalid query operation."
        
    except Exception as e:
        return f"❌ Error querying collection: {str(e)}"


@mcp.tool(name="count_documents",
          description="Count documents in any collection with optional filters.")
def count_documents(database_name: str, collection_name: str, filter_query: str = "") -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        if not filter_query.strip():
            # Count all documents
            count = collection.count_documents({})
            return f"Total documents in {database_name}.{collection_name}: {count}"
        
        try:
            # Try parsing as JSON first
            filter_dict = json.loads(filter_query)
        except json.JSONDecodeError:
            # Parse as natural language
            filter_dict = extract_generic_filter(filter_query)
        
        count = collection.count_documents(filter_dict)
        filter_desc = json.dumps(filter_dict) if filter_dict else "all documents"
        return f"Found {count} documents in {database_name}.{collection_name} matching filter: {filter_desc}"
        
    except Exception as e:
        return f"❌ Error counting documents: {str(e)}"


@mcp.tool(name="get_document_by_id",
          description="Get a specific document by its MongoDB ObjectId from any collection.")
def get_document_by_id(database_name: str, collection_name: str, document_id: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # Convert string to ObjectId
        obj_id = ObjectId(document_id)
        doc = collection.find_one({"_id": obj_id})
        
        if doc:
            return json.dumps({
                "database": database_name,
                "collection": collection_name,
                "document": doc
            }, indent=2, default=mongo_json_encoder)
        else:
            return f"No document found with ID: {document_id} in {database_name}.{collection_name}"
            
    except Exception as e:
        return f"❌ Error finding document by ID: {str(e)}"


# --- Universal CRUD Operations ---
@mcp.tool(name="add_document",
          description="Add a new document to any collection. Provide document data as JSON or natural language (field: value, field2: value2).")
def add_document(database_name: str, collection_name: str, document_data: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # Try to parse as JSON first
        try:
            doc = json.loads(document_data)
        except json.JSONDecodeError:
            # Parse natural language input
            doc = parse_document_input(document_data)
        
        if not doc:
            return "❌ Could not parse document data. Please provide JSON or natural language format (field: value, field2: value2)."
        
        # Add timestamp
        doc['created_at'] = datetime.now()
        
        # Insert the document
        result = collection.insert_one(doc)
        return f"✅ Document added successfully to {database_name}.{collection_name} with ID: {result.inserted_id}"
        
    except Exception as e:
        return f"❌ Error adding document: {str(e)}"


@mcp.tool(name="update_document",
          description="Update an existing document in any collection. Provide document ID and update data as JSON or natural language.")
def update_document(database_name: str, collection_name: str, document_id: str, update_data: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # Convert to ObjectId
        obj_id = ObjectId(document_id)
        
        # Try to parse update data as JSON first
        try:
            update_doc = json.loads(update_data)
        except json.JSONDecodeError:
            # Parse natural language update
            update_doc = parse_document_input(update_data)
        
        if not update_doc:
            return "❌ Could not parse update data. Please provide JSON or natural language format."
        
        # Add update timestamp
        update_doc['updated_at'] = datetime.now()
        
        # Update the document
        result = collection.update_one({"_id": obj_id}, {"$set": update_doc})
        
        if result.matched_count == 0:
            return f"❌ No document found with ID: {document_id} in {database_name}.{collection_name}"
        elif result.modified_count > 0:
            return f"✅ Document updated successfully in {database_name}.{collection_name}. Modified {result.modified_count} field(s)."
        else:
            return f"ℹ️ Document found in {database_name}.{collection_name} but no changes were made (data was already current)."
            
    except Exception as e:
        return f"❌ Error updating document: {str(e)}"


@mcp.tool(name="delete_document",
          description="Delete a document by ID from any collection. Use with caution as this operation cannot be undone.")
def delete_document(database_name: str, collection_name: str, document_id: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # Convert to ObjectId
        obj_id = ObjectId(document_id)
        
        # First check if document exists
        doc = collection.find_one({"_id": obj_id})
        if not doc:
            return f"❌ No document found with ID: {document_id} in {database_name}.{collection_name}"
        
        # Delete the document
        result = collection.delete_one({"_id": obj_id})
        
        if result.deleted_count > 0:
            return f"✅ Document (ID: {document_id}) deleted successfully from {database_name}.{collection_name}."
        else:
            return f"❌ Failed to delete document with ID: {document_id} from {database_name}.{collection_name}"
            
    except Exception as e:
        return f"❌ Error deleting document: {str(e)}"


# --- Bulk Operations ---
@mcp.tool(name="delete_multiple_documents",
          description="Delete multiple documents based on a filter. Use with extreme caution as this operation cannot be undone.")
def delete_multiple_documents(database_name: str, collection_name: str, filter_query: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        # Parse filter
        try:
            filter_dict = json.loads(filter_query)
        except json.JSONDecodeError:
            filter_dict = extract_generic_filter(filter_query)
        
        if not filter_dict:
            return "❌ Could not parse filter. Please provide a valid filter to avoid deleting all documents."
        
        # Count documents that will be deleted first
        count = collection.count_documents(filter_dict)
        if count == 0:
            return f"No documents found matching the filter in {database_name}.{collection_name}."
        
        # Delete the documents
        result = collection.delete_many(filter_dict)
        return f"✅ Deleted {result.deleted_count} documents from {database_name}.{collection_name} matching filter: {json.dumps(filter_dict)}"
        
    except Exception as e:
        return f"❌ Error deleting multiple documents: {str(e)}"


# --- Aggregation Operations ---
@mcp.tool(name="aggregate_collection",
          description="Perform aggregation operations on any collection. Examples: 'group by status', 'count by category', 'average price'.")
def aggregate_collection(database_name: str, collection_name: str, aggregation_query: str) -> str:
    try:
        db = mongo_client[database_name]
        collection = db[collection_name]
        
        query_lower = aggregation_query.lower()
        pipeline = []
        
        # Parse common aggregation patterns
        if 'group by' in query_lower:
            # Extract field name to group by
            group_match = re.search(r'group by (\w+)', query_lower)
            if group_match:
                field = group_match.group(1)
                pipeline = [
                    {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
        
        elif 'count by' in query_lower:
            # Extract field name to count by
            count_match = re.search(r'count by (\w+)', query_lower)
            if count_match:
                field = count_match.group(1)
                pipeline = [
                    {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
        
        elif 'average' in query_lower:
            # Extract field name for average
            avg_match = re.search(r'average (\w+)', query_lower)
            if avg_match:
                field = avg_match.group(1)
                pipeline = [
                    {"$group": {"_id": None, f"avg_{field}": {"$avg": f"${field}"}, "total_documents": {"$sum": 1}}}
                ]
        
        elif 'sum' in query_lower:
            # Extract field name for sum
            sum_match = re.search(r'sum (\w+)', query_lower)
            if sum_match:
                field = sum_match.group(1)
                pipeline = [
                    {"$group": {"_id": None, f"total_{field}": {"$sum": f"${field}"}, "document_count": {"$sum": 1}}}
                ]
        
        else:
            # Try to parse as JSON pipeline
            try:
                pipeline = json.loads(aggregation_query)
            except json.JSONDecodeError:
                return "Aggregation query not recognized. Try: 'group by field', 'count by field', 'average field', 'sum field', or provide a JSON aggregation pipeline."
        
        if pipeline:
            results = list(collection.aggregate(pipeline))
            return json.dumps({
                "database": database_name,
                "collection": collection_name,
                "aggregation_results": results
            }, indent=2, default=mongo_json_encoder) if results else f"No aggregation results for {database_name}.{collection_name}."
        
        return "Could not create aggregation pipeline from query."
        
    except Exception as e:
        return f"❌ Error in aggregation: {str(e)}"


@mcp.prompt(name="instructions")
def instructions():
    """
    You are a universal MongoDB assistant that can work with ANY database and collection.
    
    Available Operations:
    
    DATABASE DISCOVERY:
    - list_databases: Show all available databases
    - list_collections: Show all collections in a database
    - get_collection_info: Get detailed info about a specific collection
    
    QUERY OPERATIONS (Works with ANY collection):
    - query_collection: Search documents using natural language or JSON
    - count_documents: Count documents with optional filters
    - get_document_by_id: Find specific document by MongoDB ObjectId
    
    CRUD OPERATIONS (Works with ANY collection):
    - add_document: Add new documents to any collection
    - update_document: Update existing documents by ID
    - delete_document: Delete documents by ID
    - delete_multiple_documents: Bulk delete with filters
    
    AGGREGATION OPERATIONS:
    - aggregate_collection: Perform aggregations on any collection
    
    SUPPORTED QUERY FORMATS:
    - Natural Language: "status: active", "price > 100", "category electronics"
    - JSON: {"status": "active", "price": {"$gt": 100}}
    - Field patterns: "field: value", "field = value", "field is value"
    
    EXAMPLES:
    - "Show me all databases"
    - "List collections in ecommerce database"
    - "Query products collection for electronics"
    - "Add to users: name: John, email: john@example.com, age: 25"
    - "Count documents in orders where status: completed"
    - "Group products by category"
    - "Delete document 507f1f77bcf86cd799439011 from users collection"
    
    This system works with ANY MongoDB database and collection structure!
    You can discover available databases and collections, then perform operations on them.
    """

mcp_app = mcp.streamable_http_app()