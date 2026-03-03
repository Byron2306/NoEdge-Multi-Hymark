import React, { useState, useEffect, useCallback } from 'react';
import {
  Upload,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Download,
  ChevronRight,
  BookOpen,
  Zap,
  RefreshCw,
  X,
  FileArchive,
  Target,
  Award,
  TrendingUp,
  Eye
} from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// API helper
const api = {
  async get(endpoint) {
    const res = await fetch(`${API_URL}${endpoint}`);
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
  },
  async post(endpoint, data, isFormData = false) {
    const options = {
      method: 'POST',
      body: isFormData ? data : JSON.stringify(data),
    };
    if (!isFormData) {
      options.headers = { 'Content-Type': 'application/json' };
    }
    const res = await fetch(`${API_URL}${endpoint}`, options);
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
  }
};

// Toast notification component
function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const icons = {
    success: <CheckCircle size={18} />,
    error: <AlertCircle size={18} />,
    info: <Clock size={18} />
  };

  return (
    <div className={`toast toast-${type}`} data-testid="toast-notification">
      {icons[type]}
      <span>{message}</span>
      <button onClick={onClose} className="toast-close">
        <X size={16} />
      </button>
    </div>
  );
}

// File upload dropzone
function FileDropzone({ onFileSelect, accept, label, icon: Icon }) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setSelectedFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      onFileSelect(file);
    }
  };

  return (
    <div
      className={`dropzone ${isDragging ? 'dropzone-active' : ''} ${selectedFile ? 'dropzone-selected' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      data-testid="file-dropzone"
    >
      <input
        type="file"
        accept={accept}
        onChange={handleFileInput}
        className="dropzone-input"
        data-testid="file-input"
      />
      <Icon size={32} className="dropzone-icon" />
      {selectedFile ? (
        <div className="dropzone-selected-info">
          <span className="selected-filename">{selectedFile.name}</span>
          <span className="selected-size">{(selectedFile.size / 1024).toFixed(1)} KB</span>
        </div>
      ) : (
        <>
          <span className="dropzone-label">{label}</span>
          <span className="dropzone-hint">Drop file or click to browse</span>
        </>
      )}
    </div>
  );
}

// Rubric display card
function RubricCard({ rubric, isSelected, onSelect }) {
  return (
    <div 
      className={`rubric-card ${isSelected ? 'rubric-card-selected' : ''}`}
      onClick={() => onSelect(rubric)}
      data-testid={`rubric-card-${rubric._id}`}
    >
      <div className="rubric-card-header">
        <BookOpen size={20} />
        <span className="rubric-name">{rubric.name}</span>
      </div>
      <div className="rubric-card-body">
        <div className="rubric-stat">
          <Target size={14} />
          <span>{rubric.total_marks} marks</span>
        </div>
        <div className="rubric-stat">
          <FileText size={14} />
          <span>{rubric.criteria?.length || 0} criteria</span>
        </div>
      </div>
      {isSelected && (
        <div className="rubric-selected-badge">
          <CheckCircle size={16} />
          Selected
        </div>
      )}
    </div>
  );
}

// Assessment result card
function AssessmentResultCard({ assessment, onViewDetails }) {
  const getScoreColor = (percentage) => {
    if (percentage >= 75) return 'score-excellent';
    if (percentage >= 60) return 'score-good';
    if (percentage >= 50) return 'score-satisfactory';
    return 'score-needs-work';
  };

  return (
    <div className="assessment-card" data-testid={`assessment-${assessment.student_id}`}>
      <div className="assessment-header">
        <div className="student-info">
          <span className="student-id">{assessment.student_id || 'Unknown'}</span>
          <span className="submission-file">{assessment.submission_file}</span>
        </div>
        <div className={`score-badge ${getScoreColor(assessment.percentage)}`}>
          <Award size={16} />
          {assessment.total_score?.toFixed(1)} / {assessment.max_score || 100}
        </div>
      </div>
      <div className="assessment-body">
        <div className="percentage-bar">
          <div 
            className={`percentage-fill ${getScoreColor(assessment.percentage)}`}
            style={{ width: `${Math.min(assessment.percentage, 100)}%` }}
          />
          <span className="percentage-text">{assessment.percentage?.toFixed(1)}%</span>
        </div>
        {assessment.strengths?.length > 0 && (
          <div className="feedback-preview">
            <strong>Strengths:</strong> {assessment.strengths[0]}
          </div>
        )}
      </div>
      <button 
        className="view-details-btn"
        onClick={() => onViewDetails(assessment)}
        data-testid={`view-details-${assessment.student_id}`}
      >
        <Eye size={16} />
        View Details
      </button>
    </div>
  );
}

// Assessment details modal
function AssessmentDetailsModal({ assessment, onClose }) {
  if (!assessment) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="assessment-details-modal">
        <button className="modal-close" onClick={onClose}>
          <X size={24} />
        </button>
        
        <div className="modal-header">
          <h2>Assessment Details</h2>
          <div className="modal-student-info">
            <span>Student: {assessment.student_id}</span>
            <span>File: {assessment.submission_file}</span>
          </div>
        </div>

        <div className="modal-score-section">
          <div className="big-score">
            <span className="score-value">{assessment.total_score?.toFixed(1)}</span>
            <span className="score-max">/ {assessment.max_score || 100}</span>
          </div>
          <div className="score-percentage">
            {assessment.percentage?.toFixed(1)}%
          </div>
        </div>

        <div className="modal-section">
          <h3>Overall Feedback</h3>
          <p className="overall-feedback">{assessment.overall_feedback}</p>
        </div>

        {assessment.strengths?.length > 0 && (
          <div className="modal-section">
            <h3><TrendingUp size={18} /> Strengths</h3>
            <ul className="feedback-list strengths">
              {assessment.strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}

        {assessment.areas_for_improvement?.length > 0 && (
          <div className="modal-section">
            <h3><Target size={18} /> Areas for Improvement</h3>
            <ul className="feedback-list improvements">
              {assessment.areas_for_improvement.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        )}

        {assessment.criteria_scores && Object.keys(assessment.criteria_scores).length > 0 && (
          <div className="modal-section">
            <h3>Criteria Breakdown</h3>
            <div className="criteria-breakdown">
              {Object.entries(assessment.criteria_scores).map(([name, data]) => (
                <div key={name} className="criterion-score">
                  <div className="criterion-header">
                    <span className="criterion-name">{name}</span>
                    <span className="criterion-value">{data.score?.toFixed(1)} ({data.level})</span>
                  </div>
                  <p className="criterion-feedback">{data.feedback}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {assessment.annotations?.length > 0 && (
          <div className="modal-section">
            <h3>Annotations</h3>
            <div className="annotations-list">
              {assessment.annotations.map((ann, i) => (
                <div key={i} className={`annotation annotation-${ann.type}`}>
                  <span className="annotation-type">{ann.type}</span>
                  <p className="annotation-comment">{ann.comment}</p>
                  {ann.quote && (
                    <blockquote className="annotation-quote">"{ann.quote}"</blockquote>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Job status card
function JobCard({ job, onDownload }) {
  const statusIcons = {
    processing: <RefreshCw size={18} className="spin" />,
    completed: <CheckCircle size={18} />,
    failed: <AlertCircle size={18} />
  };

  return (
    <div className={`job-card job-${job.status}`} data-testid={`job-${job.job_id}`}>
      <div className="job-header">
        {statusIcons[job.status]}
        <span className="job-id">{job.job_id}</span>
        <span className={`job-status status-${job.status}`}>{job.status}</span>
      </div>
      <div className="job-body">
        <span className="job-rubric">Rubric: {job.rubric_name}</span>
        <span className="job-file">File: {job.zip_file}</span>
        {job.results && (
          <span className="job-count">{job.results.submissions_processed} submissions</span>
        )}
      </div>
      {job.status === 'completed' && (
        <button 
          className="download-btn"
          onClick={() => onDownload(job.job_id)}
          data-testid={`download-${job.job_id}`}
        >
          <Download size={16} />
          Download Results
        </button>
      )}
    </div>
  );
}

// Main App
function App() {
  const [activeTab, setActiveTab] = useState('assess');
  const [rubrics, setRubrics] = useState([]);
  const [selectedRubric, setSelectedRubric] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [recentAssessments, setRecentAssessments] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAssessment, setSelectedAssessment] = useState(null);

  // Toast helpers
  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // Load data
  const loadRubrics = useCallback(async () => {
    try {
      const data = await api.get('/api/rubrics');
      setRubrics(data.rubrics || []);
    } catch (error) {
      console.error('Failed to load rubrics:', error);
    }
  }, []);

  const loadJobs = useCallback(async () => {
    try {
      const data = await api.get('/api/jobs');
      setJobs(data.jobs || []);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    }
  }, []);

  const loadAssessments = useCallback(async () => {
    try {
      const data = await api.get('/api/assessments');
      setRecentAssessments(data.assessments || []);
    } catch (error) {
      console.error('Failed to load assessments:', error);
    }
  }, []);

  useEffect(() => {
    loadRubrics();
    loadJobs();
    loadAssessments();
    
    // Poll jobs every 5 seconds
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [loadRubrics, loadJobs, loadAssessments]);

  // Upload rubric
  const handleRubricUpload = async (file) => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace(/\.[^.]+$/, ''));
      
      const result = await api.post('/api/rubric/upload', formData, true);
      showToast(`Rubric "${result.rubric.name}" uploaded successfully!`, 'success');
      loadRubrics();
    } catch (error) {
      showToast(`Failed to upload rubric: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Single assessment
  const handleSingleAssessment = async (file) => {
    if (!selectedRubric) {
      showToast('Please select a rubric first', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('rubric_id', selectedRubric._id);
      
      const result = await api.post('/api/assess/single', formData, true);
      showToast(`Assessment complete! Score: ${result.total_score?.toFixed(1)}/${result.max_score}`, 'success');
      setSelectedAssessment(result);
      loadAssessments();
    } catch (error) {
      showToast(`Assessment failed: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Bulk assessment
  const handleBulkAssessment = async (file) => {
    if (!selectedRubric) {
      showToast('Please select a rubric first', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('rubric_id', selectedRubric._id);
      
      const result = await api.post('/api/assess/bulk', formData, true);
      showToast(`Bulk assessment started! Job ID: ${result.job_id}`, 'success');
      loadJobs();
    } catch (error) {
      showToast(`Failed to start assessment: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Download results
  const handleDownload = (jobId) => {
    window.open(`${API_URL}/api/download/${jobId}`, '_blank');
  };

  // View assessment details
  const handleViewDetails = async (assessment) => {
    try {
      if (assessment._id) {
        const detailed = await api.get(`/api/assessment/${assessment._id}`);
        setSelectedAssessment(detailed);
      } else {
        setSelectedAssessment(assessment);
      }
    } catch (error) {
      setSelectedAssessment(assessment);
    }
  };

  return (
    <div className="app" data-testid="smart-assessor-app">
      {/* Toast container */}
      <div className="toast-container">
        {toasts.map(toast => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>

      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <Zap size={28} className="logo-icon" />
            <span className="logo-text">Smart Assessor</span>
          </div>
          <p className="tagline">AI-Powered Assignment Grading</p>
        </div>
      </header>

      {/* Navigation */}
      <nav className="nav">
        <button 
          className={`nav-btn ${activeTab === 'assess' ? 'nav-btn-active' : ''}`}
          onClick={() => setActiveTab('assess')}
          data-testid="nav-assess"
        >
          <FileText size={18} />
          Assess
        </button>
        <button 
          className={`nav-btn ${activeTab === 'rubrics' ? 'nav-btn-active' : ''}`}
          onClick={() => setActiveTab('rubrics')}
          data-testid="nav-rubrics"
        >
          <BookOpen size={18} />
          Rubrics
        </button>
        <button 
          className={`nav-btn ${activeTab === 'jobs' ? 'nav-btn-active' : ''}`}
          onClick={() => setActiveTab('jobs')}
          data-testid="nav-jobs"
        >
          <Clock size={18} />
          Jobs
        </button>
      </nav>

      {/* Main content */}
      <main className="main">
        {/* Assess Tab */}
        {activeTab === 'assess' && (
          <div className="tab-content" data-testid="assess-tab">
            <section className="section">
              <h2 className="section-title">
                <Target size={22} />
                Select Rubric
              </h2>
              {rubrics.length === 0 ? (
                <div className="empty-state">
                  <BookOpen size={48} />
                  <p>No rubrics available. Upload one in the Rubrics tab.</p>
                </div>
              ) : (
                <div className="rubrics-grid">
                  {rubrics.map(rubric => (
                    <RubricCard
                      key={rubric._id}
                      rubric={rubric}
                      isSelected={selectedRubric?._id === rubric._id}
                      onSelect={setSelectedRubric}
                    />
                  ))}
                </div>
              )}
            </section>

            <section className="section">
              <h2 className="section-title">
                <Upload size={22} />
                Upload Submission
              </h2>
              <div className="upload-options">
                <div className="upload-option">
                  <h3>Single Submission</h3>
                  <FileDropzone
                    onFileSelect={handleSingleAssessment}
                    accept=".docx,.pdf,.doc"
                    label="Upload Essay (DOCX/PDF)"
                    icon={FileText}
                  />
                </div>
                <div className="upload-option">
                  <h3>Bulk Assessment (eFundi ZIP)</h3>
                  <FileDropzone
                    onFileSelect={handleBulkAssessment}
                    accept=".zip"
                    label="Upload eFundi ZIP"
                    icon={FileArchive}
                  />
                </div>
              </div>
            </section>

            {recentAssessments.length > 0 && (
              <section className="section">
                <h2 className="section-title">
                  <Award size={22} />
                  Recent Assessments
                </h2>
                <div className="assessments-grid">
                  {recentAssessments.slice(0, 6).map(assessment => (
                    <AssessmentResultCard
                      key={assessment._id}
                      assessment={assessment}
                      onViewDetails={handleViewDetails}
                    />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        {/* Rubrics Tab */}
        {activeTab === 'rubrics' && (
          <div className="tab-content" data-testid="rubrics-tab">
            <section className="section">
              <h2 className="section-title">
                <Upload size={22} />
                Upload New Rubric
              </h2>
              <FileDropzone
                onFileSelect={handleRubricUpload}
                accept=".docx,.pdf,.doc"
                label="Upload Rubric (DOCX/PDF)"
                icon={BookOpen}
              />
            </section>

            <section className="section">
              <h2 className="section-title">
                <BookOpen size={22} />
                Available Rubrics
              </h2>
              {rubrics.length === 0 ? (
                <div className="empty-state">
                  <BookOpen size={48} />
                  <p>No rubrics uploaded yet.</p>
                </div>
              ) : (
                <div className="rubrics-list">
                  {rubrics.map(rubric => (
                    <div key={rubric._id} className="rubric-detail-card" data-testid={`rubric-detail-${rubric._id}`}>
                      <div className="rubric-detail-header">
                        <BookOpen size={24} />
                        <div>
                          <h3>{rubric.name}</h3>
                          <span className="rubric-meta">
                            {rubric.total_marks} total marks | {rubric.criteria?.length || 0} criteria
                          </span>
                        </div>
                      </div>
                      {rubric.criteria?.length > 0 && (
                        <div className="criteria-list">
                          <h4>Criteria:</h4>
                          <ul>
                            {rubric.criteria.map((c, i) => (
                              <li key={i}>
                                <ChevronRight size={14} />
                                <span className="criterion-name">{c.name}</span>
                                <span className="criterion-weight">({c.weight} marks)</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {/* Jobs Tab */}
        {activeTab === 'jobs' && (
          <div className="tab-content" data-testid="jobs-tab">
            <section className="section">
              <div className="section-header">
                <h2 className="section-title">
                  <Clock size={22} />
                  Assessment Jobs
                </h2>
                <button className="refresh-btn" onClick={loadJobs} data-testid="refresh-jobs">
                  <RefreshCw size={18} />
                  Refresh
                </button>
              </div>
              {jobs.length === 0 ? (
                <div className="empty-state">
                  <Clock size={48} />
                  <p>No assessment jobs yet. Start a bulk assessment to see jobs here.</p>
                </div>
              ) : (
                <div className="jobs-list">
                  {jobs.map(job => (
                    <JobCard
                      key={job.job_id}
                      job={job}
                      onDownload={handleDownload}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>

      {/* Loading overlay */}
      {isLoading && (
        <div className="loading-overlay" data-testid="loading-overlay">
          <div className="loading-spinner">
            <RefreshCw size={48} className="spin" />
            <span>Processing...</span>
          </div>
        </div>
      )}

      {/* Assessment details modal */}
      {selectedAssessment && (
        <AssessmentDetailsModal
          assessment={selectedAssessment}
          onClose={() => setSelectedAssessment(null)}
        />
      )}
    </div>
  );
}

export default App;
