"""
Shot Segmentation Module.

Detects the temporal boundaries of an overhead smash:
- Shot start: Peak knee flexion (loading phase)
- Contact point: Peak wrist velocity (impact proxy)
- Timeline normalization to 0-100% for comparison

The overhead smash has distinct phases:
1. Preparation: Player loads weight, flexes knees
2. Backswing: Racket drawn back, rotation begins
3. Forward swing: Kinetic chain uncoils
4. Contact: Maximum wrist velocity at shuttle impact
5. Follow-through: Deceleration and recovery
"""
import numpy as np
from scipy import signal
from typing import Optional
from ..models.schemas import FramePose, ShotSegment, Keypoint


# Minimum frames needed for reliable shot detection
MIN_FRAMES_FOR_ANALYSIS = 15

# Smoothing window for velocity calculations (frames)
SMOOTHING_WINDOW = 5


class ShotSegmenter:
    """
    Detects overhead smash boundaries using biomechanical markers.
    
    Uses knee flexion to detect loading phase start and
    wrist velocity peak to detect contact point.
    """
    
    def __init__(self, dominant_hand: str = "right"):
        """
        Initialize segmenter with player's dominant hand.
        
        Args:
            dominant_hand: "left" or "right" - determines which side to analyze
        """
        self.dominant_hand = dominant_hand
        # Select appropriate joints based on dominant hand
        self.wrist_key = f"{dominant_hand}_wrist"
        self.elbow_key = f"{dominant_hand}_elbow"
        self.shoulder_key = f"{dominant_hand}_shoulder"
        self.knee_key = f"{dominant_hand}_knee"
        self.hip_key = f"{dominant_hand}_hip"
    
    def segment_shot(
        self,
        poses: list[FramePose],
        fps: float
    ) -> Optional[ShotSegment]:
        """
        Detect shot boundaries from pose sequence.
        
        Args:
            poses: List of frame poses
            fps: Video frames per second
            
        Returns:
            ShotSegment with start/contact frames, or None if detection fails
        """
        if len(poses) < MIN_FRAMES_FOR_ANALYSIS:
            return None
        
        # Extract time series data for segmentation
        knee_angles = self._compute_knee_angles(poses)
        wrist_velocities = self._compute_wrist_velocities(poses, fps)
        
        if knee_angles is None or wrist_velocities is None:
            return None
        
        # Smooth signals to reduce noise
        knee_angles_smooth = self._smooth_signal(knee_angles)
        wrist_velocities_smooth = self._smooth_signal(wrist_velocities)
        
        # Find shot start: peak knee flexion (minimum angle = maximum flexion)
        # During loading phase, player bends knees to store energy
        start_frame = self._find_knee_flexion_peak(knee_angles_smooth)
        
        # Find contact: peak wrist velocity
        # At contact, wrist reaches maximum speed in the kinetic chain
        contact_frame = self._find_wrist_velocity_peak(
            wrist_velocities_smooth,
            start_frame
        )
        
        if start_frame is None or contact_frame is None:
            return None
        
        # Ensure valid order
        if start_frame >= contact_frame:
            return None
        
        # End frame is slightly after contact for follow-through
        end_frame = min(contact_frame + int(fps * 0.1), len(poses) - 1)
        
        total_frames = contact_frame - start_frame
        duration_ms = (total_frames / fps) * 1000 if fps > 0 else 0
        
        return ShotSegment(
            start_frame=start_frame,
            contact_frame=contact_frame,
            end_frame=end_frame,
            total_frames=total_frames,
            duration_ms=duration_ms
        )
    
    def _compute_knee_angles(self, poses: list[FramePose]) -> Optional[np.ndarray]:
        """
        Compute knee flexion angles across all frames.
        
        Knee angle is measured as hip-knee-ankle angle.
        Smaller angle = more flexion (bent knee).
        
        Returns:
            Array of knee angles in degrees, or None if data insufficient
        """
        angles = []
        
        for pose in poses:
            kp = pose.keypoints
            
            # Check all required keypoints exist and are visible
            hip = kp.get(self.hip_key)
            knee = kp.get(self.knee_key)
            ankle = kp.get(f"{self.dominant_hand}_ankle")
            
            if not all([hip, knee, ankle]):
                angles.append(np.nan)
                continue
            
            # Low visibility = unreliable detection
            if min(hip.visibility, knee.visibility, ankle.visibility) < 0.5:
                angles.append(np.nan)
                continue
            
            angle = self._compute_joint_angle(
                (hip.x, hip.y),
                (knee.x, knee.y),
                (ankle.x, ankle.y)
            )
            angles.append(angle)
        
        angles = np.array(angles)
        
        # Need enough valid data points
        if np.sum(~np.isnan(angles)) < MIN_FRAMES_FOR_ANALYSIS:
            return None
        
        # Interpolate missing values
        angles = self._interpolate_nans(angles)
        
        return angles
    
    def _compute_wrist_velocities(
        self,
        poses: list[FramePose],
        fps: float
    ) -> Optional[np.ndarray]:
        """
        Compute wrist velocity magnitude across frames.
        
        Velocity is computed as frame-to-frame displacement.
        Units: pixels per second.
        
        Returns:
            Array of wrist velocities, or None if data insufficient
        """
        positions = []
        
        for pose in poses:
            wrist = pose.keypoints.get(self.wrist_key)
            
            if wrist and wrist.visibility > 0.5:
                positions.append((wrist.x, wrist.y))
            else:
                positions.append((np.nan, np.nan))
        
        positions = np.array(positions)
        
        # Need enough valid data
        valid_count = np.sum(~np.isnan(positions[:, 0]))
        if valid_count < MIN_FRAMES_FOR_ANALYSIS:
            return None
        
        # Interpolate missing positions
        positions[:, 0] = self._interpolate_nans(positions[:, 0])
        positions[:, 1] = self._interpolate_nans(positions[:, 1])
        
        # Compute velocities using central differences
        velocities = np.zeros(len(positions))
        dt = 1.0 / fps if fps > 0 else 1.0
        
        for i in range(1, len(positions) - 1):
            dx = positions[i + 1, 0] - positions[i - 1, 0]
            dy = positions[i + 1, 1] - positions[i - 1, 1]
            # Velocity magnitude
            velocities[i] = np.sqrt(dx**2 + dy**2) / (2 * dt)
        
        # Handle edge frames
        velocities[0] = velocities[1]
        velocities[-1] = velocities[-2]
        
        return velocities
    
    def _compute_joint_angle(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float]
    ) -> float:
        """
        Compute angle at p2 formed by p1-p2-p3.
        
        Uses dot product formula: cos(θ) = (v1 · v2) / (|v1| |v2|)
        
        Returns:
            Angle in degrees (0-180)
        """
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        return np.degrees(np.arccos(cos_angle))
    
    def _find_knee_flexion_peak(self, angles: np.ndarray) -> Optional[int]:
        """
        Find frame with maximum knee flexion (minimum angle).
        
        Only searches first 60% of video to avoid finding
        landing phase flexion.
        
        Returns:
            Frame index of peak flexion, or None
        """
        search_end = int(len(angles) * 0.6)
        
        if search_end < 5:
            return None
        
        # Find local minima (peaks in flexion)
        # Negative because we want minima
        peaks, properties = signal.find_peaks(
            -angles[:search_end],
            prominence=5,  # Minimum 5 degrees prominence
            distance=3     # Minimum frames between peaks
        )
        
        if len(peaks) == 0:
            # Fall back to global minimum
            return int(np.argmin(angles[:search_end]))
        
        # Return the most prominent peak
        most_prominent_idx = np.argmax(properties["prominences"])
        return int(peaks[most_prominent_idx])
    
    def _find_wrist_velocity_peak(
        self,
        velocities: np.ndarray,
        after_frame: int
    ) -> Optional[int]:
        """
        Find frame with peak wrist velocity after shot start.
        
        Args:
            velocities: Wrist velocity array
            after_frame: Search only after this frame (shot start)
            
        Returns:
            Frame index of peak velocity, or None
        """
        if after_frame >= len(velocities) - 5:
            return None
        
        search_region = velocities[after_frame:]
        
        # Find peaks in velocity
        peaks, properties = signal.find_peaks(
            search_region,
            prominence=np.std(search_region) * 0.5,
            distance=3
        )
        
        if len(peaks) == 0:
            # Fall back to global maximum
            return after_frame + int(np.argmax(search_region))
        
        # Return the highest peak
        highest_idx = np.argmax(search_region[peaks])
        return after_frame + int(peaks[highest_idx])
    
    def _smooth_signal(self, data: np.ndarray) -> np.ndarray:
        """Apply Savitzky-Golay filter for smoothing."""
        if len(data) < SMOOTHING_WINDOW:
            return data
        
        window = min(SMOOTHING_WINDOW, len(data) - 1)
        if window % 2 == 0:
            window -= 1
        if window < 3:
            return data
        
        return signal.savgol_filter(data, window, polyorder=2)
    
    def _interpolate_nans(self, data: np.ndarray) -> np.ndarray:
        """Linear interpolation of NaN values."""
        data = data.copy()
        nans = np.isnan(data)
        
        if nans.all():
            return data
        
        indices = np.arange(len(data))
        data[nans] = np.interp(
            indices[nans],
            indices[~nans],
            data[~nans]
        )
        
        return data
    
    def normalize_timeline(
        self,
        frame: int,
        start_frame: int,
        contact_frame: int
    ) -> float:
        """
        Normalize frame number to 0-100% timeline.
        
        0% = shot start (knee flexion peak)
        100% = contact (wrist velocity peak)
        
        Returns:
            Normalized percentage (can be < 0 or > 100 for frames outside range)
        """
        if contact_frame == start_frame:
            return 0.0
        
        return ((frame - start_frame) / (contact_frame - start_frame)) * 100

