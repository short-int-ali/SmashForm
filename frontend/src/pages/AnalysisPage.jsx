import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Skeleton connections for drawing
const SKELETON_CONNECTIONS = [
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
]

// Severity color mapping
const SEVERITY_COLORS = {
  low: { bg: 'bg-emerald-500/20', border: 'border-emerald-500/40', text: 'text-emerald-400', dot: 'bg-emerald-500' },
  medium: { bg: 'bg-amber-500/20', border: 'border-amber-500/40', text: 'text-amber-400', dot: 'bg-amber-500' },
  high: { bg: 'bg-rose-500/20', border: 'border-rose-500/40', text: 'text-rose-400', dot: 'bg-rose-500' },
}

// Score ring component
const ScoreRing = ({ score }) => {
  const circumference = 2 * Math.PI * 45
  const offset = circumference - (score / 100) * circumference
  
  const getScoreColor = () => {
    if (score >= 80) return '#10b981'
    if (score >= 60) return '#f59e0b'
    return '#f43f5e'
  }

  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="45"
          fill="none"
          stroke="#1e293b"
          strokeWidth="8"
        />
        <motion.circle
          cx="64"
          cy="64"
          r="45"
          fill="none"
          stroke={getScoreColor()}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span 
          className="text-3xl font-bold text-white"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.5 }}
        >
          {Math.round(score)}
        </motion.span>
        <span className="text-xs text-slate-400">/ 100</span>
      </div>
    </div>
  )
}

// Metric Card component
const MetricCard = ({ metric, index }) => {
  const colors = SEVERITY_COLORS[metric.severity]
  const isPositiveDiff = metric.difference > 0
  
  return (
    <motion.div
      className={`glass-card rounded-xl p-4 border ${colors.border} hover:scale-[1.02] transition-transform duration-200`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 * index }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
          <h4 className="font-medium text-white text-sm">{metric.display_name}</h4>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full ${colors.bg} ${colors.text}`}>
          {metric.severity}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-bold text-white font-mono">
            {metric.user_value}
          </span>
          <span className="text-sm text-slate-500">
            ref: {metric.reference_value} {metric.unit}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <span className={`text-sm font-mono ${isPositiveDiff ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isPositiveDiff ? '+' : ''}{metric.difference.toFixed(1)} {metric.unit}
          </span>
          <span className="text-xs text-slate-500">
            ({Math.abs(metric.difference_percent).toFixed(1)}%)
          </span>
        </div>
      </div>
      
      <p className="mt-3 text-xs text-slate-500 leading-relaxed">
        {metric.description}
      </p>
    </motion.div>
  )
}

// Skeleton overlay canvas component
const SkeletonOverlay = ({ poseData, currentFrame, videoWidth, videoHeight, deviations }) => {
  const canvasRef = useRef(null)
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !poseData?.length) return
    
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    // Find the pose for current frame
    const pose = poseData.find(p => p.frame_number === currentFrame) || poseData[0]
    if (!pose?.keypoints) return
    
    const keypoints = pose.keypoints
    
    // Scale factors
    const scaleX = canvas.width / videoWidth
    const scaleY = canvas.height / videoHeight
    
    // Draw connections
    ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)'
    ctx.lineWidth = 2
    
    SKELETON_CONNECTIONS.forEach(([start, end]) => {
      const startPt = keypoints[start]
      const endPt = keypoints[end]
      
      if (startPt && endPt && startPt.visibility > 0.5 && endPt.visibility > 0.5) {
        ctx.beginPath()
        ctx.moveTo(startPt.x * scaleX, startPt.y * scaleY)
        ctx.lineTo(endPt.x * scaleX, endPt.y * scaleY)
        ctx.stroke()
      }
    })
    
    // Draw keypoints
    Object.entries(keypoints).forEach(([name, point]) => {
      if (point.visibility < 0.5) return
      
      const x = point.x * scaleX
      const y = point.y * scaleY
      
      // Check if this joint has high deviation
      const hasDeviation = deviations?.includes(name)
      
      ctx.beginPath()
      ctx.arc(x, y, hasDeviation ? 6 : 4, 0, Math.PI * 2)
      ctx.fillStyle = hasDeviation ? '#f43f5e' : '#10b981'
      ctx.fill()
      
      if (hasDeviation) {
        ctx.beginPath()
        ctx.arc(x, y, 10, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.5)'
        ctx.lineWidth = 2
        ctx.stroke()
      }
    })
  }, [poseData, currentFrame, videoWidth, videoHeight, deviations])
  
  return (
    <canvas
      ref={canvasRef}
      width={videoWidth || 640}
      height={videoHeight || 360}
      className="absolute inset-0 w-full h-full pointer-events-none"
    />
  )
}

