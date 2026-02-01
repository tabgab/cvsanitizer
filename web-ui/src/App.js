import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';

// Helper function to escape regex special characters
const escapeRegex = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const App = () => {
  const [cvText, setCvText] = useState('');
  const [piiData, setPiiData] = useState([]);
  const [selectedPii, setSelectedPii] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [showAddPiiModal, setShowAddPiiModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingPii, setEditingPii] = useState(null);
  const [newPii, setNewPii] = useState({ type: 'email', text: '', notes: '' });
  const [agreementVerified, setAgreementVerified] = useState(false);
  
  // Text selection state
  const [selectionPopup, setSelectionPopup] = useState(null);
  const [showOtherTypeModal, setShowOtherTypeModal] = useState(false);
  const [customPiiType, setCustomPiiType] = useState('');
  const [otherPiiText, setOtherPiiText] = useState(''); // Store text for Other modal
  const cvContainerRef = useRef(null);
  
  // Redacted view toggle
  const [isRedactedView, setIsRedactedView] = useState(false);
  
  // Handle text selection in CV view
  const handleTextSelection = useCallback((e) => {
    // Don't show popup if clicking on a PII box
    if (e.target.closest('[data-pii-box]')) {
      return;
    }
    
    // Deselect all PII when clicking outside boxes
    setSelectedPii([]);
    
    setTimeout(() => {
      const selection = window.getSelection();
      const selectedText = selection.toString().trim();
      
      if (selectedText && selectedText.length > 1) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        // Verify the selected text exists in cvText
        if (cvText.includes(selectedText)) {
          setSelectionPopup({
            text: selectedText,
            x: rect.left + rect.width / 2,
            y: rect.top - 10
          });
        }
      } else {
        setSelectionPopup(null);
      }
    }, 10);
  }, [cvText]);
  
  // Create PII from selected text
  const createPiiFromSelection = (type = 'address') => {
    if (!selectionPopup) return;
    
    setPiiData(prev => [...prev, {
      id: `user-${Date.now()}`,
      type,
      text: selectionPopup.text,
      confidence: 1.0,
      approved: false,
      removed: false,
      userAdded: true
    }]);
    
    setSelectionPopup(null);
    window.getSelection().removeAllRanges();
  };
  
  // Open modal for custom "Other" PII type
  const openOtherTypeModal = () => {
    if (!selectionPopup) return;
    setOtherPiiText(selectionPopup.text); // Store the text before closing popup
    setSelectionPopup(null); // Close the popup
    window.getSelection().removeAllRanges();
    setShowOtherTypeModal(true);
    setCustomPiiType('');
  };
  
  // Create PII with custom type from "Other" modal
  const createCustomPii = () => {
    if (!otherPiiText || !customPiiType.trim()) return;
    
    setPiiData(prev => [...prev, {
      id: `user-${Date.now()}`,
      type: customPiiType.trim().toLowerCase(),
      text: otherPiiText,
      confidence: 1.0,
      approved: false,
      removed: false,
      userAdded: true
    }]);
    
    setShowOtherTypeModal(false);
    setOtherPiiText('');
    setCustomPiiType('');
  };

  // Drag resize state
  const [dragState, setDragState] = useState(null);
  
  // Start dragging to resize a PII box
  const startDrag = useCallback((e, pii, direction, matchStart, matchEnd) => {
    e.stopPropagation();
    e.preventDefault();
    console.log('Starting drag:', direction, pii.text, matchStart, matchEnd);
    setDragState({
      piiId: pii.id,
      direction,
      startX: e.clientX,
      originalText: pii.text,
      matchStart,
      matchEnd
    });
  }, []);
  
  // Handle drag move
  useEffect(() => {
    if (!dragState) return;
    
    const handleMouseMove = (e) => {
      if (!dragState) return;
      
      const pii = piiData.find(p => p.id === dragState.piiId);
      if (!pii) return;
      
      // Calculate character offset based on drag distance (approx 8px per char)
      const deltaX = e.clientX - dragState.startX;
      const charDelta = Math.round(deltaX / 8);
      
      if (charDelta === 0) return;
      
      let newStart = dragState.matchStart;
      let newEnd = dragState.matchEnd;
      
      if (dragState.direction === 'left') {
        newStart = Math.max(0, dragState.matchStart + charDelta);
      } else {
        newEnd = Math.min(cvText.length, dragState.matchEnd + charDelta);
      }
      
      if (newEnd > newStart) {
        const newText = cvText.substring(newStart, newEnd);
        if (newText !== pii.text) {
          setPiiData(prev => prev.map(p => 
            p.id === dragState.piiId ? { ...p, text: newText, userEdited: true } : p
          ));
        }
      }
    };
    
    const handleMouseUp = () => {
      setDragState(null);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragState, cvText, piiData]);

  // Clear selection popup on click outside
  useEffect(() => {
    const handleClick = (e) => {
      if (selectionPopup && !e.target.closest('[data-selection-popup]')) {
        // Small delay to allow button clicks to register
        setTimeout(() => {
          const selection = window.getSelection();
          if (!selection.toString().trim()) {
            setSelectionPopup(null);
          }
        }, 100);
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [selectionPopup]);

  // Available test CVs
  const testCVs = [
    'CV_Ahmed_Mohamed',
    'CV_Carlos_Silva', 
    'CV_Hans_Mueller',
    'CV_Jose_Garcia',
    'CV_Tanaka_Taro'
  ];
  
  const [currentCV, setCurrentCV] = useState('');

  useEffect(() => {
    // Check URL parameter for CV name, otherwise pick random
    const urlParams = new URLSearchParams(window.location.search);
    const cvParam = urlParams.get('cv');
    
    let cvName;
    if (cvParam) {
      // Use provided CV name (strip .pdf extension if present)
      cvName = cvParam.replace('.pdf', '').replace('.PDF', '');
    } else {
      // Pick random CV from test set
      cvName = testCVs[Math.floor(Math.random() * testCVs.length)];
    }
    
    setCurrentCV(cvName);
    loadData(cvName);
  }, []);

  const loadData = async (cvName) => {
    if (!cvName) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Load the redacted JSON which contains the extracted text
      const redactedResponse = await fetch(`/imaginary_test_cvs/${cvName}_redacted.json`);
      if (!redactedResponse.ok) throw new Error(`Failed to fetch redacted data for ${cvName}: ${redactedResponse.status}`);
      
      const redactedJson = await redactedResponse.json();
      
      // Get the original text by replacing PII placeholders with actual values
      let originalText = redactedJson.redacted_text || '';
      
      // Load PII data
      const piiResponse = await fetch(`/imaginary_test_cvs/${cvName}.pii.json`);
      if (!piiResponse.ok) throw new Error(`Failed to fetch PII for ${cvName}: ${piiResponse.status}`);
      
      const piiJson = await piiResponse.json();
      const piiArray = Object.entries(piiJson).map(([id, data]) => ({
        id,
        type: data.category,
        text: data.original,
        confidence: data.confidence,
        approved: false,
        removed: false,
        userAdded: false
      }));
      
      // Reconstruct original text by replacing PII placeholders with original values
      piiArray.forEach(pii => {
        // Replace PII tags like <pii type="email" serial="19"> with the original text
        const tagPattern = new RegExp(`<pii[^>]*serial="${pii.id.replace('pii_', '')}"[^>]*>`, 'g');
        originalText = originalText.replace(tagPattern, pii.text);
      });
      
      // Also try direct ID replacement for any remaining placeholders
      piiArray.forEach(pii => {
        originalText = originalText.replace(pii.id, pii.text);
      });
      
      // Clean up any remaining PII tags that weren't matched
      originalText = originalText.replace(/<pii[^>]*>/g, '[REDACTED]');
      
      setCvText(originalText);
      setPiiData(piiArray);
      setLoading(false);
    } catch (err) {
      console.error('Error loading data:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  // Render CV text with PII highlighted
  const renderCvWithPii = useMemo(() => {
    if (!cvText || piiData.length === 0) return cvText;
    
    // Sort PII by text length (longest first) to handle overlapping matches
    const sortedPii = [...piiData]
      .filter(p => !p.removed)
      .sort((a, b) => b.text.length - a.text.length);
    
    // Create a map of positions to PII
    let result = cvText;
    const replacements = [];
    
    sortedPii.forEach(pii => {
      // Only find the FIRST occurrence of each PII text, not all occurrences
      // This prevents words like "Hungarian" from being redacted everywhere
      const regex = new RegExp(escapeRegex(pii.text), 'i');
      const match = regex.exec(cvText);
      if (match) {
        replacements.push({
          start: match.index,
          end: match.index + match[0].length,
          pii,
          originalText: match[0]
        });
      }
    });
    
    // Sort by position and remove overlaps
    replacements.sort((a, b) => a.start - b.start);
    const filtered = [];
    let lastEnd = 0;
    for (const r of replacements) {
      if (r.start >= lastEnd) {
        filtered.push(r);
        lastEnd = r.end;
      }
    }
    
    // Build result with React elements
    const elements = [];
    let currentPos = 0;
    
    filtered.forEach((r, idx) => {
      // Add text before this match
      if (r.start > currentPos) {
        elements.push(cvText.substring(currentPos, r.start));
      }
      
      // Add highlighted PII with drag handles
      const isSelected = selectedPii.includes(r.pii.id);
      elements.push(
        <span
          key={`pii-${idx}`}
          data-pii-box="true"
          style={{ display: 'inline-flex', alignItems: 'center' }}
        >
          {/* Left drag handle */}
          <span
            onMouseDown={(e) => startDrag(e, r.pii, 'left', r.start, r.end)}
            style={{
              display: 'inline-block',
              width: 6,
              height: 20,
              cursor: 'ew-resize',
              background: isSelected ? '#3498db' : '#e74c3c',
              borderRadius: '3px 0 0 3px',
              marginRight: -1
            }}
            title="Drag left to extend"
          />
          <span
            onClick={() => togglePiiSelection(r.pii.id)}
            style={{
              backgroundColor: isSelected ? 'rgba(52, 152, 219, 0.4)' : 'rgba(231, 76, 60, 0.3)',
              border: `2px solid ${isSelected ? '#3498db' : '#e74c3c'}`,
              borderRadius: '0',
              padding: '1px 4px',
              cursor: 'pointer',
              display: 'inline',
              fontWeight: 'bold'
            }}
            title={`${r.pii.type}: ${r.pii.text} (${(r.pii.confidence * 100).toFixed(0)}% confidence)`}
          >
            {r.originalText}
          </span>
          {/* Right drag handle */}
          <span
            onMouseDown={(e) => startDrag(e, r.pii, 'right', r.start, r.end)}
            style={{
              display: 'inline-block',
              width: 6,
              height: 20,
              cursor: 'ew-resize',
              background: isSelected ? '#3498db' : '#e74c3c',
              borderRadius: '0 3px 3px 0',
              marginLeft: -1
            }}
            title="Drag right to extend"
          />
        </span>
      );
      
      currentPos = r.end;
    });
    
    // Add remaining text
    if (currentPos < cvText.length) {
      elements.push(cvText.substring(currentPos));
    }
    
    return elements;
  }, [cvText, piiData, selectedPii, startDrag]);

  const togglePiiSelection = (piiId) => {
    setSelectedPii(prev => 
      prev.includes(piiId) ? prev.filter(id => id !== piiId) : [...prev, piiId]
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
    setSelectedPii(piiData.filter(p => !p.removed).map(p => p.id));
  };

  const deselectAll = () => setSelectedPii([]);

  const approveAll = () => setShowApprovalModal(true);

  const agreeToProcessing = () => {
    setPiiData(prev => prev.map(pii => !pii.removed ? { ...pii, approved: true } : pii));
    setAgreementVerified(true);
    setShowApprovalModal(false);
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
      setPiiData(prev => [...prev, {
        id: `user-${Date.now()}`,
        type: newPii.type,
        text: newPii.text,
        confidence: 1.0,
        approved: false,
        removed: false,
        userAdded: true
      }]);
      setShowAddPiiModal(false);
    }
  };

  // Merge selected PII items into one
  const mergeSelected = () => {
    if (selectedPii.length < 2) {
      alert('Select at least 2 PII items to merge');
      return;
    }
    
    const toMerge = piiData.filter(p => selectedPii.includes(p.id));
    
    // Find the combined text in cvText by locating positions
    const positions = [];
    toMerge.forEach(pii => {
      const idx = cvText.toLowerCase().indexOf(pii.text.toLowerCase());
      if (idx !== -1) {
        positions.push({ start: idx, end: idx + pii.text.length, pii });
      }
    });
    
    if (positions.length < 2) {
      alert('Could not find all selected items in the text');
      return;
    }
    
    // Sort by position
    positions.sort((a, b) => a.start - b.start);
    
    // Get the text span from first to last
    const mergedText = cvText.substring(positions[0].start, positions[positions.length - 1].end);
    const primaryType = toMerge[0].type;
    
    // Create merged PII
    const mergedPii = {
      id: `merged-${Date.now()}`,
      type: primaryType,
      text: mergedText,
      confidence: Math.max(...toMerge.map(p => p.confidence)),
      approved: false,
      removed: false,
      userAdded: true,
      mergedFrom: toMerge.map(p => p.id)
    };
    
    // Remove old items and add merged
    setPiiData(prev => [
      ...prev.map(p => selectedPii.includes(p.id) ? { ...p, removed: true } : p),
      mergedPii
    ]);
    setSelectedPii([mergedPii.id]);
  };

  // Open edit modal for a PII item
  const openEditModal = (pii) => {
    // Find context around the PII text
    const idx = cvText.toLowerCase().indexOf(pii.text.toLowerCase());
    const contextStart = Math.max(0, idx - 30);
    const contextEnd = Math.min(cvText.length, idx + pii.text.length + 30);
    const context = cvText.substring(contextStart, contextEnd);
    
    setEditingPii({
      ...pii,
      newText: pii.text,
      context,
      contextStart,
      originalIdx: idx
    });
    setShowEditModal(true);
  };

  // Save edited PII
  const saveEditedPii = () => {
    if (!editingPii || !editingPii.newText.trim()) return;
    
    // Verify the new text exists in CV
    if (!cvText.toLowerCase().includes(editingPii.newText.toLowerCase())) {
      alert('The new text must exist in the CV. Copy the exact text from the preview.');
      return;
    }
    
    setPiiData(prev => prev.map(p => 
      p.id === editingPii.id 
        ? { ...p, text: editingPii.newText, userEdited: true }
        : p
    ));
    setShowEditModal(false);
    setEditingPii(null);
  };

  // Render redacted view with Type_REDACTED placeholders
  const renderRedactedView = useMemo(() => {
    if (!cvText) return null;
    
    // Preview shows ALL non-removed PII (marked for redaction)
    // Export will only use approved items
    const piiToRedact = piiData.filter(p => !p.removed);
    if (piiToRedact.length === 0) {
      return <span style={{ color: '#666', fontStyle: 'italic' }}>No PII marked for redaction. Add PII items in edit mode.</span>;
    }
    
    // Find all PII positions
    const replacements = [];
    piiToRedact.forEach(pii => {
      const regex = new RegExp(escapeRegex(pii.text), 'i');
      const match = regex.exec(cvText);
      if (match) {
        replacements.push({
          start: match.index,
          end: match.index + match[0].length,
          pii,
          originalText: match[0]
        });
      }
    });
    
    // Sort by position and remove overlaps
    replacements.sort((a, b) => a.start - b.start);
    const filtered = [];
    let lastEnd = 0;
    for (const r of replacements) {
      if (r.start >= lastEnd) {
        filtered.push(r);
        lastEnd = r.end;
      }
    }
    
    // Build result with redacted placeholders
    const elements = [];
    let currentPos = 0;
    
    filtered.forEach((r, idx) => {
      if (r.start > currentPos) {
        elements.push(cvText.substring(currentPos, r.start));
      }
      
      // Format type for display (capitalize first letter)
      const typeDisplay = r.pii.type.charAt(0).toUpperCase() + r.pii.type.slice(1);
      elements.push(
        <span key={`redacted-${idx}`} style={{ color: '#e74c3c', fontWeight: 'bold' }}>
          {typeDisplay}_REDACTED
        </span>
      );
      
      currentPos = r.end;
    });
    
    if (currentPos < cvText.length) {
      elements.push(cvText.substring(currentPos));
    }
    
    return elements;
  }, [cvText, piiData]);

  // Generate redacted text string for export
  const generateRedactedText = () => {
    if (!cvText) return '';
    
    const piiToRedact = piiData.filter(p => !p.removed && p.approved);
    if (piiToRedact.length === 0) return cvText;
    
    let redactedText = cvText;
    const piiMapping = {};
    let serial = 1;
    
    // Sort PII by position (descending) to replace from end to start
    const sortedPii = [...piiToRedact].sort((a, b) => {
      const posA = cvText.toLowerCase().indexOf(a.text.toLowerCase());
      const posB = cvText.toLowerCase().indexOf(b.text.toLowerCase());
      return posB - posA;
    });
    
    sortedPii.forEach(pii => {
      const regex = new RegExp(escapeRegex(pii.text), 'i');
      const match = regex.exec(redactedText);
      if (match) {
        const placeholder = `<pii type="${pii.type}" serial="${serial}">`;
        piiMapping[placeholder] = {
          original: pii.text,
          category: pii.type,
          position: { start: match.index, end: match.index + match[0].length },
          confidence: pii.confidence || 0.9
        };
        redactedText = redactedText.substring(0, match.index) + placeholder + redactedText.substring(match.index + match[0].length);
        serial++;
      }
    });
    
    return { redactedText, piiMapping };
  };

  const exportResults = () => {
    const { redactedText, piiMapping } = generateRedactedText();
    const timestamp = new Date().toISOString();
    
    // Redacted JSON (for LLM processing)
    const redactedJson = {
      cv_filename: `${currentCV}_redacted.json`,
      original_filename: `${currentCV}.pdf`,
      processing_date: timestamp,
      pii_detected_count: Object.keys(piiMapping).length,
      redacted_text: redactedText,
      pii_summary: {
        total: Object.keys(piiMapping).length,
        by_category: piiData.filter(p => !p.removed && p.approved).reduce((acc, p) => {
          acc[p.type] = (acc[p.type] || 0) + 1;
          return acc;
        }, {})
      },
      llm_processing_agreement: agreementVerified,
      llm_agreement_timestamp: agreementVerified ? timestamp : null
    };
    
    // PII Mapping JSON (for reconstruction)
    const piiMappingJson = piiMapping;
    
    // Download redacted JSON
    const blob1 = new Blob([JSON.stringify(redactedJson, null, 2)], { type: 'application/json' });
    const a1 = document.createElement('a');
    a1.href = URL.createObjectURL(blob1);
    a1.download = `${currentCV}_redacted.json`;
    a1.click();
    
    // Download PII mapping JSON
    setTimeout(() => {
      const blob2 = new Blob([JSON.stringify(piiMappingJson, null, 2)], { type: 'application/json' });
      const a2 = document.createElement('a');
      a2.href = URL.createObjectURL(blob2);
      a2.download = `${currentCV}.pii.json`;
      a2.click();
    }, 500);
  };

  const stats = {
    total: piiData.length,
    approved: piiData.filter(p => p.approved && !p.removed).length,
    rejected: piiData.filter(p => p.removed).length,
    pending: piiData.filter(p => !p.approved && !p.removed).length
  };

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center' }}><h2>Loading CV data...</h2></div>;
  }

  if (error) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'red' }}><h2>Error: {error}</h2></div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'Arial, sans-serif' }}>
      {/* Header */}
      <div style={{ background: '#2c3e50', color: 'white', padding: 15, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>CV Sanitizer - PII Review Interface</h1>
        <button
          onClick={() => setIsRedactedView(!isRedactedView)}
          style={{
            background: isRedactedView ? '#e74c3c' : '#27ae60',
            border: 'none',
            borderRadius: 8,
            padding: '10px 20px',
            color: 'white',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 14,
            fontWeight: 'bold'
          }}
          title={isRedactedView ? 'Switch to Edit Mode' : 'Preview Redacted View'}
        >
          {isRedactedView ? (
            <>
              {/* Eye with strikethrough */}
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23" stroke="#e74c3c" strokeWidth="3"/>
              </svg>
              Edit Mode
            </>
          ) : (
            <>
              {/* Eye icon */}
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              Preview Redacted
            </>
          )}
        </button>
      </div>
      
      {/* Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* CV Content View */}
        <div 
          ref={cvContainerRef}
          style={{ flex: 1, overflow: 'auto', padding: 20, background: '#fff', position: 'relative' }}
          onMouseUp={handleTextSelection}
        >
          <div style={{ 
            maxWidth: 800, 
            margin: '0 auto', 
            background: '#fafafa', 
            padding: 30, 
            borderRadius: 8,
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            lineHeight: 1.8,
            fontSize: 14,
            whiteSpace: 'pre-wrap',
            fontFamily: 'Georgia, serif'
          }}>
            <div style={{ textAlign: 'center', marginBottom: 20, borderBottom: '2px solid #2c3e50', paddingBottom: 15 }}>
              <h2 style={{ margin: 0, color: '#2c3e50' }}>
                CURRICULUM VITAE
                {isRedactedView && <span style={{ color: '#e74c3c', fontSize: 14, marginLeft: 10 }}>(REDACTED PREVIEW)</span>}
              </h2>
              <p style={{ color: '#666', fontSize: 12, marginTop: 10 }}>
                {isRedactedView 
                  ? 'Preview: All marked PII shown as redacted. Approve items before Export for final version.'
                  : 'Select text to add as PII • Click boxes to select • Drag box edges to resize'
                }
              </p>
            </div>
            {isRedactedView ? renderRedactedView : renderCvWithPii}
          </div>
          
          {/* Selection Popup - only show in edit mode */}
          {selectionPopup && !isRedactedView && (
            <div 
              data-selection-popup="true"
              style={{
                position: 'fixed',
                left: selectionPopup.x,
                top: selectionPopup.y,
                transform: 'translate(-50%, -100%)',
                background: '#2c3e50',
                borderRadius: 6,
                padding: 8,
                boxShadow: '0 3px 12px rgba(0,0,0,0.3)',
                zIndex: 1000,
                display: 'flex',
                gap: 4
              }}>
              <button onClick={() => createPiiFromSelection('name')} style={popupBtnStyle}>Name</button>
              <button onClick={() => createPiiFromSelection('email')} style={popupBtnStyle}>Email</button>
              <button onClick={() => createPiiFromSelection('phone')} style={popupBtnStyle}>Phone</button>
              <button onClick={() => createPiiFromSelection('address')} style={popupBtnStyle}>Address</button>
              <button onClick={() => createPiiFromSelection('linkedin')} style={popupBtnStyle}>LinkedIn</button>
              <button onClick={() => createPiiFromSelection('nationality')} style={popupBtnStyle}>Nationality</button>
              <button onClick={openOtherTypeModal} style={{ ...popupBtnStyle, background: '#9b59b6' }}>Other...</button>
              <button onClick={() => setSelectionPopup(null)} style={{ ...popupBtnStyle, background: '#e74c3c' }}>✕</button>
              <div style={{
                position: 'absolute',
                bottom: -6,
                left: '50%',
                transform: 'translateX(-50%)',
                width: 0,
                height: 0,
                borderLeft: '6px solid transparent',
                borderRight: '6px solid transparent',
                borderTop: '6px solid #2c3e50'
              }} />
            </div>
          )}
        </div>
        
        {/* Controls Panel */}
        <div style={{ width: 320, padding: 15, background: '#f8f9fa', overflowY: 'auto', borderLeft: '1px solid #ddd' }}>
          {/* Stats */}
          <div style={{ background: 'white', border: '1px solid #ddd', borderRadius: 4, padding: 12, marginBottom: 15 }}>
            <h4 style={{ margin: '0 0 10px 0' }}>PII Summary</h4>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Total:</span><b style={{ color: '#3498db' }}>{stats.total}</b></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Approved:</span><b style={{ color: '#27ae60' }}>{stats.approved}</b></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Rejected:</span><b style={{ color: '#e74c3c' }}>{stats.rejected}</b></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Pending:</span><b style={{ color: '#f39c12' }}>{stats.pending}</b></div>
          </div>
          
          {/* Legend */}
          <div style={{ background: 'white', border: '1px solid #ddd', borderRadius: 4, padding: 12, marginBottom: 15 }}>
            <h4 style={{ margin: '0 0 10px 0' }}>Legend</h4>
            <div style={{ marginBottom: 5 }}>
              <span style={{ backgroundColor: 'rgba(231, 76, 60, 0.3)', border: '2px solid #e74c3c', borderRadius: 3, padding: '2px 6px', marginRight: 8 }}>PII</span>
              Detected PII (unselected)
            </div>
            <div>
              <span style={{ backgroundColor: 'rgba(52, 152, 219, 0.4)', border: '2px solid #3498db', borderRadius: 3, padding: '2px 6px', marginRight: 8 }}>PII</span>
              Selected PII
            </div>
          </div>
          
          {/* PII Items */}
          <div style={{ marginBottom: 15 }}>
            <h4>PII Items</h4>
            {piiData.map(pii => (
              <div
                key={pii.id}
                onClick={() => !pii.removed && togglePiiSelection(pii.id)}
                style={{
                  border: `1px solid ${selectedPii.includes(pii.id) ? '#3498db' : '#ddd'}`,
                  borderRadius: 4,
                  padding: 8,
                  margin: '5px 0',
                  background: selectedPii.includes(pii.id) ? '#e3f2fd' : 'white',
                  cursor: pii.removed ? 'default' : 'pointer',
                  opacity: pii.removed ? 0.4 : 1,
                  textDecoration: pii.removed ? 'line-through' : 'none'
                }}
              >
                <div style={{ fontWeight: 'bold', fontSize: 11, textTransform: 'uppercase', color: '#2c3e50' }}>{pii.type}</div>
                <div style={{ fontSize: 13, color: '#555', margin: '3px 0' }}>{pii.text}</div>
                <div style={{ fontSize: 11, color: '#888' }}>Confidence: {(pii.confidence * 100).toFixed(0)}%</div>
                {pii.approved && <div style={{ color: '#27ae60', fontWeight: 'bold', fontSize: 11 }}>✓ Approved</div>}
              </div>
            ))}
          </div>
          
          {/* Control Buttons */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 10 }}>
            <button onClick={selectAll} style={btnStyle}>Select All</button>
            <button onClick={deselectAll} style={btnStyle}>Deselect</button>
          </div>
          
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 10 }}>
            <button onClick={removeSelected} disabled={!selectedPii.length} style={{ ...btnStyle, background: selectedPii.length ? '#e74c3c' : '#aaa' }}>Delete</button>
            <button onClick={approveSelected} disabled={!selectedPii.length} style={{ ...btnStyle, background: selectedPii.length ? '#27ae60' : '#aaa' }}>Approve</button>
            <button onClick={mergeSelected} disabled={selectedPii.length < 2} style={{ ...btnStyle, background: selectedPii.length >= 2 ? '#9b59b6' : '#aaa' }}>Merge</button>
            <button onClick={() => selectedPii.length === 1 && openEditModal(piiData.find(p => p.id === selectedPii[0]))} disabled={selectedPii.length !== 1} style={{ ...btnStyle, background: selectedPii.length === 1 ? '#f39c12' : '#aaa' }}>Edit</button>
          </div>
          
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 15 }}>
            <button onClick={approveAll} style={{ ...btnStyle, background: '#27ae60', fontWeight: 'bold' }}>Approve All</button>
            <button onClick={addNewPii} style={btnStyle}>Add PII</button>
            <button onClick={exportResults} style={btnStyle}>Export</button>
          </div>
        </div>
      </div>
      
      {/* Approval Modal */}
      {showApprovalModal && (
        <div style={modalOverlay}>
          <div style={modalContent}>
            <h3>LLM Processing Consent</h3>
            <p>I have reviewed what personal information will be redacted before LLM processing and concede to submit the remaining information to LLM processing.</p>
            <div style={{ marginTop: 20 }}>
              <button onClick={agreeToProcessing} style={{ ...btnStyle, background: '#27ae60', marginRight: 10 }}>Agree</button>
              <button onClick={rejectProcessing} style={{ ...btnStyle, background: '#e74c3c' }}>Reject</button>
            </div>
          </div>
        </div>
      )}
      
      {/* Add PII Modal */}
      {showAddPiiModal && (
        <div style={modalOverlay}>
          <div style={modalContent}>
            <h3>Add New PII</h3>
            <div style={{ textAlign: 'left' }}>
              <label>Type:</label>
              <select value={newPii.type} onChange={e => setNewPii(p => ({ ...p, type: e.target.value }))} style={{ width: '100%', padding: 8, marginBottom: 10 }}>
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="address">Address</option>
                <option value="name">Name</option>
                <option value="dob">Date of Birth</option>
                <option value="linkedin">LinkedIn</option>
                <option value="postcode">Postcode</option>
              </select>
              <label>Text (must match text in CV):</label>
              <input type="text" value={newPii.text} onChange={e => setNewPii(p => ({ ...p, text: e.target.value }))} style={{ width: '100%', padding: 8, marginBottom: 10 }} placeholder="Enter exact text from CV" />
            </div>
            <button onClick={saveNewPii} style={{ ...btnStyle, background: '#27ae60', marginRight: 10 }}>Save</button>
            <button onClick={() => setShowAddPiiModal(false)} style={btnStyle}>Cancel</button>
          </div>
        </div>
      )}
      
      {/* Edit PII Modal */}
      {showEditModal && editingPii && (
        <div style={modalOverlay}>
          <div style={{ ...modalContent, maxWidth: 600, textAlign: 'left' }}>
            <h3>Edit PII Boundaries</h3>
            <p style={{ fontSize: 12, color: '#666', marginBottom: 15 }}>
              Extend or modify the text that should be redacted. The text must exist in the CV.
            </p>
            
            <div style={{ marginBottom: 15 }}>
              <label style={{ fontWeight: 'bold' }}>Type:</label>
              <select 
                value={editingPii.type} 
                onChange={e => setEditingPii(p => ({ ...p, type: e.target.value }))} 
                style={{ width: '100%', padding: 8, marginBottom: 10 }}
              >
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="address">Address</option>
                <option value="name">Name</option>
                <option value="dob">Date of Birth</option>
                <option value="linkedin">LinkedIn</option>
                <option value="postcode">Postcode</option>
              </select>
            </div>
            
            <div style={{ marginBottom: 15 }}>
              <label style={{ fontWeight: 'bold' }}>Context (select text to include):</label>
              <div style={{ 
                background: '#f5f5f5', 
                padding: 10, 
                borderRadius: 4, 
                fontFamily: 'monospace',
                fontSize: 13,
                lineHeight: 1.6,
                marginTop: 5,
                whiteSpace: 'pre-wrap',
                border: '1px solid #ddd'
              }}>
                {editingPii.context}
              </div>
              <p style={{ fontSize: 11, color: '#888', marginTop: 5 }}>
                Copy the exact text you want to redact from above
              </p>
            </div>
            
            <div style={{ marginBottom: 15 }}>
              <label style={{ fontWeight: 'bold' }}>Current text:</label>
              <div style={{ 
                background: 'rgba(231, 76, 60, 0.2)', 
                padding: 8, 
                borderRadius: 4,
                border: '1px solid #e74c3c',
                fontFamily: 'monospace',
                marginTop: 5
              }}>
                {editingPii.text}
              </div>
            </div>
            
            <div style={{ marginBottom: 15 }}>
              <label style={{ fontWeight: 'bold' }}>New text to redact:</label>
              <input 
                type="text" 
                value={editingPii.newText} 
                onChange={e => setEditingPii(p => ({ ...p, newText: e.target.value }))} 
                style={{ width: '100%', padding: 8, fontFamily: 'monospace', marginTop: 5 }} 
                placeholder="Enter or paste the exact text from context above"
              />
            </div>
            
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => { setShowEditModal(false); setEditingPii(null); }} style={btnStyle}>Cancel</button>
              <button onClick={saveEditedPii} style={{ ...btnStyle, background: '#27ae60' }}>Save Changes</button>
            </div>
          </div>
        </div>
      )}
      
      {/* Custom PII Type Modal (Other) */}
      {showOtherTypeModal && otherPiiText && (
        <div style={modalOverlay}>
          <div style={modalContent}>
            <h3>Add Custom PII Type</h3>
            <p style={{ fontSize: 13, color: '#666', marginBottom: 15 }}>
              Selected text: <strong>"{otherPiiText}"</strong>
            </p>
            <div style={{ textAlign: 'left', marginBottom: 15 }}>
              <label style={{ fontWeight: 'bold' }}>Custom type name:</label>
              <input 
                type="text" 
                value={customPiiType} 
                onChange={e => setCustomPiiType(e.target.value)} 
                style={{ width: '100%', padding: 8, marginTop: 5 }} 
                placeholder="e.g., passport, ssn, id_number, religion"
                autoFocus
              />
              <p style={{ fontSize: 11, color: '#888', marginTop: 5 }}>
                Enter any descriptive type name (will be converted to lowercase)
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button onClick={() => { setShowOtherTypeModal(false); }} style={btnStyle}>Cancel</button>
              <button 
                onClick={createCustomPii} 
                disabled={!customPiiType.trim()}
                style={{ ...btnStyle, background: customPiiType.trim() ? '#27ae60' : '#aaa' }}
              >
                Add PII
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const btnStyle = { background: '#3498db', color: 'white', border: 'none', padding: '8px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 13 };
const popupBtnStyle = { background: '#3498db', color: 'white', border: 'none', padding: '4px 8px', borderRadius: 3, cursor: 'pointer', fontSize: 11, whiteSpace: 'nowrap' };
const modalOverlay = { position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 };
const modalContent = { background: 'white', padding: 25, borderRadius: 8, maxWidth: 450, textAlign: 'center' };

export default App;
