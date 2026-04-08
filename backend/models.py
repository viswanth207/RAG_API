from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class DataSourceType(str, Enum):
    CSV = "csv"
    JSON = "json"
    URL = "url"
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"


class ExternalClientAuth(BaseModel):
    api_key: str = Field(..., description="The client's public API key")
    password: str = Field(..., description="The client's secret password")


class ExternalTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExternalChatRequest(BaseModel):
    database_name: str = Field(..., description="Target database name")
    message: str = Field(..., description="User's message")
    database_url: Optional[str] = Field(None, description="Optional DB Connection String (defaults to registered default)")



class AssistantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Assistant name")
    data_source_type: DataSourceType = Field(..., description="Type of data source")
    data_source_url: Optional[str] = Field(None, description="URL for URL-based data source")
    custom_instructions: str = Field(
        default="You are a helpful AI assistant. Answer questions based only on the provided data.",
        description="System prompt/instructions for the assistant"
    )
    enable_statistics: bool = Field(default=False, description="Enable statistical analysis")
    enable_alerts: bool = Field(default=False, description="Enable alert detection")
    enable_recommendations: bool = Field(default=False, description="Enable recommendations")
    
    @validator('data_source_url')
    def validate_url_for_url_type(cls, v, values):
        if values.get('data_source_type') == DataSourceType.URL and not v:
            raise ValueError("data_source_url is required when data_source_type is 'url'")
        return v


class AssistantCreateResponse(BaseModel):
    assistant_id: str = Field(..., description="Unique identifier for the assistant")
    name: str = Field(..., description="Assistant name")
    data_source_type: str = Field(..., description="Type of data source")
    documents_loaded: int = Field(..., description="Number of documents loaded")
    created_at: str = Field(..., description="Creation timestamp")
    message: str = Field(default="Assistant created successfully")


class ChatRequest(BaseModel):
    assistant_id: str = Field(..., description="ID of the assistant to chat with")
    message: str = Field(..., min_length=1, description="User's message")
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    assistant_id: str = Field(..., description="ID of the assistant")
    user_message: str = Field(..., description="User's message")
    assistant_response: str = Field(..., description="Assistant's response")
    sources_used: int = Field(..., description="Number of source documents used")
    timestamp: str = Field(..., description="Response timestamp")


class AssistantInfo(BaseModel):
    assistant_id: str
    name: str
    data_source_type: str
    custom_instructions: str
    documents_count: int
    enable_statistics: bool
    enable_alerts: bool
    enable_recommendations: bool
    created_at: str


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy")
    timestamp: str
    version: str = Field(default="1.0.0")
