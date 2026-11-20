"""Base schema types for domain data transfer objects."""

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Strict base model for gateway domain DTOs.

    Subclasses reject unknown fields and re-validate on assignment.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
