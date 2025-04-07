from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Voice Profile schemas
class VoiceProfileBase(BaseModel):
    name: str
    description: Optional[str] = None

class VoiceProfileCreate(VoiceProfileBase):
    pass

class VoiceProfileUpdate(VoiceProfileBase):
    name: Optional[str] = None

class VoiceProfileResponse(VoiceProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Vocabulary schemas
class VocabularyBase(BaseModel):
    word: str

class VocabularyCreate(VocabularyBase):
    pass

class VocabularyResponse(BaseModel):
    id: int
    voice_profile_id: int
    word: str
    audio_path: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    exists: Optional[bool] = False
    message: Optional[str] = None

    class Config:
        orm_mode = True

class VocabularyDelete(BaseModel):
    word: str

class VoiceProfileWithVocabularies(VoiceProfileResponse):
    vocabularies: List[VocabularyResponse] = []

    class Config:
        from_attributes = True

# Text to speech request
class TextToSpeechRequest(BaseModel):
    voice_profile_id: int
    text: str 