export default function AnalysisPage({ analysisData, videoUrl }) {
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [showSkeleton, setShowSkeleton] = useState(true)
  const [videoDimensions, setVideoDimensions] = useState({ width: 640, height: 360 })
  
  // Redirect if no data
  useEffect(() => {
    if (!analysisData) {
      navigate('/upload')
    }
  }, [analysisData, navigate])
  
  if (!analysisData) return null
  
  const { metrics, technique_similarity_score, shot_segment, pose_data, dominant_hand } = analysisData
  
  // Find joints with high deviation
  const highDeviationJoints = metrics
    ?.filter(m => m.severity === 'high')
    ?.flatMap(m => {
      // Map metric names to joint names
      if (m.name.includes('elbow')) return [`${dominant_hand}_elbow`]
      if (m.name.includes('wrist')) return [`${dominant_hand}_wrist`]
      if (m.name.includes('shoulder')) return ['left_shoulder', 'right_shoulder']
      if (m.name.includes('knee')) return [`${dominant_hand}_knee`]
      if (m.name.includes('hip')) return ['left_hip', 'right_hip']
      return []
    })
  
  const handleVideoLoad = () => {
    if (videoRef.current) {
      setVideoDimensions({
        width: videoRef.current.videoWidth || 640,
        height: videoRef.current.videoHeight || 360,
      })
    }
  }
  
  const handleTimeUpdate = () => {
    if (videoRef.current && shot_segment) {
      const currentTime = videoRef.current.currentTime
      const fps = 30 // Assume 30fps
      const frame = Math.floor(currentTime * fps)
      setCurrentFrame(shot_segment.start_frame + frame)
    }
  }
  
  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }
  
  // Group metrics by category
  const metricCategories = {
    'Rotation & Power': metrics?.filter(m => 
      m.name.includes('shoulder') || m.name.includes('hip_shoulder_separation')
    ),
    'Arm Mechanics': metrics?.filter(m => 
      m.name.includes('elbow') || m.name.includes('wrist')
    ),
    'Lower Body': metrics?.filter(m => 
      m.name.includes('knee') || m.name.includes('com')
    ),
    'Timing': metrics?.filter(m => 
      m.name.includes('delay') || m.name.includes('duration')
    ),
  }
  
  return (
    <div className="min-h-screen px-6 py-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8">
        <nav className="flex items-center justify-between">
          <Link to="/upload" className="flex items-center gap-2 text-emerald-400 hover:text-emerald-300 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span className="font-medium">New Analysis</span>
          </Link>
          <h1 className="font-display font-bold text-xl text-white">Analysis Results</h1>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="capitalize">{dominant_hand}-handed</span>
          </div>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left column - Video and Score */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video Player with Skeleton Overlay */}
            <motion.div
              className="glass-card rounded-2xl overflow-hidden"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="relative aspect-video bg-slate-900">
                <video
                  ref={videoRef}
                  src={videoUrl}
                  className="w-full h-full object-contain"
                  onLoadedMetadata={handleVideoLoad}
                  onTimeUpdate={handleTimeUpdate}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  loop
                />
                
                {showSkeleton && pose_data?.length > 0 && (
                  <SkeletonOverlay
                    poseData={pose_data}
                    currentFrame={currentFrame}
                    videoWidth={videoDimensions.width}
                    videoHeight={videoDimensions.height}
                    deviations={highDeviationJoints}
                  />
                )}
                
                {/* Video controls overlay */}
                <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-900/90 to-transparent">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handlePlayPause}
                      className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
                    >
                      {isPlaying ? (
                        <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                        </svg>
                      ) : (
                        <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8 5v14l11-7z"/>
                        </svg>
                      )}
                    </button>
                    
                    <button
                      onClick={() => setShowSkeleton(!showSkeleton)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        showSkeleton 
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' 
                          : 'bg-slate-700/50 text-slate-400'
                      }`}
                    >
                      {showSkeleton ? 'Hide' : 'Show'} Skeleton
                    </button>
                    
                    {shot_segment && (
                      <div className="ml-auto text-sm text-slate-400 font-mono">
                        Duration: {shot_segment.duration_ms.toFixed(0)}ms
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Score Card */}
            <motion.div
              className="glass-card rounded-2xl p-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center gap-8">
                <ScoreRing score={technique_similarity_score} />
                
                <div className="flex-1">
                  <h2 className="text-2xl font-display font-bold text-white mb-2">
                    Technique Similarity Score
                  </h2>
                  <p className="text-slate-400 mb-4">
                    {technique_similarity_score >= 80 
                      ? 'Excellent technique! Your biomechanics closely match elite player patterns.'
                      : technique_similarity_score >= 60
                      ? 'Good foundation with room for improvement. Focus on the highlighted areas.'
                      : 'Several areas need attention. Review each metric for targeted improvements.'}
                  </p>
                  
                  <div className="flex gap-4">
                    <div className="flex items-center gap-2 text-sm">
                      <div className="w-3 h-3 rounded-full bg-emerald-500" />
                      <span className="text-slate-400">Low deviation</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <div className="w-3 h-3 rounded-full bg-amber-500" />
                      <span className="text-slate-400">Medium</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <div className="w-3 h-3 rounded-full bg-rose-500" />
                      <span className="text-slate-400">High</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right column - Metrics */}
          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="sticky top-6"
            >
              <h2 className="font-display font-bold text-lg text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Biomechanics Breakdown
              </h2>
              
              <div className="max-h-[calc(100vh-180px)] overflow-y-auto space-y-6 pr-2">
                {Object.entries(metricCategories).map(([category, categoryMetrics]) => (
                  categoryMetrics?.length > 0 && (
                    <div key={category}>
                      <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">
                        {category}
                      </h3>
                      <div className="space-y-3">
                        {categoryMetrics.map((metric, idx) => (
                          <MetricCard key={metric.name} metric={metric} index={idx} />
                        ))}
                      </div>
                    </div>
                  )
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  )
}

