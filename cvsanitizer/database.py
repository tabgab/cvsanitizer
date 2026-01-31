"""
Database Models for CV Sanitizer

Implements audit trail and user confirmation tracking as required by the project.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.sql import func
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


Base = declarative_base() if SQLALCHEMY_AVAILABLE else None


class CVProcessingSession:
    """
    Database session for tracking CV processing with audit trail.
    
    This class provides database functionality when SQLAlchemy is available,
    and falls back to file-based storage when it's not.
    """
    
    def __init__(self, db_url: str = "sqlite:///cvsanitizer.db"):
        """
        Initialize database session.
        
        Args:
            db_url: Database connection URL
        """
        self.db_url = db_url
        self.use_database = SQLALCHEMY_AVAILABLE
        
        if self.use_database:
            self._init_database()
        else:
            self._init_file_storage()
    
    def _init_database(self):
        """Initialize SQLAlchemy database."""
        if not SQLALCHEMY_AVAILABLE:
            self.use_database = False
            self._init_file_storage()
            return
        
        try:
            self.engine = create_engine(self.db_url)
            Base.metadata.create_all(self.engine)
            SessionLocal = sessionmaker(bind=self.engine)
            self.session = SessionLocal()
        except Exception:
            # Fallback to file storage if database fails
            self.use_database = False
            self._init_file_storage()
    
    def _init_file_storage(self):
        """Initialize file-based storage fallback."""
        import os
        from pathlib import Path
        
        self.storage_dir = Path("data")
        self.storage_dir.mkdir(exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self.confirmations_file = self.storage_dir / "confirmations.json"
        
        # Initialize files if they don't exist
        if not self.sessions_file.exists():
            with open(self.sessions_file, 'w') as f:
                json.dump({}, f)
        
        if not self.confirmations_file.exists():
            with open(self.confirmations_file, 'w') as f:
                json.dump({}, f)
    
    def create_session(self, pdf_path: str, username: str, country: str = "GB") -> str:
        """
        Create a new processing session.
        
        Args:
            pdf_path: Path to PDF file
            username: Username for audit trail
            country: Country code used for processing
            
        Returns:
            Session ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(pdf_path) % 10000}"
        
        session_data = {
            'session_id': session_id,
            'pdf_path': pdf_path,
            'username': username,
            'country_code': country,
            'created_at': datetime.now().isoformat(),
            'status': 'created',
            'pii_detected': [],
            'user_edits': [],
            'final_confirmation': None,
            'processing_completed_at': None
        }
        
        if self.use_database:
            db_session = CVSessionDB(
                session_id=session_id,
                pdf_path=pdf_path,
                username=username,
                country_code=country,
                status='created'
            )
            self.session.add(db_session)
            self.session.commit()
        else:
            # File-based storage
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            sessions[session_id] = session_data
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2)
        
        return session_id
    
    def record_pii_detection(self, session_id: str, pii_detections: List[Dict[str, Any]]):
        """
        Record PII detections for a session.
        
        Args:
            session_id: Session ID
            pii_detections: List of PII detection data
        """
        if self.use_database:
            db_session = self.session.query(CVSessionDB).filter_by(session_id=session_id).first()
            if db_session:
                db_session.pii_detected = pii_detections
                db_session.status = 'pii_detected'
                self.session.commit()
        else:
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            if session_id in sessions:
                sessions[session_id]['pii_detected'] = pii_detections
                sessions[session_id]['status'] = 'pii_detected'
                with open(self.sessions_file, 'w') as f:
                    json.dump(sessions, f, indent=2)
    
    def record_user_edit(self, session_id: str, edit_data: Dict[str, Any]):
        """
        Record a user edit to PII detections.
        
        Args:
            session_id: Session ID
            edit_data: Dictionary describing the edit
        """
        if self.use_database:
            db_session = self.session.query(CVSessionDB).filter_by(session_id=session_id).first()
            if db_session:
                if not db_session.user_edits:
                    db_session.user_edits = []
                db_session.user_edits.append(edit_data)
                self.session.commit()
        else:
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            if session_id in sessions:
                if 'user_edits' not in sessions[session_id]:
                    sessions[session_id]['user_edits'] = []
                sessions[session_id]['user_edits'].append(edit_data)
                with open(self.sessions_file, 'w') as f:
                    json.dump(sessions, f, indent=2)
    
    def record_final_confirmation(self, session_id: str, username: str, confirmed: bool, 
                                pii_mapping: Dict[str, Any], output_files: Dict[str, str]):
        """
        Record final user confirmation and completion.
        
        Args:
            session_id: Session ID
            username: Username who confirmed
            confirmed: Whether user confirmed the redaction
            pii_mapping: Final PII mapping
            output_files: Paths to output files
        """
        confirmation_data = {
            'session_id': session_id,
            'username': username,
            'confirmed': confirmed,
            'confirmation_time': datetime.now().isoformat(),
            'pii_mapping': pii_mapping,
            'output_files': output_files,
            'pii_count': len(pii_mapping)
        }
        
        if self.use_database:
            # Update session
            db_session = self.session.query(CVSessionDB).filter_by(session_id=session_id).first()
            if db_session:
                db_session.status = 'completed' if confirmed else 'cancelled'
                db_session.processing_completed_at = datetime.now()
                self.session.commit()
            
            # Create confirmation record
            confirmation = CVConfirmationDB(
                session_id=session_id,
                username=username,
                confirmed=confirmed,
                pii_mapping=pii_mapping,
                output_files=output_files
            )
            self.session.add(confirmation)
            self.session.commit()
        else:
            # Update session
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            if session_id in sessions:
                sessions[session_id]['status'] = 'completed' if confirmed else 'cancelled'
                sessions[session_id]['processing_completed_at'] = datetime.now().isoformat()
                sessions[session_id]['final_confirmation'] = confirmation_data
                with open(self.sessions_file, 'w') as f:
                    json.dump(sessions, f, indent=2)
            
            # Store confirmation
            with open(self.confirmations_file, 'r') as f:
                confirmations = json.load(f)
            confirmations[session_id] = confirmation_data
            with open(self.confirmations_file, 'w') as f:
                json.dump(confirmations, f, indent=2)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        if self.use_database:
            db_session = self.session.query(CVSessionDB).filter_by(session_id=session_id).first()
            if db_session:
                return {
                    'session_id': db_session.session_id,
                    'pdf_path': db_session.pdf_path,
                    'username': db_session.username,
                    'country_code': db_session.country_code,
                    'created_at': db_session.created_at.isoformat(),
                    'status': db_session.status,
                    'pii_detected': db_session.pii_detected or [],
                    'user_edits': db_session.user_edits or [],
                    'processing_completed_at': db_session.processing_completed_at.isoformat() if db_session.processing_completed_at else None
                }
        else:
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            return sessions.get(session_id)
        
        return None
    
    def get_user_sessions(self, username: str) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        Args:
            username: Username
            
        Returns:
            List of session data
        """
        if self.use_database:
            db_sessions = self.session.query(CVSessionDB).filter_by(username=username).all()
            return [
                {
                    'session_id': sess.session_id,
                    'pdf_path': sess.pdf_path,
                    'country_code': sess.country_code,
                    'created_at': sess.created_at.isoformat(),
                    'status': sess.status,
                    'processing_completed_at': sess.processing_completed_at.isoformat() if sess.processing_completed_at else None
                }
                for sess in db_sessions
            ]
        else:
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            return [
                sess_data for sess_data in sessions.values()
                if sess_data.get('username') == username
            ]
    
    def get_audit_report(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate audit report for a date range.
        
        Args:
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Audit report data
        """
        if self.use_database:
            query = self.session.query(CVSessionDB)
            
            if start_date:
                query = query.filter(CVSessionDB.created_at >= start_date)
            if end_date:
                query = query.filter(CVSessionDB.created_at <= end_date)
            
            sessions = query.all()
            
            # Get confirmations
            conf_query = self.session.query(CVConfirmationDB)
            if start_date:
                conf_query = conf_query.filter(CVConfirmationDB.confirmation_time >= start_date)
            if end_date:
                conf_query = conf_query.filter(CVConfirmationDB.confirmation_time <= end_date)
            confirmations = conf_query.all()
            
            return {
                'total_sessions': len(sessions),
                'completed_sessions': len([s for s in sessions if s.status == 'completed']),
                'cancelled_sessions': len([s for s in sessions if s.status == 'cancelled']),
                'total_confirmations': len(confirmations),
                'confirmed_redactions': len([c for c in confirmations if c.confirmed]),
                'countries_used': list(set(s.country_code for s in sessions)),
                'unique_users': list(set(s.username for s in sessions)),
                'sessions': [
                    {
                        'session_id': s.session_id,
                        'username': s.username,
                        'pdf_path': s.pdf_path,
                        'created_at': s.created_at.isoformat(),
                        'status': s.status
                    }
                    for s in sessions
                ]
            }
        else:
            # File-based audit report
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            
            with open(self.confirmations_file, 'r') as f:
                confirmations = json.load(f)
            
            # Filter by date if specified
            filtered_sessions = []
            for sess_data in sessions.values():
                sess_date = datetime.fromisoformat(sess_data['created_at'])
                if start_date and sess_date < start_date:
                    continue
                if end_date and sess_date > end_date:
                    continue
                filtered_sessions.append(sess_data)
            
            return {
                'total_sessions': len(filtered_sessions),
                'completed_sessions': len([s for s in filtered_sessions if s.get('status') == 'completed']),
                'cancelled_sessions': len([s for s in filtered_sessions if s.get('status') == 'cancelled']),
                'total_confirmations': len(confirmations),
                'confirmed_redactions': len([c for c in confirmations.values() if c.get('confirmed')]),
                'countries_used': list(set(s.get('country_code') for s in filtered_sessions)),
                'unique_users': list(set(s.get('username') for s in filtered_sessions)),
                'sessions': filtered_sessions
            }


