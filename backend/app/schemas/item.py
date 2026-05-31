import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from app.models.item import ItemCategory, ItemStatus, ItemType


# ── Hidden Q&A ──────────────────────────────────────────────────────────────

class HiddenQuestionInput(BaseModel):
    question: str
    answer: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > 300:
            raise ValueError("Question must be 300 characters or fewer")
        return v

    @field_validator("answer")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Answer cannot be empty")
        if len(v) > 300:
            raise ValueError("Answer must be 300 characters or fewer")
        return v


class HiddenQuestionPublic(BaseModel):
    """Finder's questions shown to the owner during verification; answers are NEVER returned."""
    id: uuid.UUID
    position: int
    question: str  # decrypted question text, only sent to the item owner

    model_config = {"from_attributes": True}


# ── Lost Item Request ────────────────────────────────────────────────────────

class CreateLostItemRequest(BaseModel):
    """
    Lost items: owner sets hidden verification Q&A (Section 6, V4.3).
    """
    category: ItemCategory
    public_description: str
    location_id: Optional[uuid.UUID] = None
    date_occurred: datetime
    image_urls: list[str] = []
    hidden_questions: list[HiddenQuestionInput]

    @field_validator("public_description")
    @classmethod
    def public_desc_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Public description is required")
        if len(v) > 1000:
            raise ValueError("Public description must be 1000 characters or fewer")
        return v

    @field_validator("hidden_questions")
    @classmethod
    def validate_questions(cls, v: list[HiddenQuestionInput]) -> list[HiddenQuestionInput]:
        if len(v) < 2:
            raise ValueError("At least 2 hidden verification questions are required")
        if len(v) > 3:
            raise ValueError("Maximum 3 hidden verification questions allowed")
        return v

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: list[str]) -> list[str]:
        if len(v) > 2:
            raise ValueError("Maximum 2 images allowed")
        for url in v:
            if not ("cloudinary.com" in url or "res.cloudinary.com" in url):
                raise ValueError(f"Invalid image URL — only Cloudinary URLs are accepted")
        return v


# ── Patch / Edit ─────────────────────────────────────────────────────────────

class UpdateLostItemRequest(BaseModel):
    """Only public-facing fields may be edited. Encrypted fields are immutable."""
    category: Optional[ItemCategory] = None
    public_description: Optional[str] = None
    location_id: Optional[uuid.UUID] = None
    date_occurred: Optional[datetime] = None
    image_urls: Optional[list[str]] = None

    @field_validator("public_description")
    @classmethod
    def public_desc_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Public description cannot be empty")
            if len(v) > 1000:
                raise ValueError("Public description must be 1000 characters or fewer")
        return v

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            if len(v) > 2:
                raise ValueError("Maximum 2 images allowed")
            for url in v:
                if not ("cloudinary.com" in url or "res.cloudinary.com" in url):
                    raise ValueError("Invalid image URL — only Cloudinary URLs are accepted")
        return v


# ── Responses ────────────────────────────────────────────────────────────────

class ItemPosterSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    username: str
    trust_tier: str = "New Member"

    model_config = {"from_attributes": True}


class LostItemPublicResponse(BaseModel):
    """Returned for any authenticated user viewing an item (public fields only)."""
    id: uuid.UUID
    item_type: ItemType
    status: ItemStatus
    category: ItemCategory
    public_description: str
    location_label: str
    location_lat: Optional[float]
    location_lng: Optional[float]
    date_occurred: datetime
    image_urls: list[str]
    expiry_date: datetime
    extensions_used: int
    created_at: datetime
    posted_by: ItemPosterSummary
    # Path B claim state for the requesting user (lost items only; Section V4.3)
    viewer_path_b_status: Optional[str] = None  # under_review | approved | rejected | exhausted
    viewer_path_b_conversation_id: Optional[uuid.UUID] = None
    viewer_path_c_status: Optional[str] = None  # under_review | approved | exhausted
    viewer_path_c_conversation_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class LostItemOwnerResponse(LostItemPublicResponse):
    """Extended response for the item owner; hidden answers are never included."""

    warnings: list[str] = []

    model_config = {"from_attributes": True}


class CheckHiddenAnswersRequest(BaseModel):
    """Optional pre-submit check for obvious hidden answers (V4.3 §6.1)."""
    public_description: str
    hidden_questions: list[HiddenQuestionInput]


class CheckHiddenAnswersResponse(BaseModel):
    warnings: list[str] = []


class LostItemListItem(BaseModel):
    """Lightweight row for dashboard listing."""
    id: uuid.UUID
    category: ItemCategory
    status: ItemStatus
    public_description: str
    location_label: str
    date_occurred: datetime
    image_urls: list[str]
    expiry_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LostItemListResponse(BaseModel):
    items: list[LostItemListItem]
    total: int


