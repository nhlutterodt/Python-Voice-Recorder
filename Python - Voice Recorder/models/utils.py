"""Small utilities for working with SQLAlchemy model instances.

Provides a lightweight `to_dict` serializer that converts model instances
to JSON-serializable dictionaries and handles common Python types.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.inspection import inspect


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        # Decimal is not JSON serializable by default
        return float(value)
    # primitives (int, float, str, bool) and other JSON-safe values pass
    return value


def to_dict(model_instance, include_relationships=False, exclude=None):
    """Convert a SQLAlchemy model instance to a JSON-serializable dict.

    Parameters:
    - model_instance: declarative model instance
    - include_relationships: if True, include scalar relationships (best-effort)
    - exclude: iterable of attribute names to exclude

    Returns: dict
    """
    if exclude is None:
        exclude = set()
    else:
        exclude = set(exclude)

    insp = inspect(model_instance)
    data = {}

    # Columns / simple attributes
    for attr in insp.mapper.column_attrs:
        key = attr.key
        if key in exclude:
            continue
        try:
            value = getattr(model_instance, key)
        except Exception:
            # Be robust: skip attributes that raise on access
            continue
        data[key] = _serialize_value(value)

    # Optionally include simple scalar relationships (not collections)
    if include_relationships:
        for rel in insp.mapper.relationships:
            if rel.key in exclude:
                continue
            # skip collections (one-to-many, many-to-many)
            if rel.uselist:
                continue
            try:
                related = getattr(model_instance, rel.key)
            except Exception:
                continue
            if related is None:
                data[rel.key] = None
            else:
                # If related object looks like a mapped instance, try to serialize its primary columns
                try:
                    related_insp = inspect(related)
                    # include primary key values only to avoid deep recursion
                    pk_vals = {}
                    for pk_col in related_insp.mapper.primary_key:
                        pk_name = pk_col.key
                        pk_vals[pk_name] = _serialize_value(getattr(related, pk_name, None))
                    data[rel.key] = pk_vals
                except Exception:
                    # Fallback to string representation
                    data[rel.key] = str(related)

    return data
