import os
import urllib.parse
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId

# Load MongoDB connection URI
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    # Fallback to local MongoDB for development
    MONGODB_URI = "mongodb://localhost:27017/amazon_autolister"

# Parse database name from URI, default to "amazon_autolister"
db_name = "amazon_autolister"
try:
    parsed = urllib.parse.urlparse(MONGODB_URI)
    if parsed.path and parsed.path != "/":
        path_clean = parsed.path.strip("/").split("?")[0]
        if path_clean:
            db_name = path_clean
except Exception:
    pass

print(f"🔌 Connecting to MongoDB Database: {db_name}")
mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
mongo_db = mongo_client[db_name]

class MongoField:
    def __init__(self, name):
        self.name = name
    def __eq__(self, other):
        return (self.name, other)
    def __ne__(self, other):
        return (self.name, {"$ne": other})
    def desc(self):
        return (self.name, -1)
    def asc(self):
        return (self.name, 1)
    def like(self, pattern):
        regex_pattern = pattern.replace("%", ".*").replace("_", ".")
        return (self.name, {"$regex": regex_pattern, "$options": "i"})

def to_mongo_id(id_val):
    if isinstance(id_val, str) and len(id_val) == 24:
        try:
            return ObjectId(id_val)
        except Exception:
            pass
    return id_val

class MongoQuery:
    def __init__(self, session, model_class):
        self.session = session
        self.model_class = model_class
        self.filters = {}
        self.sort_list = []
        self.collection_name = model_class.__tablename__
        
    def filter(self, *args):
        for arg in args:
            if isinstance(arg, tuple) and len(arg) == 2:
                key, val = arg
                # Map 'id' attribute to '_id' in MongoDB
                if key == "id":
                    key = "_id"
                    val = to_mongo_id(val)
                self.filters[key] = val
        return self
        
    def order_by(self, *args):
        for arg in args:
            if isinstance(arg, tuple) and len(arg) == 2:
                key, val = arg
                if key == "id":
                    key = "_id"
                self.sort_list.append((key, val))
        return self
        
    def all(self):
        collection = self.session.db[self.collection_name]
        cursor = collection.find(self.filters)
        if self.sort_list:
            cursor = cursor.sort(self.sort_list)
        return [self.model_class.from_mongo(doc) for doc in cursor]
        
    def first(self):
        collection = self.session.db[self.collection_name]
        doc = collection.find_one(self.filters)
        return self.model_class.from_mongo(doc) if doc else None
        
    def delete(self):
        collection = self.session.db[self.collection_name]
        result = collection.delete_many(self.filters)
        return result.deleted_count

class MongoSession:
    def __init__(self):
        self.client = mongo_client
        self.db = mongo_db
        self.pending_add = []
        self.pending_delete = []
        
    def query(self, model_class):
        return MongoQuery(self, model_class)
        
    def add(self, obj):
        self.pending_add.append(obj)
        
    def delete(self, obj):
        self.pending_delete.append(obj)
        
    def commit(self):
        # Perform deletes
        for obj in self.pending_delete:
            collection = self.db[obj.__tablename__]
            doc_id = to_mongo_id(getattr(obj, "id", None))
            if doc_id:
                collection.delete_one({"_id": doc_id})
        self.pending_delete = []
        
        # Perform adds/updates
        for obj in self.pending_add:
            collection = self.db[obj.__tablename__]
            doc = obj.to_mongo()
            
            # Check if object has an id (updating or pre-generated key)
            doc_id = doc.get("_id")
            if doc_id:
                doc_id = to_mongo_id(doc_id)
                doc["_id"] = doc_id
                collection.replace_one({"_id": doc_id}, doc, upsert=True)
            else:
                res = collection.insert_one(doc)
                obj.id = str(res.inserted_id)
        self.pending_add = []
        
    def rollback(self):
        self.pending_add = []
        self.pending_delete = []
        
    def refresh(self, obj):
        """Re-fetch the object from MongoDB to get latest data (e.g. auto-generated _id)"""
        collection = self.db[obj.__tablename__]
        doc_id = to_mongo_id(getattr(obj, "id", None))
        if doc_id:
            doc = collection.find_one({"_id": doc_id})
            if doc:
                refreshed = obj.__class__.from_mongo(doc)
                for key, val in refreshed.__dict__.items():
                    setattr(obj, key, val)
        
    def close(self):
        pass

# Dependency generator emulating SQLAlchemy get_db
def get_db():
    db = MongoSession()
    try:
        yield db
    finally:
        db.close()

# Mock objects to prevent SQLAlchemy initialization errors in main.py
class MockMetadata:
    def create_all(self, bind=None):
        pass

class Base:
    metadata = MockMetadata()

class MockEngine:
    def connect(self):
        return self

engine = MockEngine()
SessionLocal = MongoSession
Session = MongoSession