class CampusZoneOption(BaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


# ── Found Item schemas (Feature D) ───────────────────────────────────────────

class CreateFoundItemRequest(BaseModel):
    """
    Found items: finder sets hidden verification Q&A (Section 7, V4.2).
    At least one image is mandatory.
    """
    category: ItemCategory
    public_description: str
    location_id: Optional[uuid.UUID] = None
    date_occurred: datetime
    image_urls: list[str]  # min 1 required, max 2
    hidden_questions: list[HiddenQuestionInput]

    @field_validator("public_description")
    @classmethod
    def public_desc_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description is required")
        if len(v) > 1000:
            raise ValueError("Description must be 1000 characters or fewer")
        return v

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("At least one photo is required for found items (Section 7)")
        if len(v) > 2:
            raise ValueError("Maximum 2 images allowed")
        for url in v:
            if not ("cloudinary.com" in url or "res.cloudinary.com" in url):
                raise ValueError("Invalid image URL — only Cloudinary URLs are accepted")
        return v

    @field_validator("hidden_questions")
    @classmethod
    def validate_questions(cls, v: list[HiddenQuestionInput]) -> list[HiddenQuestionInput]:
        if len(v) < 2:
            raise ValueError("At least 2 hidden verification questions are required")
        if len(v) > 3:
            raise ValueError("Maximum 3 hidden verification questions allowed")
        return v


class UpdateFoundItemRequest(BaseModel):
    """Only public-facing fields may be edited."""
    category: Optional[ItemCategory] = None
    public_description: Optional[str] = None
    location_id: Optional[uuid.UUID] = None
    date_occurred: Optional[datetime] = None
    image_urls: Optional[list[str]] = None

    @field_validator("public_description")
    @classmethod
    def public_desc_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Description cannot be empty")
            if len(v) > 1000:
                raise ValueError("Description must be 1000 characters or fewer")
        return v

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            if len(v) < 1:
                raise ValueError("At least one photo is required for found items")
            if len(v) > 2:
                raise ValueError("Maximum 2 images allowed")
            for url in v:
                if not ("cloudinary.com" in url or "res.cloudinary.com" in url):
                    raise ValueError("Invalid image URL — only Cloudinary URLs are accepted")
        return v


# Found items: hidden Q&A never exposed in any API response (Section 7.2)
FoundItemPublicResponse = LostItemPublicResponse
FoundItemOwnerResponse = LostItemPublicResponse

class FoundItemListItem(BaseModel):
    """Lightweight row for dashboard listing."""
    id: uuid.UUID
    category: ItemCategory
    status: ItemStatus
    public_description: str
    location_label: str
    date_occurred: datetime
    image_urls: list[str]
    expiry_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class FoundItemListResponse(BaseModel):
    items: list[FoundItemListItem]
    total: int


# ── Public browse schemas (Feature F) ────────────────────────────────────────

class BrowseItemPoster(BaseModel):
    """Poster info for the public feed — tier label only, no raw score (Section 17.2)."""
    id: uuid.UUID
    username: str
    display_name: str
    trust_tier: str

    model_config = {"from_attributes": True}


class BrowseItemCard(BaseModel):
    """Public card shown on /lost, /found, and homepage previews."""
    id: uuid.UUID
    item_type: ItemType
    status: ItemStatus
    category: ItemCategory
    public_description: str
    location_label: str
    date_occurred: datetime
    image_urls: list[str]
    created_at: datetime
    updated_at: datetime
    posted_by: BrowseItemPoster
    viewer_path_b_status: Optional[str] = None
    viewer_path_b_conversation_id: Optional[uuid.UUID] = None
    viewer_path_c_status: Optional[str] = None
    viewer_path_c_conversation_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class BrowseListResponse(BaseModel):
    items: list[BrowseItemCard]
    total: int
    skip: int
    limit: int


class RecentlyReturnedItem(BaseModel):
    """Anonymous resolved-item summary for the homepage (Section 16.6)."""
    id: uuid.UUID
    category: ItemCategory
    returned_at: datetime
    university_short_name: str

    model_config = {"from_attributes": True}


class PublicReturnedItem(BaseModel):
    """Anonymous returned item for public /returned page (Section 16.6)."""
    id: uuid.UUID
    category: ItemCategory
    item_name: str
    returned_at: datetime
    university_short_name: str

    model_config = {"from_attributes": True}


class PublicReturnedListResponse(BaseModel):
    items: list[PublicReturnedItem]
    total: int


class HomepageResponse(BaseModel):
    latest_lost: list[BrowseItemCard]
    latest_found: list[BrowseItemCard]
    recently_returned: list[RecentlyReturnedItem] = []
    recently_returned_count: int = 0
