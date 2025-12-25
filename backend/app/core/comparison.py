"""
Reference Comparison Module.

Compares extracted biomechanics features against a reference profile
and generates similarity scores with severity levels.

Reference profiles are based on biomechanics literature and
elite player analysis (not real-time ML predictions).
"""
import json
import os
from typing import Optional
from ..models.schemas import BiomechanicsMetric, SeverityLevel


# Threshold percentages for severity classification
# These determine how much deviation from reference is acceptable
SEVERITY_THRESHOLDS = {
    "low": 15,      # Within 15% of reference = good
    "medium": 30,   # Within 30% = needs attention
    # Above 30% = high severity, significant deviation
}

# Feature metadata: display names, units, descriptions, reference values
# Reference values based on biomechanics literature for elite smash technique
FEATURE_METADATA = {
    "shoulder_rotation_angle": {
        "display_name": "Shoulder Rotation",
        "unit": "degrees",
        "reference": 45.0,  # Peak rotation angle
        "description": "Maximum shoulder rotation during backswing. Greater rotation stores more energy.",
        "higher_is_better": True,
        "tolerance": 10.0,  # Absolute tolerance for low severity
    },
    "shoulder_angular_velocity": {
        "display_name": "Shoulder Angular Velocity",
        "unit": "deg/s",
        "reference": 800.0,  # Peak angular velocity
        "description": "Peak rotational speed of shoulders during swing.",
        "higher_is_better": True,
        "tolerance": 150.0,
    },
    "elbow_extension_angle": {
        "display_name": "Elbow Extension",
        "unit": "degrees",
        "reference": 165.0,  # Near-full extension at contact
        "description": "Elbow angle at contact. Should be nearly extended but not locked.",
        "higher_is_better": True,  # Up to a point
        "tolerance": 10.0,
    },
    "elbow_angular_velocity": {
        "display_name": "Elbow Angular Velocity",
        "unit": "deg/s",
        "reference": 1200.0,  # High speed extension
        "description": "Speed of elbow extension. Higher = more power.",
        "higher_is_better": True,
        "tolerance": 200.0,
    },
    "wrist_snap_timing": {
        "display_name": "Wrist Snap Timing",
        "unit": "%",
        "reference": 8.0,  # Wrist peaks 8% after elbow
        "description": "When wrist peaks relative to elbow. Positive = after elbow (correct).",
        "higher_is_better": None,  # Optimal is close to reference
        "tolerance": 3.0,
    },
    "hip_shoulder_separation": {
        "display_name": "Hip-Shoulder Separation",
        "unit": "degrees",
        "reference": 45.0,  # Good separation at peak coil
        "description": "Angular difference between hip and shoulder lines. More = more power potential.",
        "higher_is_better": True,
        "tolerance": 8.0,
    },
    "knee_flexion_angle": {
        "display_name": "Knee Flexion",
        "unit": "degrees",
        "reference": 120.0,  # Moderate flexion for loading
        "description": "Knee bend during loading phase. Optimal ~120° for power without compromising stability.",
        "higher_is_better": None,  # Too much or too little is bad
        "tolerance": 15.0,
    },
    "com_vertical_displacement": {
        "display_name": "Vertical Displacement",
        "unit": "pixels",
        "reference": 80.0,  # Significant upward movement
        "description": "How much the body rises during swing (jump smash component).",
        "higher_is_better": True,
        "tolerance": 20.0,
    },
    "hip_shoulder_delay": {
        "display_name": "Hip-Shoulder Delay",
        "unit": "ms",
        "reference": 25.0,  # ~25ms between hip and shoulder peak
        "description": "Time between hip and shoulder peak velocity. Proper sequencing = 20-30ms.",
        "higher_is_better": None,
        "tolerance": 10.0,
    },
    "shoulder_elbow_delay": {
        "display_name": "Shoulder-Elbow Delay",
        "unit": "ms",
        "reference": 20.0,  # ~20ms between shoulder and elbow
        "description": "Time between shoulder and elbow peak velocity.",
        "higher_is_better": None,
        "tolerance": 8.0,
    },
    "elbow_wrist_delay": {
        "display_name": "Elbow-Wrist Delay",
        "unit": "ms",
        "reference": 15.0,  # ~15ms between elbow and wrist
        "description": "Time between elbow and wrist peak velocity.",
        "higher_is_better": None,
        "tolerance": 6.0,
    },
    "swing_duration_ms": {
        "display_name": "Swing Duration",
        "unit": "ms",
        "reference": 250.0,  # ~250ms from load to contact
        "description": "Total time from knee flexion to contact. Too fast = less power, too slow = telegraphed.",
        "higher_is_better": None,
        "tolerance": 40.0,
    },
}


