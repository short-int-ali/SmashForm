"""
Pose Extraction Module using MediaPipe Pose.

Extracts 2D/3D keypoints from video frames for biomechanical analysis.
Focuses on keypoints relevant to overhead smash mechanics:
- Shoulders, elbows, wrists (upper body kinetic chain)
- Hips (rotation and power generation)
- Knees, ankles (lower body loading and push-off)
"""
import cv2
import mediapipe as mp
import numpy as np
from typing import Optional
from ..models.schemas import Keypoint, FramePose


# MediaPipe landmark indices for relevant joints
# Reference: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
LANDMARK_MAPPING = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    # Additional landmarks for reference
    "nose": 0,
    "left_ear": 7,
    "right_ear": 8,
}


class PoseExtractor:
    """
    Extracts pose keypoints from video using MediaPipe Pose.
    
    MediaPipe Pose provides 33 3D landmarks. We extract only the
    biomechanically relevant points for smash analysis.
    """
    
    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 2  # 0, 1, or 2 - higher is more accurate
    ):
        """
        Initialize MediaPipe Pose with specified confidence thresholds.
        
        Args:
            min_detection_confidence: Minimum confidence for initial detection
            min_tracking_confidence: Minimum confidence for tracking between frames
            model_complexity: Model complexity (2 = most accurate for analysis)
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            enable_segmentation=False,
        )
    
    def extract_from_video(self, video_path: str) -> tuple[list[FramePose], dict]:
        """
        Extract pose keypoints from all frames of a video.
        
        Args:
            video_path: Path to the input video file
            
        Returns:
            Tuple of (list of FramePose, video metadata dict)
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        metadata = {
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration_ms": (total_frames / fps) * 1000 if fps > 0 else 0
        }
        
        poses = []
        frame_number = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # MediaPipe expects RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame
            results = self.pose.process(frame_rgb)
            
            if results.pose_landmarks:
                # Convert landmarks to our schema
                keypoints = self._extract_keypoints(
                    results.pose_landmarks.landmark,
                    width,
                    height
                )
                
                timestamp_ms = (frame_number / fps) * 1000 if fps > 0 else 0
                
                poses.append(FramePose(
                    frame_number=frame_number,
                    timestamp_ms=timestamp_ms,
                    keypoints=keypoints
                ))
            
            frame_number += 1
        
        cap.release()
        
        return poses, metadata
    
    def _extract_keypoints(
        self,
        landmarks,
        frame_width: int,
        frame_height: int
    ) -> dict[str, Keypoint]:
        """
        Extract relevant keypoints from MediaPipe landmarks.
        
        Coordinates are normalized to frame dimensions.
        Z coordinate represents depth relative to hip midpoint.
        
        Args:
            landmarks: MediaPipe pose landmarks
            frame_width: Video frame width for denormalization
            frame_height: Video frame height for denormalization
            
        Returns:
            Dictionary mapping joint names to Keypoint objects
        """
        keypoints = {}
        
        for joint_name, landmark_idx in LANDMARK_MAPPING.items():
            lm = landmarks[landmark_idx]
            keypoints[joint_name] = Keypoint(
                # Store as pixel coordinates for easier visualization
                x=lm.x * frame_width,
                y=lm.y * frame_height,
                # Z is depth - negative means closer to camera
                z=lm.z * frame_width,  # Scale z similarly for consistency
                visibility=lm.visibility
            )
        
        return keypoints
    
    def close(self):
        """Release MediaPipe resources."""
        self.pose.close()

