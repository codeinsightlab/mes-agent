from dataclasses import dataclass


@dataclass(frozen=True)
class IdentityContext:
    user_id: str | None = None
    visitor_id: str | None = None

    def __post_init__(self):
        user_id = self.user_id.strip() if self.user_id else None
        visitor_id = self.visitor_id.strip() if self.visitor_id else None
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "visitor_id", visitor_id)
        if user_id is None and visitor_id is None:
            raise ValueError("IdentityContext requires user_id or visitor_id.")

    def require_anonymous_visitor(self) -> str:
        if not self.visitor_id:
            raise ValueError("Anonymous identity requires visitor_id.")
        return self.visitor_id
