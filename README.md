# SmashForm

**Biomechanics-based badminton coaching platform for overhead smash analysis.**

SmashForm analyzes your overhead smash technique from video, extracts biomechanical features using MediaPipe pose estimation, and compares them against elite player reference profiles to provide actionable feedback.

![SmashForm](https://img.shields.io/badge/MVP-v1.0-emerald?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![React](https://img.shields.io/badge/React-18-cyan?style=flat-square)

---

## 🎯 What This System Measures

### Biomechanical Features (10 Metrics)

| Metric | Description | Elite Reference |
|--------|-------------|-----------------|
| **Shoulder Rotation** | Maximum rotation angle during backswing | 45° |
| **Shoulder Angular Velocity** | Peak rotational speed | 800 deg/s |
| **Elbow Extension** | Arm angle at contact point | 165° |
| **Elbow Angular Velocity** | Speed of arm extension | 1200 deg/s |
| **Wrist Snap Timing** | When wrist peaks vs elbow | +8% (after) |
| **Hip-Shoulder Separation** | Rotational coil between hips/shoulders | 45° |
| **Knee Flexion** | Knee bend during loading phase | 120° |
| **Vertical Displacement** | Upward body movement (jump smash) | 80 px |
| **Kinetic Chain Delays** | Hip→Shoulder→Elbow→Wrist timing | 25/20/15 ms |
| **Swing Duration** | Total time from load to contact | 250 ms |

### The Kinetic Chain

An efficient smash follows a proximal-to-distal sequence:

```
Legs → Hips → Trunk → Shoulder → Elbow → Wrist
```

Each segment reaches peak velocity slightly after the previous one, creating a "whip" effect that maximizes racket head speed at contact.

---

## 📹 Camera Placement (IMPORTANT)

**This system requires a SIDE-VIEW video.**

### For Right-Handed Players:
- Place camera on the **LEFT** side of the court
- Camera should be perpendicular to the player's facing direction
- This captures the dominant arm's full range of motion

### For Left-Handed Players:
- Place camera on the **RIGHT** side of the court

### Recording Guidelines:
1. **Side View**: Camera 90° to player's facing direction
2. **Full Body**: Ensure entire body visible throughout swing
3. **Stable**: Use tripod or stable surface
4. **Good Lighting**: Well-lit environment helps pose detection
5. **Clear Background**: Minimize clutter behind player

```
         [CAMERA]
            |
            v
    ┌───────────────┐
    │               │
    │    [PLAYER]   │  ← Facing forward (toward net)
    │               │
    └───────────────┘
         COURT
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- pip
- npm or yarn

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The app will be available at `http://localhost:3000`

---

## 📁 Project Structure

```
SmashForm/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── api/
│   │   │   └── routes.py        # API endpoints
│   │   ├── core/
│   │   │   ├── pose_extractor.py    # MediaPipe pose detection
│   │   │   ├── shot_segmenter.py    # Detect shot boundaries
│   │   │   ├── biomechanics.py      # Feature extraction
│   │   │   └── comparison.py        # Reference comparison
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── data/
│   │   └── reference_profile.json   # Elite player reference
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx
│   │   │   ├── UploadPage.jsx
│   │   │   └── AnalysisPage.jsx
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   └── tailwind.config.js
│
└── README.md
```

---

## 🔌 API Endpoints

### `POST /api/upload`
Upload a video file for analysis.

**Request**: `multipart/form-data` with `video` file

**Response**:
```json
{
  "success": true,
  "video_id": "uuid-string",
  "message": "Video uploaded successfully"
}
```

### `POST /api/analyze`
Run biomechanics analysis on uploaded video.

**Request**: `form-data` with:
- `video_id`: string
- `dominant_hand`: "left" | "right"

**Response**:
```json
{
  "success": true,
  "video_id": "...",
  "technique_similarity_score": 75.5,
  "shot_segment": {
    "start_frame": 45,
    "contact_frame": 78,
    "duration_ms": 267
  },
  "metrics": [
    {
      "name": "shoulder_rotation_angle",
      "display_name": "Shoulder Rotation",
      "user_value": 42.3,
      "reference_value": 45.0,
      "unit": "degrees",
      "difference": -2.7,
      "difference_percent": -6.0,
      "severity": "low",
      "description": "..."
    }
  ],
  "pose_data": [...]
}
```

### `GET /api/reference`
Get reference profile values.

---

## ⚠️ MVP Limitations

This is a Minimum Viable Product with intentional constraints:

| Feature | Status |
|---------|--------|
| Shot type | **Overhead smash only** |
| Camera angle | **Side view only** |
| Videos per analysis | **Single video** |
| Processing mode | **Batch (upload → analyze)** |
| Authentication | **None** |
| Database | **JSON files only** |
| Real-time feedback | **Not supported** |

### What This System Does NOT Do:

- ❌ Real-time video processing
- ❌ Multiple camera angles
- ❌ Other shot types (clears, drops, net shots)
- ❌ Deep learning-based technique classification
- ❌ User accounts or history
- ❌ Mobile app support

---

## 🧬 Technical Details

### Pose Detection

Uses **MediaPipe Pose** with:
- Model complexity: 2 (highest accuracy)
- Min detection confidence: 0.5
- Min tracking confidence: 0.5

Extracts 12+ keypoints: shoulders, elbows, wrists, hips, knees, ankles.

### Shot Segmentation

1. **Start Detection**: Peak knee flexion (loading phase)
2. **Contact Detection**: Peak wrist velocity
3. **Timeline Normalization**: 0% = start, 100% = contact

### Feature Extraction

All features computed from 2D keypoint trajectories:
- Joint angles via vector dot product
- Velocities via central differences
- Smoothing via Savitzky-Golay filter

### Comparison

- Absolute difference from reference
- Severity classification: low (<15%), medium (<30%), high (>30%)
- Weighted similarity score (0-100)

---

## 🤝 Contributing

This is an MVP. For production use, consider:

1. Adding more shot types
2. Supporting multiple camera angles
3. Implementing 3D pose estimation
4. Adding user accounts and history
5. Real-time feedback via WebSocket

---

## 📄 License

MIT License - Use freely for personal and commercial projects.

---

Built with ❤️ for the badminton community.

