import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.models.item import ItemCategory, ItemStatus, ItemType
from app.schemas.drop_off import DropOffInfo
from app.schemas.token import TokenEscrowInfo
from app.schemas.claim import ViewerClaimSummary


# ── Lost Item Request ────────────────────────────────────────────────────────

class CreateLostItemRequest(BaseModel):
    category: ItemCategory
    public_description: str
    location_id: Optional[uuid.UUID] = None
    date_occurred: datetime
    image_urls: list[str] = []

    @field_validator("public_description")
    @classmethod
    def public_desc_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Public description is required")
        if len(v) > 1000:
            raise ValueError("Public description must be 1000 characters or fewer")
        return v

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: list[str]) -> list[str]:
        if len(v) > 2:
            raise ValueError("Maximum 2 images allowed")
        for url in v:
            if not ("cloudinary.com" in url or "res.cloudinary.com" in url):
                raise ValueError("Invalid image URL — only Cloudinary URLs are accepted")
        return v


class UpdateLostItemRequest(BaseModel):
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


class ItemPosterSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    username: str

    model_config = {"from_attributes": True}


class LostItemPublicResponse(BaseModel):
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
    viewer_claim: Optional[ViewerClaimSummary] = None

    model_config = {"from_attributes": True}


class LostItemOwnerResponse(LostItemPublicResponse):
    already_submitted: bool = False
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class LostItemListItem(BaseModel):
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
    university_id: uuid.UUID

    model_config = {"from_attributes": True}


class CreateFoundItemRequest(BaseModel):
    category: ItemCategory
    public_description: str
    location_id: uuid.UUID
    date_occurred: datetime
    image_urls: list[str]
    drop_point_id: Optional[uuid.UUID] = None
    escrow_token: Optional[str] = None

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
            raise ValueError("At least one photo is required for found items")
        if len(v) > 2:
            raise ValueError("Maximum 2 images allowed")
        for url in v:
            if not ("cloudinary.com" in url or "res.cloudinary.com" in url):
                raise ValueError("Invalid image URL — only Cloudinary URLs are accepted")
        return v


class UpdateFoundItemRequest(BaseModel):
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


FoundItemPublicResponse = LostItemPublicResponse


class FoundItemCreateResponse(BaseModel):
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
    tracking_reference: str
    drop_point_id: uuid.UUID
    drop_point_name: str
    instruction_message: str
    can_edit: bool
    edit_window_ends_at: datetime
    drop_off: DropOffInfo
    token_escrow: TokenEscrowInfo

    model_config = {"from_attributes": True}


class FoundItemTrackResponse(FoundItemCreateResponse):
    minutes_remaining: int

    model_config = {"from_attributes": True}


FoundItemOwnerResponse = LostItemPublicResponse


class FoundItemListItem(BaseModel):
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


class BrowseItemPoster(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str

    model_config = {"from_attributes": True}


class BrowseItemCard(BaseModel):
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
    viewer_claim: Optional[ViewerClaimSummary] = None

    model_config = {"from_attributes": True}


class BrowseListResponse(BaseModel):
    items: list[BrowseItemCard]
    total: int
    skip: int
    limit: int


class RecentlyReturnedItem(BaseModel):
    id: uuid.UUID
    category: ItemCategory
    returned_at: datetime
    university_short_name: str

    model_config = {"from_attributes": True}


class PublicReturnedItem(BaseModel):
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
