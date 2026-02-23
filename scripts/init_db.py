from sentinel.db import DB_PATH, engine
from sentinel.models import Base


if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"Initialized database at {DB_PATH}")