# SQLAlchemy database models (only used when SQLAlchemy is available)
if SQLALCHEMY_AVAILABLE:
    
    class CVSessionDB(Base):
        """Database model for CV processing sessions."""
        __tablename__ = 'cv_sessions'
        
        id = Column(Integer, primary_key=True)
        session_id = Column(String(100), unique=True, nullable=False, index=True)
        pdf_path = Column(String(500), nullable=False)
        username = Column(String(100), nullable=False, index=True)
        country_code = Column(String(10), nullable=False)
        status = Column(String(50), default='created')
        pii_detected = Column(JSON)  # List of PII detections
        user_edits = Column(JSON)  # List of user edits
        created_at = Column(DateTime, default=datetime.utcnow)
        processing_completed_at = Column(DateTime)
        
        def to_dict(self):
            return {
                'session_id': self.session_id,
                'pdf_path': self.pdf_path,
                'username': self.username,
                'country_code': self.country_code,
                'status': self.status,
                'pii_detected': self.pii_detected or [],
                'user_edits': self.user_edits or [],
                'created_at': self.created_at.isoformat(),
                'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None
            }
    
    
    class CVConfirmationDB(Base):
        """Database model for user confirmations."""
        __tablename__ = 'cv_confirmations'
        
        id = Column(Integer, primary_key=True)
        session_id = Column(String(100), nullable=False, index=True)
        username = Column(String(100), nullable=False)
        confirmed = Column(Boolean, nullable=False)
        confirmation_time = Column(DateTime, default=datetime.utcnow)
        pii_mapping = Column(JSON)  # Final PII mapping
        output_files = Column(JSON)  # Output file paths
        
        def to_dict(self):
            return {
                'session_id': self.session_id,
                'username': self.username,
                'confirmed': self.confirmed,
                'confirmation_time': self.confirmation_time.isoformat(),
                'pii_mapping': self.pii_mapping,
                'output_files': self.output_files
            }
