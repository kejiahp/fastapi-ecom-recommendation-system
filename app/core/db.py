from .config import settings
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from typing import Union

from enum import Enum

# Create a MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client.get_default_database()


class MONGO_COLLECTIONS(Enum):
    USERS = "users"
    PRODUCTS = "products"


def get_collection(
    collection_name: MONGO_COLLECTIONS,
) -> Union[AsyncIOMotorCollection, None]:
    try:
        coll_name = collection_name.value
        return db.get_collection(coll_name)
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
