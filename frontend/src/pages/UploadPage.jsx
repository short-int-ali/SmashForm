import { useState, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'

const API_BASE = '/api'

// Camera placement guide component
const RecordingGuide = () => (
  <div className="glass-card rounded-2xl p-6 space-y-4">
    <h3 className="font-display font-semibold text-white flex items-center gap-2">
      <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
      Recording Guidelines
    </h3>
    <ul className="space-y-3 text-sm text-gray-400">
      <li className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">1</span>
        <span><strong className="text-gray-200">Side View:</strong> Place camera perpendicular to the court, opposite your dominant hand</span>
      </li>
      <li className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">2</span>
        <span><strong className="text-gray-200">Full Body:</strong> Ensure your entire body is visible throughout the swing</span>
      </li>
      <li className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">3</span>
        <span><strong className="text-gray-200">Stable Setup:</strong> Use a tripod or stable surface, avoid shaky footage</span>
      </li>
      <li className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">4</span>
        <span><strong className="text-gray-200">Good Lighting:</strong> Well-lit environment helps pose detection accuracy</span>
      </li>
    </ul>
    
    {/* Visual camera placement diagram */}
    <div className="mt-4 p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
      <div className="relative h-32 flex items-center justify-center">
        {/* Court representation */}
        <div className="w-48 h-20 border-2 border-dashed border-slate-600 rounded-lg flex items-center justify-center">
          <span className="text-xs text-slate-500">COURT</span>
        </div>
        {/* Player */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="w-4 h-8 bg-emerald-500/60 rounded-full" />
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-emerald-400 whitespace-nowrap">Player</span>
        </div>
        {/* Camera for right-handed */}
        <div className="absolute -right-2 top-1/2 -translate-y-1/2">
          <svg className="w-8 h-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-cyan-400 whitespace-nowrap">Camera</span>
        </div>
        {/* Arrow showing camera direction */}
        <div className="absolute right-12 top-1/2 -translate-y-1/2">
          <svg className="w-6 h-6 text-cyan-400/50 rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </div>
      </div>
      <p className="text-center text-xs text-slate-500 mt-4">
        For right-handed players: camera on left side
      </p>
    </div>
  </div>
)

export default function UploadPage({ setAnalysisData, setVideoUrl }) {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [dominantHand, setDominantHand] = useState('right')
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState(0)

  const onDrop = useCallback((acceptedFiles) => {
    const videoFile = acceptedFiles[0]
    if (videoFile) {
      setFile(videoFile)
      setPreview(URL.createObjectURL(videoFile))
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/mp4': ['.mp4'],
      'video/quicktime': ['.mov'],
      'video/x-msvideo': ['.avi'],
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100MB
  })

  const handleAnalyze = async () => {
    if (!file) return

    setError(null)
    setUploading(true)
    setProgress(10)

    try {
      // Step 1: Upload video
      const formData = new FormData()
      formData.append('video', file)

      const uploadRes = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          const pct = Math.round((e.loaded / e.total) * 40)
          setProgress(10 + pct)
        },
      })

      if (!uploadRes.data.success) {
        throw new Error(uploadRes.data.message || 'Upload failed')
      }

      const videoId = uploadRes.data.video_id
      setProgress(50)
      setUploading(false)
      setAnalyzing(true)

      // Step 2: Analyze video
      const analyzeForm = new FormData()
      analyzeForm.append('video_id', videoId)
      analyzeForm.append('dominant_hand', dominantHand)

      const analyzeRes = await axios.post(`${API_BASE}/analyze`, analyzeForm)
      
      setProgress(100)

      if (!analyzeRes.data.success) {
        throw new Error(analyzeRes.data.message || 'Analysis failed')
      }

      // Store results and navigate
      setAnalysisData(analyzeRes.data)
      setVideoUrl(preview)
      navigate('/analysis')

    } catch (err) {
      console.error('Analysis error:', err)
      setError(err.response?.data?.detail || err.message || 'Analysis failed')
      setUploading(false)
      setAnalyzing(false)
      setProgress(0)
    }
  }

  const removeFile = () => {
    setFile(null)
    if (preview) {
      URL.revokeObjectURL(preview)
      setPreview(null)
    }
    setError(null)
    setProgress(0)
  }

  return (
    <div className="min-h-screen px-6 py-8">
      {/* Header */}
      <header className="max-w-5xl mx-auto mb-12">
        <nav className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-emerald-400 hover:text-emerald-300 transition-colors">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span className="font-display font-semibold">SmashForm</span>
          </Link>
          <h1 className="font-display font-bold text-xl text-white">Upload Video</h1>
          <div className="w-24" /> {/* Spacer for centering */}
        </nav>
      </header>

      <main className="max-w-5xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left column - Upload zone */}
          <div className="space-y-6">
            {/* Dropzone */}
            <motion.div
              className={`
                relative rounded-2xl border-2 border-dashed transition-all duration-300 overflow-hidden
                ${isDragActive ? 'border-emerald-400 bg-emerald-500/10' : 'border-slate-600 hover:border-slate-500'}
                ${file ? 'border-solid border-emerald-500/50' : ''}
              `}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {!file ? (
                <div
                  {...getRootProps()}
                  className="p-12 text-center cursor-pointer"
                >
                  <input {...getInputProps()} />
                  <div className="flex flex-col items-center gap-4">
                    <div className={`
                      w-16 h-16 rounded-2xl flex items-center justify-center transition-colors
                      ${isDragActive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}
                    `}>
                      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-white font-medium mb-1">
                        {isDragActive ? 'Drop your video here' : 'Drag & drop your video'}
                      </p>
                      <p className="text-sm text-slate-400">
                        or click to browse • MP4, MOV, AVI up to 100MB
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="relative">
                  <video
                    src={preview}
                    className="w-full aspect-video object-cover"
                    controls
                  />
                  <button
                    onClick={removeFile}
                    className="absolute top-3 right-3 w-8 h-8 rounded-full bg-slate-900/80 text-white hover:bg-rose-500 transition-colors flex items-center justify-center"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                  <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-slate-900/90 to-transparent">
                    <p className="text-sm text-white font-medium truncate">{file.name}</p>
                    <p className="text-xs text-slate-400">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Dominant Hand Toggle */}
            <motion.div
              className="glass-card rounded-2xl p-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <label className="block text-sm font-medium text-gray-300 mb-4">
                Dominant Hand
              </label>
              <div className="flex gap-3">
                {['left', 'right'].map((hand) => (
                  <button
                    key={hand}
                    onClick={() => setDominantHand(hand)}
                    className={`
                      flex-1 py-3 px-4 rounded-xl font-medium transition-all duration-200
                      ${dominantHand === hand 
                        ? 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/20' 
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}
                    `}
                  >
                    {hand === 'left' ? '🫲' : '🫱'} {hand.charAt(0).toUpperCase() + hand.slice(1)}
                  </button>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Camera should be placed on the opposite side of your dominant hand
              </p>
            </motion.div>

            {/* Error message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm"
                >
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>{error}</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Analyze Button */}
            <motion.button
              onClick={handleAnalyze}
              disabled={!file || uploading || analyzing}
              className={`
                w-full py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300
                flex items-center justify-center gap-3
                ${file && !uploading && !analyzing
                  ? 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed'}
              `}
              whileHover={file && !uploading && !analyzing ? { scale: 1.01 } : {}}
              whileTap={file && !uploading && !analyzing ? { scale: 0.99 } : {}}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {uploading || analyzing ? (
                <>
                  <div className="w-5 h-5 spinner" />
                  <span>{uploading ? 'Uploading...' : 'Analyzing biomechanics...'}</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                  <span>Analyze Technique</span>
                </>
              )}
            </motion.button>

            {/* Progress bar */}
            <AnimatePresence>
              {(uploading || analyzing) && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2"
                >
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 text-center">
                    {progress < 50 ? 'Uploading video...' : 'Running pose detection and biomechanics analysis...'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right column - Guide */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <RecordingGuide />
          </motion.div>
        </div>
      </main>
    </div>
  )
}

