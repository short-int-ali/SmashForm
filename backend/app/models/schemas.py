"""
Pydantic schemas for SmashForm API.
Defines request/response models for video analysis.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class DominantHand(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Keypoint(BaseModel):
    """Single pose keypoint with 3D coordinates and visibility."""
    x: float
    y: float
    z: float
    visibility: float


class FramePose(BaseModel):
    """Pose data for a single frame."""
    frame_number: int
    timestamp_ms: float
    keypoints: dict[str, Keypoint]


class BiomechanicsMetric(BaseModel):
    """Single biomechanics measurement with comparison data."""
    name: str
    display_name: str
    user_value: float
    reference_value: float
    unit: str
    difference: float
    difference_percent: float
    severity: SeverityLevel
    description: str


class ShotSegment(BaseModel):
    """Temporal boundaries of the detected shot."""
    start_frame: int
    contact_frame: int
    end_frame: int
    total_frames: int
    duration_ms: float


class AnalysisRequest(BaseModel):
    """Request model for video analysis."""
    dominant_hand: DominantHand = Field(
        default=DominantHand.RIGHT,
        description="Player's dominant hand for correct interpretation of side view"
    )


class AnalysisResponse(BaseModel):
    """Complete analysis response with all biomechanics data."""
    success: bool
    message: str
    video_id: str
    dominant_hand: DominantHand
    shot_segment: Optional[ShotSegment]
    metrics: list[BiomechanicsMetric]
    technique_similarity_score: float = Field(
        ge=0, le=100,
        description="Overall technique similarity percentage (0-100)"
    )
    pose_data: list[FramePose] = Field(
        default_factory=list,
        description="Frame-by-frame pose data for visualization"
    )


class UploadResponse(BaseModel):
    """Response after successful video upload."""
    success: bool
    video_id: str
    message: str

