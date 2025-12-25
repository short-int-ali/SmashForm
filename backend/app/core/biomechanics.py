"""
Biomechanics Feature Extraction Module.

Extracts key biomechanical features from pose data for overhead smash analysis.

Feature Categories:
1. Upper Body Rotation: Shoulder rotation and angular velocity
2. Arm Mechanics: Elbow extension, wrist snap timing
3. Lower Body: Knee flexion, hip-shoulder separation
4. Kinetic Chain: Timing sequence, center of mass

The kinetic chain in an overhead smash follows this sequence:
Legs → Hips → Trunk → Shoulder → Elbow → Wrist

Proper sequencing with small delays between segments creates
maximum energy transfer and racket head speed.
"""
import numpy as np
from scipy import signal
from typing import Optional
from ..models.schemas import FramePose, ShotSegment


class BiomechanicsExtractor:
    """
    Extracts biomechanical features from pose sequences.
    
    All angles are in degrees, velocities in degrees/second,
    timings in milliseconds or normalized percentage.
    """
    
    def __init__(self, dominant_hand: str = "right", fps: float = 30.0):
        """
        Initialize extractor with player configuration.
        
        Args:
            dominant_hand: "left" or "right"
            fps: Video frames per second for velocity calculations
        """
        self.dominant_hand = dominant_hand
        self.fps = fps
        
        # Joint key shortcuts based on dominant hand
        self.dom = dominant_hand
        self.non_dom = "left" if dominant_hand == "right" else "right"
    
    def extract_all_features(
        self,
        poses: list[FramePose],
        segment: ShotSegment
    ) -> dict[str, float]:
        """
        Extract all biomechanical features for the shot.
        
        Args:
            poses: Full pose sequence
            segment: Shot temporal boundaries
            
        Returns:
            Dictionary of feature names to values
        """
        # Get poses within shot segment
        shot_poses = [
            p for p in poses
            if segment.start_frame <= p.frame_number <= segment.end_frame
        ]
        
        if len(shot_poses) < 5:
            return {}
        
        features = {}
        
        # 1. Shoulder Rotation
        shoulder_rotation = self._compute_shoulder_rotation(shot_poses)
        if shoulder_rotation is not None:
            features["shoulder_rotation_angle"] = shoulder_rotation["max_rotation"]
            features["shoulder_angular_velocity"] = shoulder_rotation["max_velocity"]
        
        # 2. Elbow Extension
        elbow_extension = self._compute_elbow_extension(shot_poses)
        if elbow_extension is not None:
            features["elbow_extension_angle"] = elbow_extension["max_angle"]
            features["elbow_angular_velocity"] = elbow_extension["max_velocity"]
        
        # 3. Wrist Snap Timing
        wrist_timing = self._compute_wrist_snap_timing(shot_poses, segment)
        if wrist_timing is not None:
            features["wrist_snap_timing"] = wrist_timing
        
        # 4. Hip-Shoulder Separation
        hip_shoulder_sep = self._compute_hip_shoulder_separation(shot_poses)
        if hip_shoulder_sep is not None:
            features["hip_shoulder_separation"] = hip_shoulder_sep
        
        # 5. Knee Flexion at Loading
        knee_flexion = self._compute_knee_flexion(shot_poses)
        if knee_flexion is not None:
            features["knee_flexion_angle"] = knee_flexion
        
        # 6. Center of Mass Vertical Displacement
        com_displacement = self._compute_com_vertical_displacement(shot_poses)
        if com_displacement is not None:
            features["com_vertical_displacement"] = com_displacement
        
        # 7. Kinetic Chain Delays
        kinetic_delays = self._compute_kinetic_chain_delays(shot_poses, segment)
        if kinetic_delays is not None:
            features["hip_shoulder_delay"] = kinetic_delays.get("hip_shoulder", 0)
            features["shoulder_elbow_delay"] = kinetic_delays.get("shoulder_elbow", 0)
            features["elbow_wrist_delay"] = kinetic_delays.get("elbow_wrist", 0)
        
        # 8. Total Swing Duration
        features["swing_duration_ms"] = segment.duration_ms
        
        return features
    
    def _compute_shoulder_rotation(
        self,
        poses: list[FramePose]
    ) -> Optional[dict]:
        """
        Compute shoulder rotation angle and angular velocity.
        
        Shoulder rotation is measured as the angle of the shoulder line
        (connecting left and right shoulders) relative to the horizontal
        in the frontal plane.
        
        In a side view, this appears as the shoulder line tilting.
        """
        angles = []
        
        for pose in poses:
            kp = pose.keypoints
            left_shoulder = kp.get("left_shoulder")
            right_shoulder = kp.get("right_shoulder")
            
            if not (left_shoulder and right_shoulder):
                angles.append(np.nan)
                continue
            
            if min(left_shoulder.visibility, right_shoulder.visibility) < 0.5:
                angles.append(np.nan)
                continue
            
            # Shoulder rotation angle in side view
            # Using z-depth and x-position to estimate rotation
            dx = right_shoulder.x - left_shoulder.x
            dz = right_shoulder.z - left_shoulder.z
            
            # Rotation angle from side view perspective
            angle = np.degrees(np.arctan2(dz, dx + 1e-8))
            angles.append(angle)
        
        angles = np.array(angles)
        
        if np.sum(~np.isnan(angles)) < 3:
            return None
        
        # Interpolate and smooth
        angles = self._interpolate_nans(angles)
        angles = self._smooth(angles)
        
        # Compute angular velocity
        dt = 1.0 / self.fps
        angular_velocity = np.gradient(angles, dt)
        
        return {
            "max_rotation": float(np.max(np.abs(angles))),
            "max_velocity": float(np.max(np.abs(angular_velocity)))
        }
    
    def _compute_elbow_extension(
        self,
        poses: list[FramePose]
    ) -> Optional[dict]:
        """
        Compute elbow extension angle and velocity.
        
        Elbow angle is measured as shoulder-elbow-wrist angle.
        Full extension = 180 degrees.
        
        Key biomechanics insight:
        - At backswing: Elbow typically at 90-120 degrees
        - At contact: Should extend to 150-170 degrees
        - Never fully extend to avoid injury
        """
        angles = []
        
        for pose in poses:
            kp = pose.keypoints
            shoulder = kp.get(f"{self.dom}_shoulder")
            elbow = kp.get(f"{self.dom}_elbow")
            wrist = kp.get(f"{self.dom}_wrist")
            
            if not all([shoulder, elbow, wrist]):
                angles.append(np.nan)
                continue
            
            if min(shoulder.visibility, elbow.visibility, wrist.visibility) < 0.5:
                angles.append(np.nan)
                continue
            
            angle = self._joint_angle_2d(
                (shoulder.x, shoulder.y),
                (elbow.x, elbow.y),
                (wrist.x, wrist.y)
            )
            angles.append(angle)
        
        angles = np.array(angles)
        
        if np.sum(~np.isnan(angles)) < 3:
            return None
        
        angles = self._interpolate_nans(angles)
        angles = self._smooth(angles)
        
        # Angular velocity
        dt = 1.0 / self.fps
        angular_velocity = np.gradient(angles, dt)
        
        return {
            "max_angle": float(np.max(angles)),
            "max_velocity": float(np.max(np.abs(angular_velocity)))
        }
    
    def _compute_wrist_snap_timing(
        self,
        poses: list[FramePose],
        segment: ShotSegment
    ) -> Optional[float]:
        """
        Compute wrist snap timing relative to elbow peak velocity.
        
        The wrist snap should occur AFTER elbow reaches peak velocity
        for optimal energy transfer (kinetic chain principle).
        
        Returns:
            Timing difference in normalized timeline percentage.
            Positive = wrist peaks after elbow (correct).
            Negative = wrist peaks before elbow (inefficient).
        """
        elbow_velocities = []
        wrist_velocities = []
        
        prev_elbow = None
        prev_wrist = None
        
        for pose in poses:
            kp = pose.keypoints
            elbow = kp.get(f"{self.dom}_elbow")
            wrist = kp.get(f"{self.dom}_wrist")
            
            if prev_elbow and elbow and elbow.visibility > 0.5:
                dx = elbow.x - prev_elbow.x
                dy = elbow.y - prev_elbow.y
                elbow_velocities.append(np.sqrt(dx**2 + dy**2) * self.fps)
            else:
                elbow_velocities.append(np.nan)
            
            if prev_wrist and wrist and wrist.visibility > 0.5:
                dx = wrist.x - prev_wrist.x
                dy = wrist.y - prev_wrist.y
                wrist_velocities.append(np.sqrt(dx**2 + dy**2) * self.fps)
            else:
                wrist_velocities.append(np.nan)
            
            prev_elbow = elbow if elbow and elbow.visibility > 0.5 else prev_elbow
            prev_wrist = wrist if wrist and wrist.visibility > 0.5 else prev_wrist
        
        elbow_velocities = np.array(elbow_velocities)
        wrist_velocities = np.array(wrist_velocities)
        
        if np.sum(~np.isnan(elbow_velocities)) < 3:
            return None
        if np.sum(~np.isnan(wrist_velocities)) < 3:
            return None
        
        elbow_velocities = self._interpolate_nans(elbow_velocities)
        wrist_velocities = self._interpolate_nans(wrist_velocities)
        
        elbow_velocities = self._smooth(elbow_velocities)
        wrist_velocities = self._smooth(wrist_velocities)
        
        # Find peak frames
        elbow_peak_frame = np.argmax(elbow_velocities)
        wrist_peak_frame = np.argmax(wrist_velocities)
        
        # Convert to normalized timeline
        total_frames = len(poses)
        if total_frames <= 1:
            return None
        
        elbow_pct = (elbow_peak_frame / (total_frames - 1)) * 100
        wrist_pct = (wrist_peak_frame / (total_frames - 1)) * 100
        
        # Positive = wrist after elbow (correct)
        return float(wrist_pct - elbow_pct)
    
    def _compute_hip_shoulder_separation(
        self,
        poses: list[FramePose]
    ) -> Optional[float]:
        """
        Compute maximum hip-shoulder separation angle.
        
        This measures the rotational "coil" between hips and shoulders.
        Greater separation = more stored rotational energy.
        
        In elite players: 40-60 degrees separation at peak backswing.
        """
        separations = []
        
        for pose in poses:
            kp = pose.keypoints
            
            left_shoulder = kp.get("left_shoulder")
            right_shoulder = kp.get("right_shoulder")
            left_hip = kp.get("left_hip")
            right_hip = kp.get("right_hip")
            
            if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
                separations.append(np.nan)
                continue
            
            min_vis = min(
                left_shoulder.visibility, right_shoulder.visibility,
                left_hip.visibility, right_hip.visibility
            )
            if min_vis < 0.5:
                separations.append(np.nan)
                continue
            
            # Shoulder line angle
            shoulder_angle = np.degrees(np.arctan2(
                right_shoulder.y - left_shoulder.y,
                right_shoulder.x - left_shoulder.x
            ))
            
            # Hip line angle
            hip_angle = np.degrees(np.arctan2(
                right_hip.y - left_hip.y,
                right_hip.x - left_hip.x
            ))
            
            # Separation is the difference
            separation = abs(shoulder_angle - hip_angle)
            separations.append(separation)
        
        separations = np.array(separations)
        
        if np.sum(~np.isnan(separations)) < 3:
            return None
        
        separations = self._interpolate_nans(separations)
        
        # Return maximum separation (at peak coil)
        return float(np.max(separations))
    
    def _compute_knee_flexion(
        self,
        poses: list[FramePose]
    ) -> Optional[float]:
        """
        Compute minimum knee angle (maximum flexion) during loading.
        
        Proper knee flexion (90-130 degrees) allows:
        - Energy storage in leg muscles
        - Explosive push-off for jump smash
        - Stable base for rotation
        """
        angles = []
        
        for pose in poses:
            kp = pose.keypoints
            hip = kp.get(f"{self.dom}_hip")
            knee = kp.get(f"{self.dom}_knee")
            ankle = kp.get(f"{self.dom}_ankle")
            
            if not all([hip, knee, ankle]):
                angles.append(np.nan)
                continue
            
            if min(hip.visibility, knee.visibility, ankle.visibility) < 0.5:
                angles.append(np.nan)
                continue
            
            angle = self._joint_angle_2d(
                (hip.x, hip.y),
                (knee.x, knee.y),
                (ankle.x, ankle.y)
            )
            angles.append(angle)
        
        angles = np.array(angles)
        
        if np.sum(~np.isnan(angles)) < 3:
            return None
        
        angles = self._interpolate_nans(angles)
        
        # Return minimum angle (maximum flexion)
        return float(np.min(angles))
    
    def _compute_com_vertical_displacement(
        self,
        poses: list[FramePose]
    ) -> Optional[float]:
        """
        Compute center of mass vertical displacement during shot.
        
        CoM is estimated as the midpoint between hips.
        
        Positive displacement indicates upward movement (jump smash).
        Returns displacement in pixels (normalized to frame height later).
        """
        com_y = []
        
        for pose in poses:
            kp = pose.keypoints
            left_hip = kp.get("left_hip")
            right_hip = kp.get("right_hip")
            
            if left_hip and right_hip:
                if min(left_hip.visibility, right_hip.visibility) > 0.5:
                    # Average Y position (lower Y = higher in frame)
                    com_y.append((left_hip.y + right_hip.y) / 2)
                    continue
            
            com_y.append(np.nan)
        
        com_y = np.array(com_y)
        
        if np.sum(~np.isnan(com_y)) < 3:
            return None
        
        com_y = self._interpolate_nans(com_y)
        
        # Displacement is min - max (since Y is inverted in image coords)
        # Positive value means upward movement
        displacement = np.max(com_y) - np.min(com_y)
        
        return float(displacement)
    
    def _compute_kinetic_chain_delays(
        self,
        poses: list[FramePose],
        segment: ShotSegment
    ) -> Optional[dict[str, float]]:
        """
        Compute timing delays between segments in kinetic chain.
        
        Optimal kinetic chain sequence:
        Hips → Shoulders → Elbow → Wrist
        
        Each segment should reach peak velocity slightly after
        the previous segment (10-30ms delays typical).
        
        Returns:
            Dictionary with delays in percentage of shot timeline.
        """
        # Compute rotational velocities for each segment
        hip_rot = self._segment_rotation_velocity(poses, "hip")
        shoulder_rot = self._segment_rotation_velocity(poses, "shoulder")
        elbow_vel = self._segment_velocity(poses, f"{self.dom}_elbow")
        wrist_vel = self._segment_velocity(poses, f"{self.dom}_wrist")
        
        results = {}
        
        # Find peak frames
        if hip_rot is not None and shoulder_rot is not None:
            hip_peak = np.argmax(hip_rot)
            shoulder_peak = np.argmax(shoulder_rot)
            delay_frames = shoulder_peak - hip_peak
            results["hip_shoulder"] = float(delay_frames / self.fps * 1000)  # ms
        
        if shoulder_rot is not None and elbow_vel is not None:
            shoulder_peak = np.argmax(shoulder_rot)
            elbow_peak = np.argmax(elbow_vel)
            delay_frames = elbow_peak - shoulder_peak
            results["shoulder_elbow"] = float(delay_frames / self.fps * 1000)
        
        if elbow_vel is not None and wrist_vel is not None:
            elbow_peak = np.argmax(elbow_vel)
            wrist_peak = np.argmax(wrist_vel)
            delay_frames = wrist_peak - elbow_peak
            results["elbow_wrist"] = float(delay_frames / self.fps * 1000)
        
        return results if results else None
    
    def _segment_rotation_velocity(
        self,
        poses: list[FramePose],
        segment: str
    ) -> Optional[np.ndarray]:
        """Compute rotational velocity for hip or shoulder segment."""
        if segment == "hip":
            left_key, right_key = "left_hip", "right_hip"
        else:
            left_key, right_key = "left_shoulder", "right_shoulder"
        
        angles = []
        for pose in poses:
            kp = pose.keypoints
            left = kp.get(left_key)
            right = kp.get(right_key)
            
            if left and right and min(left.visibility, right.visibility) > 0.5:
                angle = np.degrees(np.arctan2(
                    right.y - left.y,
                    right.x - left.x
                ))
                angles.append(angle)
            else:
                angles.append(np.nan)
        
        angles = np.array(angles)
        if np.sum(~np.isnan(angles)) < 3:
            return None
        
        angles = self._interpolate_nans(angles)
        angles = self._smooth(angles)
        
        # Angular velocity
        velocity = np.abs(np.gradient(angles, 1.0 / self.fps))
        return velocity
    
    def _segment_velocity(
        self,
        poses: list[FramePose],
        joint_key: str
    ) -> Optional[np.ndarray]:
        """Compute linear velocity for a specific joint."""
        positions = []
        
        for pose in poses:
            joint = pose.keypoints.get(joint_key)
            if joint and joint.visibility > 0.5:
                positions.append((joint.x, joint.y))
            else:
                positions.append((np.nan, np.nan))
        
        positions = np.array(positions)
        if np.sum(~np.isnan(positions[:, 0])) < 3:
            return None
        
        positions[:, 0] = self._interpolate_nans(positions[:, 0])
        positions[:, 1] = self._interpolate_nans(positions[:, 1])
        
        # Velocity magnitude
        dt = 1.0 / self.fps
        dx = np.gradient(positions[:, 0], dt)
        dy = np.gradient(positions[:, 1], dt)
        velocity = np.sqrt(dx**2 + dy**2)
        
        return self._smooth(velocity)
    
    def _joint_angle_2d(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float]
    ) -> float:
        """Compute 2D angle at p2 formed by p1-p2-p3."""
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        return float(np.degrees(np.arccos(cos_angle)))
    
    def _interpolate_nans(self, data: np.ndarray) -> np.ndarray:
        """Linear interpolation of NaN values."""
        data = data.copy()
        nans = np.isnan(data)
        if nans.all():
            return np.zeros_like(data)
        indices = np.arange(len(data))
        data[nans] = np.interp(indices[nans], indices[~nans], data[~nans])
        return data
    
    def _smooth(self, data: np.ndarray, window: int = 5) -> np.ndarray:
        """Savitzky-Golay smoothing filter."""
        if len(data) < window:
            return data
        if window % 2 == 0:
            window -= 1
        if window < 3:
            return data
        return signal.savgol_filter(data, window, polyorder=2)

