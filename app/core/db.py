from .config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Union, Collection

from enum import Enum

# Create a MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URI)
# print(settings.MONGODB_URI)
db = client.get_default_database(settings.MONGODB_DATABASE_NAME)


class MONGO_COLLECTIONS(Enum):
    EVENTS = "users"
    PRODUCTS = "products"


def get_collection(collection_name: MONGO_COLLECTIONS) -> Union[Collection, None]:
    try:
        coll_name = collection_name.value
        return db[coll_name]
    # catching the error just to throw it again? Yes, i know 🙃
    except AttributeError as e:
        print(f"AttributeError: {e}")
        return None
    except AssertionError as e:
        print(f"AssertionError: {e}")
        return None
    except ArithmeticError as e:
        print(f"ArithmeticError: {e}")
        return None
