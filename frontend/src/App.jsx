import { Routes, Route } from 'react-router-dom'
import { useState } from 'react'
import LandingPage from './pages/LandingPage'
import UploadPage from './pages/UploadPage'
import AnalysisPage from './pages/AnalysisPage'

function App() {
  // Shared state for analysis data
  const [analysisData, setAnalysisData] = useState(null)
  const [videoUrl, setVideoUrl] = useState(null)

  return (
    <div className="min-h-screen gradient-bg">
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route 
          path="/upload" 
          element={
            <UploadPage 
              setAnalysisData={setAnalysisData} 
              setVideoUrl={setVideoUrl}
            />
          } 
        />
        <Route 
          path="/analysis" 
          element={
            <AnalysisPage 
              analysisData={analysisData} 
              videoUrl={videoUrl}
            />
          } 
        />
      </Routes>
    </div>
  )
}

export default App

