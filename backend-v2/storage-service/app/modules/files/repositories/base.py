from __future__ import annotations
from typing import Any, Optional, Union
import uuid
import asyncpg
from asyncpg.pool import PoolConnectionProxy
from fastapi import Depends
import functools
from abc import ABC
from app.core.database import get_db_connection
from app.core.exceptions import DuplicateRecordError, InvalidOperationError, ItemNotFoundError, QuotaExceededError, InfrastructureError
from app.modules.files import queries

AsyncConn = Union[asyncpg.Connection, PoolConnectionProxy]

def map_db_errors(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncpg.exceptions.UniqueViolationError as e:
            raise DuplicateRecordError(str(e))
        except asyncpg.exceptions.ForeignKeyViolationError as e:
            detail = getattr(e, 'detail', '') or ''
            if 'is not present in table' in detail:
                raise ItemNotFoundError(f"Referenced item not found: {str(e)}")
            elif 'is still referenced from table' in detail:
                raise InvalidOperationError(f"Cannot delete item as it is still referenced: {str(e)}")
            else:
                raise InvalidOperationError(str(e))
        except asyncpg.exceptions.CheckViolationError as e:
            constraint = getattr(e, 'constraint_name', '') or ''
            if 'quota' in constraint.lower() or 'storage' in constraint.lower() or 'size' in constraint.lower():
                raise QuotaExceededError(str(e))
            else:
                raise InvalidOperationError(f"Check constraint violated: {str(e)}")
        except asyncpg.exceptions.DeadlockDetectedError as e:
            raise InfrastructureError(f"Transient deadlock detected: {str(e)}")
        except asyncpg.exceptions.RaiseError as e:
            msg = str(e).lower()
            if 'quota' in msg or 'storage' in msg or 'exceed' in msg:
                raise QuotaExceededError(str(e))
            elif 'not found' in msg:
                raise ItemNotFoundError(str(e))
            elif 'duplicate' in msg or 'already exists' in msg:
                raise DuplicateRecordError(str(e))
            else:
                raise InvalidOperationError(str(e))
    return wrapper

class BaseRepository(ABC):
    def __init__(self, conn: asyncpg.Connection = Depends(get_db_connection)):
        self.conn = conn

    @staticmethod
    def _row_to_dict(row: asyncpg.Record | None) -> Optional[dict[str, Any]]:
        return dict(row) if row else None
