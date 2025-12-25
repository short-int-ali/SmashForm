"""
API Routes for SmashForm.

Endpoints:
- POST /api/upload: Upload video for analysis
- POST /api/analyze: Run biomechanics analysis
- GET /api/reference: Get reference profile values
"""
import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from ..models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    UploadResponse,
    DominantHand,
    ShotSegment,
    FramePose,
)
from ..core.pose_extractor import PoseExtractor
from ..core.shot_segmenter import ShotSegmenter
from ..core.biomechanics import BiomechanicsExtractor
from ..core.comparison import ReferenceComparator, FEATURE_METADATA


router = APIRouter(prefix="/api", tags=["analysis"])

# Directory for uploaded videos
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Reference profile path
REFERENCE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "reference_profile.json"
)


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    video: UploadFile = File(..., description="MP4 video file of badminton smash"),
):
    """
    Upload a video for analysis.
    
    Accepts MP4 files only. Returns a video_id for subsequent analysis.
    """
    # Validate file type
    if not video.filename.lower().endswith(('.mp4', '.mov', '.avi')):
        raise HTTPException(
            status_code=400,
            detail="Only video files (MP4, MOV, AVI) are supported"
        )
    
    # Generate unique ID
    video_id = str(uuid.uuid4())
    
    # Save file
    file_ext = os.path.splitext(video.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{video_id}{file_ext}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save video: {str(e)}"
        )
    
    return UploadResponse(
        success=True,
        video_id=video_id,
        message="Video uploaded successfully. Use /api/analyze to process."
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(
    video_id: str = Form(..., description="Video ID from upload"),
    dominant_hand: str = Form("right", description="Player's dominant hand (left/right)"),
):
    """
    Analyze uploaded video for biomechanics.
    
    Extracts pose data, segments the shot, computes biomechanical
    features, and compares to reference profile.
    """
    # Find video file
    video_path = None
    for ext in ['.mp4', '.mov', '.avi']:
        path = os.path.join(UPLOAD_DIR, f"{video_id}{ext}")
        if os.path.exists(path):
            video_path = path
            break
    
    if not video_path:
        raise HTTPException(
            status_code=404,
            detail=f"Video not found: {video_id}"
        )
    
    # Validate dominant hand
    try:
        hand = DominantHand(dominant_hand.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="dominant_hand must be 'left' or 'right'"
        )
    
    try:
        # Step 1: Extract poses
        extractor = PoseExtractor()
        poses, metadata = extractor.extract_from_video(video_path)
        extractor.close()
        
        if len(poses) < 10:
            return AnalysisResponse(
                success=False,
                message="Could not detect enough pose frames. Ensure full body is visible.",
                video_id=video_id,
                dominant_hand=hand,
                shot_segment=None,
                metrics=[],
                technique_similarity_score=0,
                pose_data=poses,
            )
        
        fps = metadata.get("fps", 30.0)
        
        # Step 2: Segment shot
        segmenter = ShotSegmenter(dominant_hand=hand.value)
        segment = segmenter.segment_shot(poses, fps)
        
        if segment is None:
            return AnalysisResponse(
                success=False,
                message="Could not detect smash motion. Ensure video shows complete overhead smash.",
                video_id=video_id,
                dominant_hand=hand,
                shot_segment=None,
                metrics=[],
                technique_similarity_score=0,
                pose_data=poses,
            )
        
        # Step 3: Extract biomechanics features
        bio_extractor = BiomechanicsExtractor(
            dominant_hand=hand.value,
            fps=fps
        )
        features = bio_extractor.extract_all_features(poses, segment)
        
        if not features:
            return AnalysisResponse(
                success=False,
                message="Could not extract biomechanics features. Check video quality.",
                video_id=video_id,
                dominant_hand=hand,
                shot_segment=segment,
                metrics=[],
                technique_similarity_score=0,
                pose_data=poses,
            )
        
        # Step 4: Compare to reference
        comparator = ReferenceComparator(
            reference_path=REFERENCE_PATH if os.path.exists(REFERENCE_PATH) else None
        )
        metrics = comparator.compare(features)
        similarity_score = comparator.compute_similarity_score(metrics)
        
        # Filter pose data to shot segment for lighter response
        shot_poses = [
            p for p in poses
            if segment.start_frame <= p.frame_number <= segment.end_frame
        ]
        
        return AnalysisResponse(
            success=True,
            message="Analysis complete",
            video_id=video_id,
            dominant_hand=hand,
            shot_segment=segment,
            metrics=metrics,
            technique_similarity_score=similarity_score,
            pose_data=shot_poses,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/reference")
async def get_reference_profile():
    """
    Get the reference profile used for comparison.
    
    Returns all reference values with descriptions.
    """
    reference = {}
    for key, meta in FEATURE_METADATA.items():
        reference[key] = {
            "display_name": meta["display_name"],
            "reference_value": meta["reference"],
            "unit": meta["unit"],
            "description": meta["description"],
        }
    
    return JSONResponse(content=reference)


@router.delete("/video/{video_id}")
async def delete_video(video_id: str):
    """Delete an uploaded video."""
    deleted = False
    for ext in ['.mp4', '.mov', '.avi']:
        path = os.path.join(UPLOAD_DIR, f"{video_id}{ext}")
        if os.path.exists(path):
            os.remove(path)
            deleted = True
            break
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"success": True, "message": "Video deleted"}