class ReferenceComparator:
    """
    Compares user biomechanics to reference profiles.
    
    Uses predefined reference values based on biomechanics research.
    Can also load custom reference profiles from JSON.
    """
    
    def __init__(self, reference_path: Optional[str] = None):
        """
        Initialize comparator with optional custom reference file.
        
        Args:
            reference_path: Path to custom JSON reference profile.
                          If None, uses built-in defaults.
        """
        self.reference = self._load_reference(reference_path)
    
    def _load_reference(self, path: Optional[str]) -> dict:
        """Load reference values from file or use defaults."""
        if path and os.path.exists(path):
            with open(path, 'r') as f:
                custom = json.load(f)
            # Merge with defaults (custom overrides defaults)
            reference = {}
            for key, meta in FEATURE_METADATA.items():
                reference[key] = custom.get(key, {}).get("reference", meta["reference"])
            return reference
        
        # Use defaults from metadata
        return {key: meta["reference"] for key, meta in FEATURE_METADATA.items()}
    
    def compare(self, extracted_features: dict[str, float]) -> list[BiomechanicsMetric]:
        """
        Compare extracted features against reference.
        
        Args:
            extracted_features: Dictionary of feature name to extracted value
            
        Returns:
            List of BiomechanicsMetric with comparisons
        """
        metrics = []
        
        for feature_name, user_value in extracted_features.items():
            if feature_name not in FEATURE_METADATA:
                continue
            
            meta = FEATURE_METADATA[feature_name]
            ref_value = self.reference.get(feature_name, meta["reference"])
            
            # Compute difference
            difference = user_value - ref_value
            
            # Compute percentage difference (handle zero reference)
            if ref_value != 0:
                diff_percent = (difference / ref_value) * 100
            else:
                diff_percent = 100 if difference != 0 else 0
            
            # Determine severity based on absolute difference vs tolerance
            severity = self._classify_severity(
                difference,
                meta["tolerance"],
                meta.get("higher_is_better")
            )
            
            metrics.append(BiomechanicsMetric(
                name=feature_name,
                display_name=meta["display_name"],
                user_value=round(user_value, 1),
                reference_value=round(ref_value, 1),
                unit=meta["unit"],
                difference=round(difference, 1),
                difference_percent=round(diff_percent, 1),
                severity=severity,
                description=meta["description"]
            ))
        
        return metrics
    
    def _classify_severity(
        self,
        difference: float,
        tolerance: float,
        higher_is_better: Optional[bool]
    ) -> SeverityLevel:
        """
        Classify severity of deviation.
        
        Args:
            difference: Actual difference (user - reference)
            tolerance: Absolute tolerance for "low" severity
            higher_is_better: If True, positive difference is good.
                            If False, negative is good.
                            If None, closer to zero is better.
        """
        abs_diff = abs(difference)
        
        # Check if within tolerance
        if abs_diff <= tolerance:
            return SeverityLevel.LOW
        
        # Check if within 2x tolerance (medium)
        if abs_diff <= tolerance * 2:
            # If higher is better and user is higher, reduce severity
            if higher_is_better is True and difference > 0:
                return SeverityLevel.LOW
            # If higher is worse and user is lower, reduce severity
            if higher_is_better is False and difference < 0:
                return SeverityLevel.LOW
            return SeverityLevel.MEDIUM
        
        # Outside 2x tolerance = high severity
        # But if difference is in the "good" direction, cap at medium
        if higher_is_better is True and difference > 0:
            return SeverityLevel.MEDIUM
        if higher_is_better is False and difference < 0:
            return SeverityLevel.MEDIUM
        
        return SeverityLevel.HIGH
    
    def compute_similarity_score(
        self,
        metrics: list[BiomechanicsMetric]
    ) -> float:
        """
        Compute overall technique similarity score (0-100).
        
        Weighted average based on:
        - Feature importance
        - Severity level
        - Percentage deviation
        
        Returns:
            Similarity score where 100 = perfect match to reference
        """
        if not metrics:
            return 0.0
        
        # Weights for different feature categories
        FEATURE_WEIGHTS = {
            "shoulder_rotation_angle": 1.0,
            "shoulder_angular_velocity": 1.2,
            "elbow_extension_angle": 1.0,
            "elbow_angular_velocity": 1.2,
            "wrist_snap_timing": 1.5,  # Critical for power
            "hip_shoulder_separation": 1.0,
            "knee_flexion_angle": 0.8,
            "com_vertical_displacement": 0.6,
            "hip_shoulder_delay": 1.3,
            "shoulder_elbow_delay": 1.3,
            "elbow_wrist_delay": 1.3,
            "swing_duration_ms": 0.7,
        }
        
        total_weight = 0
        weighted_score = 0
        
        for metric in metrics:
            weight = FEATURE_WEIGHTS.get(metric.name, 1.0)
            total_weight += weight
            
            # Convert deviation to score (0-100 scale)
            # Use tolerance-based scoring
            meta = FEATURE_METADATA.get(metric.name, {})
            tolerance = meta.get("tolerance", 10)
            
            deviation_ratio = abs(metric.difference) / (tolerance * 2)
            deviation_ratio = min(deviation_ratio, 1.0)  # Cap at 100% deviation
            
            # Score: 100 at perfect match, decreasing with deviation
            feature_score = 100 * (1 - deviation_ratio)
            
            weighted_score += weight * feature_score
        
        if total_weight == 0:
            return 0.0
        
        return round(weighted_score / total_weight, 1)


def save_reference_profile(profile: dict, path: str) -> None:
    """
    Save a reference profile to JSON file.
    
    Args:
        profile: Dictionary with feature reference values
        path: Output file path
    """
    output = {}
    for key, value in profile.items():
        if key in FEATURE_METADATA:
            output[key] = {
                "reference": value,
                "display_name": FEATURE_METADATA[key]["display_name"],
                "unit": FEATURE_METADATA[key]["unit"],
            }
    
    with open(path, 'w') as f:
        json.dump(output, f, indent=2)

