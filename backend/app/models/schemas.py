from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class RedactionType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    REGION = "region"


class RedactionZone(BaseModel):
    page: int = Field(..., ge=0, description="Numero de pagina (0-indexed)")
    x: float = Field(..., ge=0, description="Coordenada X en puntos PDF")
    y: float = Field(..., ge=0, description="Coordenada Y en puntos PDF")
    width: float = Field(..., gt=0, description="Ancho en puntos PDF")
    height: float = Field(..., gt=0, description="Alto en puntos PDF")
    redaction_type: RedactionType = RedactionType.TEXT
    color: List[float] = Field(default=[0, 0, 0], description="Color RGB 0-1")
    fill: bool = Field(default=True, description="Rellenar la zona censurada")


class RedactionRequest(BaseModel):
    redaction_zones: List[RedactionZone]


class MetadataSanitizeOptions(BaseModel):
    remove_author: bool = True
    remove_creator: bool = True
    remove_producer: bool = True
    remove_title: bool = True
    remove_subject: bool = True
    remove_keywords: bool = True
    remove_creation_date: bool = True
    remove_mod_date: bool = True
    remove_all_xml_metadata: bool = True
    remove_thumbnails: bool = True
    remove_bookmarks: bool = False


class ProtectionOptions(BaseModel):
    user_password: Optional[str] = None
    owner_password: Optional[str] = None
    allow_print: bool = False
    allow_copy: bool = False
    allow_modify: bool = False
    allow_annotate: bool = False
    encryption_level: int = Field(default=256, ge=128, le=256)


class SignaturePosition(BaseModel):
    page: int
    x: float
    y: float
    width: float = 200
    height: float = 80


class ImageRedactionMethod(str, Enum):
    PIXELATE = "pixelate"
    BLACKOUT = "blackout"
    REMOVE = "remove"
