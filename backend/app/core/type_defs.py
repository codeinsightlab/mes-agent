from typing import Dict, List, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
# Pydantic 2 on the current runtime cannot build schemas for implicit
# recursive JSON aliases, so nested JSON is kept at an explicit object boundary.
JsonValue: TypeAlias = object
JsonObject: TypeAlias = Dict[str, object]
JsonArray: TypeAlias = List[object]
