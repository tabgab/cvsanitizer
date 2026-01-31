import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import './styles.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const App = () => {
  const [pdfFile, setPdfFile] = useState(null);
  const [piiData, setPiiData] = useState([]);
  const [selectedPii, setSelectedPii] = useState([]);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [showAddPiiModal, setShowAddPiiModal] = useState(false);
  const [newPii, setNewPii] = useState({ type: '', text: '', notes: '' });
  const [agreementVerified, setAgreementVerified] = useState(false);
  const [pdfTextContent, setPdfTextContent] = useState('');
  
  const canvasRef = useRef(null);

  // Load data from URL parameters or localStorage
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const pdfUrl = urlParams.get('pdf');
    const piiUrl = urlParams.get('pii');
    
    if (pdfUrl && piiUrl) {
      loadPdfAndPiiData(pdfUrl, piiUrl);
    } else {
      // Try to load from localStorage for development
      const storedPdf = localStorage.getItem('pdfFile');
      const storedPii = localStorage.getItem('piiData');
      
      if (storedPdf && storedPii) {
        loadPdfAndPiiData(storedPdf, JSON.parse(storedPii));
      } else {
        setError('No PDF or PII data provided. Please provide PDF and PII data as URL parameters.');
        setLoading(false);
      }
    }
  }, []);

  const loadPdfAndPiiData = async (pdfUrl, piiDataOrUrl) => {
    try {
      setLoading(true);
      
      // Load PDF
      const pdfResponse = await fetch(pdfUrl);
      const pdfBlob = await pdfResponse.blob();
      const pdfObjectUrl = URL.createObjectURL(pdfBlob);
      setPdfFile(pdfObjectUrl);
      
      // Load PII data
      let piiData;
      if (typeof piiDataOrUrl === 'string') {
        const piiResponse = await fetch(piiDataOrUrl);
        piiData = await piiResponse.json();
      } else {
        piiData = piiDataOrUrl;
      }
      
      // Convert PII data to array format
      const piiArray = Object.entries(piiData).map(([placeholder, data]) => ({
        id: placeholder,
        type: data.category,
        text: data.original,
        confidence: data.confidence,
        position: data.position,
        metadata: data.metadata,
        approved: false,
        removed: false,
        userAdded: false
      }));
      
      setPiiData(piiArray);
      setLoading(false);
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load PDF or PII data. Please check the file paths.');
      setLoading(false);
    }
  };

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const onDocumentLoadError = (error) => {
    console.error('Error loading PDF:', error);
    setError('Failed to load PDF document. Please check the file.');
    setLoading(false);
  };

  const togglePiiSelection = (piiId) => {
    setSelectedPii(prev => 
      prev.includes(piiId) 
        ? prev.filter(id => id !== piiId)
        : [...prev, piiId]
    );
  };

  const approveSelected = () => {
    setPiiData(prev => prev.map(pii => 
      selectedPii.includes(pii.id) ? { ...pii, approved: true } : pii
    ));
    setSelectedPii([]);
  };

  const removeSelected = () => {
    setPiiData(prev => prev.map(pii => 
      selectedPii.includes(pii.id) ? { ...pii, removed: true } : pii
    ));
    setSelectedPii([]);
  };

  const selectAll = () => {
    const activePii = piiData.filter(pii => !pii.removed);
    setSelectedPii(activePii.map(pii => pii.id));
  };

  const deselectAll = () => {
    setSelectedPii([]);
  };

  const approveAll = () => {
    setShowApprovalModal(true);
  };

  const agreeToProcessing = () => {
    // Approve all remaining PII
    setPiiData(prev => prev.map(pii => 
      !pii.removed ? { ...pii, approved: true } : pii
    ));
    setAgreementVerified(true);
    setShowApprovalModal(false);
    
    // Export results
    exportResults();
  };

  const rejectProcessing = () => {
    setShowApprovalModal(false);
    alert('Process rejected. No data will be processed.');
  };

  const addNewPii = () => {
    setNewPii({ type: 'email', text: '', notes: '' });
    setShowAddPiiModal(true);
  };

  const saveNewPii = () => {
    if (newPii.text.trim()) {
      const newPiiItem = {
        id: `<pii type="${newPii.type}" serial="${Date.now()}">`,
        type: newPii.type,
        text: newPii.text,
        confidence: 1.0,
        position: { start: 0, end: newPii.text.length },
        metadata: { notes: newPii.notes, userAdded: true },
        approved: false,
        removed: false,
        userAdded: true
      };
      
      setPiiData(prev => [...prev, newPiiItem]);
      setShowAddPiiModal(false);
      setNewPii({ type: 'email', text: '', notes: '' });
    }
  };

  const exportResults = () => {
    const approvedPii = piiData.filter(pii => pii.approved && !pii.removed);
    const results = {
      agreementVerified: agreementVerified,
      timestamp: new Date().toISOString(),
      totalPii: piiData.length,
      approvedPii: approvedPii.length,
      rejectedPii: piiData.filter(pii => pii.removed).length,
      pendingPii: piiData.filter(pii => !pii.approved && !pii.removed).length,
      piiData: piiData.reduce((acc, pii) => {
        if (!pii.removed) {
          acc[pii.id] = {
            original: pii.text,
            category: pii.type,
            position: pii.position,
            confidence: pii.confidence,
            metadata: pii.metadata,
            approved: pii.approved,
            userAdded: pii.userAdded
          };
        }
        return acc;
      }, {})
    };
    
    // Create download link
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pii_review_results.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStats = () => {
    const total = piiData.length;
    const approved = piiData.filter(pii => pii.approved && !pii.removed).length;
    const rejected = piiData.filter(pii => pii.removed).length;
    const pending = piiData.filter(pii => !pii.approved && !pii.removed).length;
    
    return { total, approved, rejected, pending };
  };

  const stats = getStats();

  if (loading) {
    return (
      <div className="container">
        <div className="header">
          <h1>CV Sanitizer - PII Review Interface</h1>
        </div>
        <div className="loading">
          Loading PDF and PII data...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="header">
          <h1>CV Sanitizer - PII Review Interface</h1>
        </div>
        <div className="error">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <h1>CV Sanitizer - PII Review Interface</h1>
      </div>
      
      <div className="content">
        <div className="pdf-container">
          <div className="pdf-controls">
            <button onClick={() => setPageNumber(prev => Math.max(1, prev - 1))} disabled={pageNumber <= 1}>
              Previous
            </button>
            <span>Page {pageNumber} of {numPages}</span>
            <button onClick={() => setPageNumber(prev => Math.min(numPages, prev + 1))} disabled={pageNumber >= numPages}>
              Next
            </button>
            <button onClick={() => setScale(prev => Math.min(2.0, prev + 0.1))}>
              Zoom In
            </button>
            <button onClick={() => setScale(prev => Math.max(0.5, prev - 0.1))}>
              Zoom Out
            </button>
          </div>
          
          <Document
            file={pdfFile}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
          >
            <Page 
              pageNumber={pageNumber} 
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </Document>
          
          {/* PII Overlay */}
          <div className="pdf-overlay">
            {piiData.filter(pii => !pii.removed).map(pii => (
              <div
                key={pii.id}
                className={`pii-box ${selectedPii.includes(pii.id) ? 'selected' : ''}`}
                onClick={() => togglePiiSelection(pii.id)}
                title={`${pii.type}: ${pii.text} (Confidence: ${(pii.confidence * 100).toFixed(1)}%)`}
              />
            ))}
          </div>
        </div>
        
        <div className="controls">
          <div className="stats">
            <h4>PII Detection Summary</h4>
            <div className="stat-item">
              <span>Total PII Found:</span>
              <span className="stat-value">{stats.total}</span>
            </div>
            <div className="stat-item">
              <span>Approved:</span>
              <span className="stat-value">{stats.approved}</span>
            </div>
            <div className="stat-item">
              <span>Rejected:</span>
              <span className="stat-value">{stats.rejected}</span>
            </div>
            <div className="stat-item">
              <span>Pending:</span>
              <span className="stat-value">{stats.pending}</span>
            </div>
          </div>
          
          <div>
            <h4>PII Items</h4>
            {piiData.map(pii => (
              <div
                key={pii.id}
                className={`pii-item ${selectedPii.includes(pii.id) ? 'selected' : ''} ${pii.removed ? 'removed' : ''}`}
                onClick={() => !pii.removed && togglePiiSelection(pii.id)}
              >
                <div className="pii-type">{pii.type}</div>
                <div className="pii-text">{pii.text}</div>
                <div className="pii-confidence">
                  Confidence: {(pii.confidence * 100).toFixed(1)}%
                  {pii.userAdded && ' (User Added)'}
                </div>
                {pii.approved && <div className="success">✓ Approved</div>}
              </div>
            ))}
          </div>
          
          <div className="control-buttons">
            <button onClick={selectAll}>Select All</button>
            <button onClick={deselectAll}>Deselect All</button>
            <button onClick={removeSelected} disabled={selectedPii.length === 0}>
              Remove Selected
            </button>
            <button onClick={approveSelected} disabled={selectedPii.length === 0}>
              Approve Selected
            </button>
            <button onClick={approveAll} className="btn-success">
              Approve All
            </button>
          </div>
          
          <div className="control-buttons">
            <button onClick={addNewPii}>Add New PII</button>
            <button onClick={exportResults}>Export Results</button>
          </div>
        </div>
      </div>
      
      {/* Approval Modal */}
      {showApprovalModal && (
        <div className="modal">
          <div className="modal-content">
            <h3>LLM Processing Consent</h3>
            <p>
              I have reviewed what personal information will be redacted before LLM processing 
              and concede to submit the remaining information to LLM processing.
            </p>
            <div className="modal-buttons">
              <button onClick={agreeToProcessing} className="btn-success">
                Agree
              </button>
              <button onClick={rejectProcessing} className="btn-danger">
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Add PII Modal */}
      {showAddPiiModal && (
        <div className="modal">
          <div className="modal-content">
            <h3>Add New PII</h3>
            <div>
              <label htmlFor="piiType">PII Type:</label>
              <select
                id="piiType"
                value={newPii.type}
                onChange={(e) => setNewPii(prev => ({ ...prev, type: e.target.value }))}
              >
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="address">Address</option>
                <option value="name">Name</option>
                <option value="dob">Date of Birth</option>
                <option value="national_id">National ID</option>
                <option value="passport">Passport</option>
                <option value="linkedin">LinkedIn</option>
                <option value="social_media">Social Media</option>
                <option value="postcode">Postcode</option>
              </select>
              
              <label htmlFor="piiText">PII Text:</label>
              <input
                type="text"
                id="piiText"
                value={newPii.text}
                onChange={(e) => setNewPii(prev => ({ ...prev, text: e.target.value }))}
                placeholder="Enter PII text"
              />
              
              <label htmlFor="piiNotes">Notes (optional):</label>
              <textarea
                id="piiNotes"
                value={newPii.notes}
                onChange={(e) => setNewPii(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Add notes about this PII"
              />
            </div>
            <div className="modal-buttons">
              <button onClick={saveNewPii} className="btn-success">
                Save
              </button>
              <button onClick={() => setShowAddPiiModal(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
