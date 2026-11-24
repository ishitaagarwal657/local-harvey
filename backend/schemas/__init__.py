from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None

class ProductCreate(BaseModel):
    company_id: int
    name: str
    description: Optional[str] = None
    value_props: Optional[List[str]] = None
    pricing_model: Optional[str] = None
    target_segments: Optional[List[str]] = None

class ProspectCreate(BaseModel):
    product_id: Optional[int] = None
    company_name: str
    website: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    location: Optional[str] = None
    raw_data: Optional[str] = None

class ReplyClassifyRequest(BaseModel):
    reply_text: str
    original_email: Optional[str] = ""
    prospect_id: Optional[int] = None

class StatusResponse(BaseModel):
    status: str
    ollama_available: bool
    models: List[str] = []
    hardware: Dict[str, Any] = {}
    recommendation: Dict[str, Any] = {}
    message: str = ""
