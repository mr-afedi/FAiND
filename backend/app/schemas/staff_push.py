from pydantic import BaseModel


class StaffPushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class StaffPushUnsubscribeRequest(BaseModel):
    endpoint: str


class StaffPushSettingsUpdate(BaseModel):
    push_notifications_enabled: bool


class StaffPushSettingsResponse(BaseModel):
    push_notifications_enabled: bool
