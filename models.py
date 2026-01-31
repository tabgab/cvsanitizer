"""
Database models for Calamari.
Handles users, profiles, chat history, and job searches.

GDPR Compliance: Sensitive PII fields use encrypted column types.
See utils/encryption.py for implementation details.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Import encryption types for GDPR-compliant PII storage
from utils.encryption import EncryptedText, EncryptedJSON, EncryptedInteger

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """User account model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    # Email: Kept unencrypted for indexed lookup (required for login)
    # Consider hashing for additional security in future
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth-only users
    # ENCRYPTED: User's name is PII
    name = db.Column(EncryptedText(), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Admin and status fields
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)  # For disabling accounts
    
    # OAuth providers
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    linkedin_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    auth_provider = db.Column(db.String(50), default='email')  # 'email', 'google', 'linkedin'
    
    # GDPR compliance
    gdpr_consent_at = db.Column(db.DateTime)
    data_export_requested_at = db.Column(db.DateTime)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    # ENCRYPTED: IP addresses are PII
    last_login_ip = db.Column(EncryptedText())  # IPv6 compatible
    
    # Two-Factor Authentication (2FA)
    # ENCRYPTED: TOTP secret is sensitive
    totp_secret = db.Column(EncryptedText())  # Base32-encoded TOTP secret
    totp_enabled = db.Column(db.Boolean, default=False)  # 2FA enabled flag
    totp_confirmed = db.Column(db.Boolean, default=False)  # Setup completed
    # ENCRYPTED: Backup codes are sensitive
    backup_codes = db.Column(EncryptedJSON())  # Hashed one-time backup codes
    totp_enabled_at = db.Column(db.DateTime)  # When 2FA was enabled
    
    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    job_searches = db.relationship('JobSearch', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash."""
        if not self.password_hash:
            return False  # OAuth-only users have no password
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'has_profile': self.profile is not None,
            'onboarding_complete': self.profile.onboarding_complete if self.profile else False,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'auth_provider': self.auth_provider or 'email',
            'has_password': bool(self.password_hash),
            'has_google': bool(self.google_id),
            'has_linkedin': bool(self.linkedin_id),
            # Two-Factor Authentication
            'totp_enabled': self.totp_enabled or False,
            'totp_confirmed': self.totp_confirmed or False
        }


class UserProfile(db.Model):
    """User profile and job preferences."""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # CV Data - ENCRYPTED: Contains sensitive personal/career information
    cv_filename = db.Column(db.String(255))  # Filename only, not sensitive
    cv_text = db.Column(EncryptedText())  # ENCRYPTED: Full CV text
    cv_analysis = db.Column(EncryptedJSON())  # ENCRYPTED: Parsed CV data from AI
    
    # Job Preferences - ENCRYPTED: Personal career goals
    why_looking = db.Column(EncryptedText())  # ENCRYPTED: Why looking for new job
    ideal_job = db.Column(EncryptedText())  # ENCRYPTED: Dream role description
    priorities = db.Column(EncryptedJSON())  # ENCRYPTED: What matters most
    
    # Logistics - ENCRYPTED: Financial and location data
    desired_salary_min = db.Column(EncryptedInteger())  # ENCRYPTED
    desired_salary_max = db.Column(EncryptedInteger())  # ENCRYPTED
    salary_currency = db.Column(db.String(10), default='GBP')  # Not sensitive
    preferred_locations = db.Column(EncryptedJSON())  # ENCRYPTED: Location preferences
    willing_to_relocate = db.Column(db.Boolean, default=False)
    needs_visa_sponsorship = db.Column(db.Boolean, default=False)
    work_preference = db.Column(db.String(50))  # remote/hybrid/onsite - not sensitive
    
    # Additional preferences - ENCRYPTED where containing personal info
    industries = db.Column(EncryptedJSON())  # ENCRYPTED: Preferred industries
    company_sizes = db.Column(db.JSON)  # Not sensitive
    excluded_companies = db.Column(EncryptedJSON())  # ENCRYPTED: Companies to avoid
    custom_notes = db.Column(EncryptedText())  # ENCRYPTED: Free-form notes for AI
    goal_preferences = db.Column(EncryptedJSON())  # ENCRYPTED: Processed swipe preferences
    profile_overrides = db.Column(EncryptedJSON())  # ENCRYPTED: User's manual edits
    
    # LinkedIn-style structured profile sections (GDPR-encrypted)
    # ENCRYPTED: Contains detailed work history with achievements
    experiences = db.Column(EncryptedJSON())  # List of experience dicts
    # ENCRYPTED: Contains educational history with modules/grades
    educations = db.Column(EncryptedJSON())  # List of education dicts
    # ENCRYPTED: Professional skills with proficiency levels
    skills_structured = db.Column(EncryptedJSON())  # List of skill dicts
    # ENCRYPTED: Certifications and achievements
    certifications_structured = db.Column(EncryptedJSON())  # List of cert dicts
    
    # CV Health Score (non-PII)
    cv_health_score = db.Column(db.Integer)  # 0-100, not sensitive
    cv_health_updated_at = db.Column(db.DateTime)
    
    # Status
    onboarding_complete = db.Column(db.Boolean, default=False)
    onboarding_step = db.Column(db.Integer, default=1)
    
    # Premium features
    is_premium = db.Column(db.Boolean, default=False)  # Legacy - kept for backward compatibility
    
    # Subscription tier system
    subscription_tier = db.Column(db.String(20), default='free')  # 'free', 'standard', 'premium'
    pending_tier = db.Column(db.String(20), nullable=True)  # Tier awaiting payment completion
    subscription_started_at = db.Column(db.DateTime)
    subscription_expires_at = db.Column(db.DateTime)
    subscription_status = db.Column(db.String(20))  # 'active', 'past_due', 'canceled', etc.
    subscription_cancel_at_period_end = db.Column(db.Boolean, default=False)
    
    # Stripe integration
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True)
    
    # Payment tracking
    payment_failed_at = db.Column(db.DateTime)  # When payment first failed
    payment_reminder_sent = db.Column(db.Boolean, default=False)  # 2-day reminder sent
    deletion_warning_sent = db.Column(db.Boolean, default=False)  # 30-day warning sent
    scheduled_deletion_at = db.Column(db.DateTime)  # When account will be deleted
    
    # Usage tracking
    monthly_cv_uploads = db.Column(db.Integer, default=0)
    cv_uploads_reset_at = db.Column(db.DateTime)
    
    # Recap email settings
    recap_email_time = db.Column(db.String(5), default='18:00')  # HH:MM format
    
    # Active persona (for premium users)
    active_persona_id = db.Column(db.Integer, db.ForeignKey('personas.id', use_alter=True), nullable=True)
    
    # Demo mode (for investor presentations)
    demo_mode_active = db.Column(db.Boolean, default=False)
    
    # Marketing preferences
    marketing_emails_enabled = db.Column(db.Boolean, default=True)
    product_updates_enabled = db.Column(db.Boolean, default=True)
    marketing_consent_at = db.Column(db.DateTime)  # When consent was given/updated
    
    # GDPR deletion request
    deletion_requested_at = db.Column(db.DateTime)  # When deletion was requested
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'user_id': self.user_id,
            'cv_filename': self.cv_filename,
            'has_cv': bool(self.cv_filename),  # Added for frontend CV status check
            'cv_analysis': self.cv_analysis,
            'profile_overrides': self.profile_overrides,
            # LinkedIn-style structured sections
            'experiences': self.experiences or [],
            'educations': self.educations or [],
            'skills_structured': self.skills_structured or [],
            'certifications_structured': self.certifications_structured or [],
            'cv_health_score': self.cv_health_score,
            'cv_health_updated_at': self.cv_health_updated_at.isoformat() if self.cv_health_updated_at else None,
            # Job preferences
            'why_looking': self.why_looking,
            'ideal_job': self.ideal_job,
            'priorities': self.priorities,
            'desired_salary_min': self.desired_salary_min,
            'desired_salary_max': self.desired_salary_max,
            'salary_currency': self.salary_currency,
            'preferred_locations': self.preferred_locations or [],
            'willing_to_relocate': self.willing_to_relocate,
            'needs_visa_sponsorship': self.needs_visa_sponsorship,
            'work_preference': self.work_preference,
            'industries': self.industries or [],
            'company_sizes': self.company_sizes or [],
            'excluded_companies': self.excluded_companies or [],
            'custom_notes': self.custom_notes,
            'onboarding_complete': self.onboarding_complete,
            'onboarding_step': self.onboarding_step,
            'is_premium': self.is_premium or self.subscription_tier in ['premium', 'advantage'],
            'subscription_tier': self.subscription_tier or 'free',
            'subscription_status': getattr(self, 'subscription_status', None),
            'subscription_expires_at': self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
            'has_stripe_subscription': bool(getattr(self, 'stripe_subscription_id', None)),
            'monthly_cv_uploads': self.monthly_cv_uploads or 0,
            'active_persona_id': self.active_persona_id,
            'demo_mode_active': getattr(self, 'demo_mode_active', False) or False
        }
    
    def get_effective_analysis(self):
        """Get CV analysis with profile overrides merged."""
        if not self.cv_analysis:
            return None
        
        analysis = dict(self.cv_analysis)
        
        if self.profile_overrides:
            # Merge overrides into analysis
            for key, value in self.profile_overrides.items():
                if value is not None:
                    analysis[key] = value
        
        return analysis
    
    def get_search_preferences(self):
        """Get preferences formatted for job search."""
        return {
            'locations': self.preferred_locations or [],
            'salary_min': self.desired_salary_min,
            'salary_max': self.desired_salary_max,
            'remote': self.work_preference in ['remote', 'flexible'],
            'visa_sponsorship': self.needs_visa_sponsorship,
            'industries': self.industries or [],
            'ideal_job': self.ideal_job,
            'custom_notes': self.custom_notes
        }


class ChatMessage(db.Model):
    """Chat history with AI assistant."""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    # ENCRYPTED: Chat messages contain personal career discussions
    content = db.Column(EncryptedText(), nullable=False)
    message_metadata = db.Column(EncryptedJSON())  # ENCRYPTED: Extracted preferences
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'metadata': self.message_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CancellationFeedback(db.Model):
    """
    Cancellation feedback from users when they cancel their subscription.
    Used for product improvement and churn analysis.
    """
    __tablename__ = 'cancellation_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reason = db.Column(db.String(100))  # Primary cancellation reason
    # ENCRYPTED: Feedback may contain personal details
    feedback = db.Column(EncryptedText())  # Optional detailed feedback
    tier_cancelled = db.Column(db.String(20))  # Which tier they cancelled from
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('cancellation_feedback', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'reason': self.reason,
            'tier_cancelled': self.tier_cancelled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class JobSearch(db.Model):
    """Job search history and results."""
    __tablename__ = 'job_searches'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_query = db.Column(db.String(255))  # Search query used
    location = db.Column(db.String(255))
    filters = db.Column(db.JSON)  # Applied filters
    results_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending/processing/completed/error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to individual job results
    job_results = db.relationship('JobResult', backref='search', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_results=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': self.id,
            'query': self.search_query,
            'location': self.location,
            'filters': self.filters,
            'results_count': self.results_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_results:
            data['results'] = [r.to_dict() for r in self.job_results.all()]
        return data


class JobResult(db.Model):
    """Individual job result from a search."""
    __tablename__ = 'job_results'
    
    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('job_searches.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Job details
    title = db.Column(db.String(255))
    company = db.Column(db.String(255))
    location = db.Column(db.String(255))
    job_url = db.Column(db.Text)
    description = db.Column(db.Text)
    
    # Match info
    match_reasons = db.Column(db.JSON)
    ats_keywords = db.Column(db.JSON)
    
    # Generated documents
    cv_pdf_path = db.Column(db.String(500))
    cover_letter_pdf_path = db.Column(db.String(500))
    tailored_cv_data = db.Column(db.JSON)
    cover_letter_data = db.Column(db.JSON)
    
    # Source tracking
    source = db.Column(db.String(50), default='google')  # google/linkedin/manual/company_page
    
    # AI Match Analysis
    match_score = db.Column(db.Integer)  # 1-10 realistic score
    honest_assessment = db.Column(db.Text)  # Honest AI feedback about fit
    
    # Status
    applied = db.Column(db.Boolean, default=False)
    applied_at = db.Column(db.DateTime)
    email_sent = db.Column(db.Boolean, default=False)
    
    # Archive status (for AI learning)
    archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime)
    archive_reason = db.Column(db.String(100))  # 'not_qualified', 'salary_low', 'location', 'company', 'already_applied', 'not_interested', 'other'
    archive_feedback = db.Column(db.Text)  # Free text explanation
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'search_id': self.search_id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'job_url': self.job_url,
            'match_reasons': self.match_reasons or [],
            'ats_keywords': self.ats_keywords or [],
            'has_cv_pdf': bool(self.cv_pdf_path),
            'has_cover_letter_pdf': bool(self.cover_letter_pdf_path),
            'source': self.source or 'google',
            'match_score': self.match_score,
            'honest_assessment': self.honest_assessment,
            'applied': self.applied,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'email_sent': self.email_sent,
            'archived': self.archived,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'archive_reason': self.archive_reason,
            'archive_feedback': self.archive_feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TargetCompany(db.Model):
    """Target companies for premium users to monitor."""
    __tablename__ = 'target_companies'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    careers_url = db.Column(db.Text)  # Optional careers page URL
    last_checked = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('target_companies', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'careers_url': self.careers_url,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DailySearchStats(db.Model):
    """Daily statistics for automated job searches."""
    __tablename__ = 'daily_search_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # Search statistics
    total_jobs_scanned = db.Column(db.Integer, default=0)  # Raw jobs found before filtering
    jobs_matched = db.Column(db.Integer, default=0)  # Jobs that passed AI verification
    searches_run = db.Column(db.Integer, default=0)  # Number of search runs today
    
    # Email tracking
    recap_sent = db.Column(db.Boolean, default=False)
    recap_sent_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one stats record per user per day
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if self.date else None,
            'total_jobs_scanned': self.total_jobs_scanned,
            'jobs_matched': self.jobs_matched,
            'searches_run': self.searches_run,
            'recap_sent': self.recap_sent,
            'recap_sent_at': self.recap_sent_at.isoformat() if self.recap_sent_at else None
        }


class GoalSwipe(db.Model):
    """
    Goal preference swipes from onboarding.
    Used for AI training on user preferences.
    """
    __tablename__ = 'goal_swipes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    goal_id = db.Column(db.Integer, nullable=False)  # ID of the goal card
    goal_text = db.Column(db.String(255))  # Text of the goal for reference
    goal_category = db.Column(db.String(100))  # Category (Work Style, Growth, etc.)
    accepted = db.Column(db.Boolean, nullable=True)  # True = swipe right, False = swipe left, None = skipped
    skipped = db.Column(db.Boolean, default=False)  # True if user skipped this card
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('goal_swipes', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'goal_text': self.goal_text,
            'goal_category': self.goal_category,
            'accepted': self.accepted,
            'skipped': self.skipped or False,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Persona(db.Model):
    """
    Multi-CV Personas for premium users.
    Each persona has its own CV, analysis, and AI feedback loop.
    Useful for career changers exploring multiple paths.
    """
    __tablename__ = 'personas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Persona identity
    name = db.Column(db.String(100), nullable=False)  # e.g., "Software Developer", "Product Manager"
    description = db.Column(db.Text)  # Optional description
    color = db.Column(db.String(20), default='#667eea')  # UI accent color
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)  # Primary/default persona
    
    # CV Data (mirrors UserProfile structure) - ENCRYPTED
    cv_filename = db.Column(db.String(255))  # Filename only, not sensitive
    cv_text = db.Column(EncryptedText())  # ENCRYPTED: Full CV text
    cv_analysis = db.Column(EncryptedJSON())  # ENCRYPTED: Parsed CV data
    profile_overrides = db.Column(EncryptedJSON())  # ENCRYPTED: User edits
    
    # Search preferences for this persona - ENCRYPTED where sensitive
    preferred_job_titles = db.Column(EncryptedJSON())  # ENCRYPTED
    preferred_locations = db.Column(EncryptedJSON())  # ENCRYPTED
    target_industries = db.Column(EncryptedJSON())  # ENCRYPTED
    experience_level = db.Column(db.String(50))  # junior/mid/senior/executive - not sensitive
    work_preference = db.Column(db.String(50))  # remote/hybrid/onsite - not sensitive
    
    # Salary expectations - ENCRYPTED
    salary_min = db.Column(EncryptedInteger())  # ENCRYPTED
    salary_max = db.Column(EncryptedInteger())  # ENCRYPTED
    salary_currency = db.Column(db.String(10), default='GBP')  # Not sensitive
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('personas', lazy='dynamic'))
    
    def to_dict(self, include_cv_data=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'has_cv': bool(self.cv_filename),
            'experience_level': self.experience_level,
            'work_preference': self.work_preference,
            'preferred_job_titles': self.preferred_job_titles or [],
            'preferred_locations': self.preferred_locations or [],
            'target_industries': self.target_industries or [],
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'salary_currency': self.salary_currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_cv_data:
            data['cv_analysis'] = self.cv_analysis
            data['profile_overrides'] = self.profile_overrides
        
        return data
    
    def get_effective_analysis(self):
        """Get CV analysis with profile overrides merged."""
        if not self.cv_analysis:
            return None
        
        analysis = dict(self.cv_analysis)
        
        if self.profile_overrides:
            # Merge overrides into analysis
            for key, value in self.profile_overrides.items():
                if value is not None:
                    analysis[key] = value
        
        return analysis
    
    def get_search_preferences(self):
        """Get preferences formatted for job search."""
        return {
            'locations': self.preferred_locations or [],
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'remote': self.work_preference in ['remote', 'flexible'],
            'industries': self.target_industries or [],
            'job_titles': self.preferred_job_titles or [],
            'experience_level': self.experience_level
        }


class SkillsAudit(db.Model):
    """
    Skills audit result for a user when job search returns 0 results.
    Analyzes skill gaps and provides upskilling recommendations.
    """
    __tablename__ = 'skills_audits'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    search_id = db.Column(db.Integer, db.ForeignKey('job_searches.id'), nullable=True)
    
    # Skills analysis (ENCRYPTED - contains career information)
    current_skills = db.Column(EncryptedJSON())  # User's current skills from CV
    target_job_titles = db.Column(EncryptedJSON())  # Job titles searched/matched
    required_skills = db.Column(EncryptedJSON())  # Skills commonly required for target jobs
    skill_gaps = db.Column(EncryptedJSON())  # Missing skills identified
    skill_match_percentage = db.Column(db.Integer)  # Overall match percentage (0-100)
    
    # AI analysis (ENCRYPTED - contains personal career advice)
    analysis_summary = db.Column(EncryptedText())  # AI summary of findings
    recommendations = db.Column(EncryptedJSON())  # Prioritized skill recommendations
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending/processing/completed/error
    error_message = db.Column(db.Text)  # Error details if status is 'error'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('skills_audits', lazy='dynamic'))
    search = db.relationship('JobSearch', backref=db.backref('skills_audit', uselist=False))
    resources = db.relationship('UpskillResource', backref='audit', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_resources=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'search_id': self.search_id,
            'current_skills': self.current_skills or [],
            'target_job_titles': self.target_job_titles or [],
            'required_skills': self.required_skills or [],
            'skill_gaps': self.skill_gaps or [],
            'skill_match_percentage': self.skill_match_percentage,
            'analysis_summary': self.analysis_summary,
            'recommendations': self.recommendations or [],
            'status': self.status,
            'error_message': self.error_message if self.status == 'error' else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_resources:
            data['resources'] = [r.to_dict() for r in self.resources.all()]
        
        return data


class UpskillResource(db.Model):
    """
    Upskilling resource recommendation linked to a skills audit.
    Suggests courses, certifications, tutorials for skill gaps.
    """
    __tablename__ = 'upskill_resources'
    
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('skills_audits.id'), nullable=False)
    
    # Resource details
    skill_name = db.Column(db.String(100), nullable=False)  # Skill this resource teaches
    resource_type = db.Column(db.String(50))  # course/certification/tutorial/bootcamp
    platform = db.Column(db.String(100))  # Coursera, Udemy, LinkedIn Learning, etc.
    
    # ENCRYPTED - may contain location-based pricing or personal recommendations
    title = db.Column(EncryptedText())  # Course/resource title
    url = db.Column(db.Text)  # Link to resource
    description = db.Column(EncryptedText())  # Brief description
    duration = db.Column(db.String(50))  # Estimated completion time
    cost = db.Column(EncryptedText())  # Price info (may vary by region)
    difficulty = db.Column(db.String(20))  # beginner/intermediate/advanced
    priority = db.Column(db.Integer, default=1)  # 1-5, higher = more important
    
    # User interaction
    user_interested = db.Column(db.Boolean)  # User marked as interested
    user_completed = db.Column(db.Boolean, default=False)  # User marked as completed
    completed_at = db.Column(db.DateTime)  # When user marked as completed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'audit_id': self.audit_id,
            'skill_name': self.skill_name,
            'resource_type': self.resource_type,
            'platform': self.platform,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'duration': self.duration,
            'cost': self.cost,
            'difficulty': self.difficulty,
            'priority': self.priority,
            'user_interested': self.user_interested,
            'user_completed': self.user_completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CVBuilderSession(db.Model):
    """
    CV Builder session for users creating a CV from scratch.
    Tracks progress through the conversational CV building process.
    Free feature - will be the only feature available to free users.
    """
    __tablename__ = 'cv_builder_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Session status
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, abandoned
    current_step = db.Column(db.String(50), default='personal_info')  # Current wizard step
    completion_percentage = db.Column(db.Integer, default=0)  # 0-100
    
    # GDPR consent (required before collecting data)
    gdpr_consent_given = db.Column(db.Boolean, default=False)
    gdpr_consent_at = db.Column(db.DateTime)
    gdpr_consent_text = db.Column(db.Text)  # The consent text user agreed to
    
    # Personal Info - ENCRYPTED
    full_name = db.Column(EncryptedText())
    email = db.Column(EncryptedText())
    phone = db.Column(EncryptedText())
    location = db.Column(EncryptedText())
    linkedin_url = db.Column(EncryptedText())
    portfolio_url = db.Column(EncryptedText())
    
    # Professional Summary - ENCRYPTED
    professional_summary = db.Column(EncryptedText())
    career_objective = db.Column(EncryptedText())
    years_experience = db.Column(db.Integer)
    
    # Collected sections (stored as JSON arrays) - ENCRYPTED
    work_experiences = db.Column(EncryptedJSON())  # List of work experience dicts
    educations = db.Column(EncryptedJSON())  # List of education dicts
    skills = db.Column(EncryptedJSON())  # List of skill dicts with proficiency
    certifications = db.Column(EncryptedJSON())  # List of certification dicts
    languages = db.Column(EncryptedJSON())  # List of language dicts with proficiency
    projects = db.Column(EncryptedJSON())  # List of project dicts
    achievements = db.Column(EncryptedJSON())  # List of achievement strings
    interests = db.Column(EncryptedJSON())  # List of interest strings
    references = db.Column(EncryptedJSON())  # List of reference dicts
    
    # Chat history for this session - ENCRYPTED
    chat_history = db.Column(EncryptedJSON())  # List of {role, content} dicts
    
    # AI-generated suggestions and improvements - ENCRYPTED
    ai_suggestions = db.Column(EncryptedJSON())  # AI feedback for improving CV
    
    # Generated CV data
    generated_cv_text = db.Column(EncryptedText())  # Final CV text
    generated_cv_path = db.Column(db.String(500))  # Path to generated PDF
    template_id = db.Column(db.Integer)  # Selected CV template
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('cv_builder_sessions', lazy='dynamic'))
    
    def to_dict(self, include_chat=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': self.id,
            'status': self.status,
            'current_step': self.current_step,
            'completion_percentage': self.completion_percentage,
            'gdpr_consent_given': self.gdpr_consent_given,
            'gdpr_consent_at': self.gdpr_consent_at.isoformat() if self.gdpr_consent_at else None,
            # Personal info
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'linkedin_url': self.linkedin_url,
            'portfolio_url': self.portfolio_url,
            # Professional
            'professional_summary': self.professional_summary,
            'career_objective': self.career_objective,
            'years_experience': self.years_experience,
            # Sections
            'work_experiences': self.work_experiences or [],
            'educations': self.educations or [],
            'skills': self.skills or [],
            'certifications': self.certifications or [],
            'languages': self.languages or [],
            'projects': self.projects or [],
            'achievements': self.achievements or [],
            'interests': self.interests or [],
            'references': self.references or [],
            # Generated
            'has_generated_cv': bool(self.generated_cv_path),
            'template_id': self.template_id,
            'ai_suggestions': self.ai_suggestions or [],
            # Timestamps
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        if include_chat:
            data['chat_history'] = self.chat_history or []
        
        return data
    
    def get_section_counts(self):
        """Get counts of each section for progress tracking."""
        return {
            'work_experiences': len(self.work_experiences or []),
            'educations': len(self.educations or []),
            'skills': len(self.skills or []),
            'certifications': len(self.certifications or []),
            'languages': len(self.languages or []),
            'projects': len(self.projects or []),
            'achievements': len(self.achievements or []),
            'interests': len(self.interests or [])
        }
    
    def calculate_completion(self):
        """Calculate completion percentage based on filled sections."""
        weights = {
            'gdpr_consent': 5,
            'personal_info': 15,  # name, email, phone, location
            'professional_summary': 10,
            'work_experiences': 25,
            'educations': 15,
            'skills': 20,
            'certifications': 5,
            'languages': 5
        }
        
        score = 0
        
        if self.gdpr_consent_given:
            score += weights['gdpr_consent']
        
        # Personal info (check if key fields are filled)
        personal_fields = [self.full_name, self.email, self.location]
        if all(personal_fields):
            score += weights['personal_info']
        elif any(personal_fields):
            score += weights['personal_info'] // 2
        
        if self.professional_summary:
            score += weights['professional_summary']
        
        if self.work_experiences and len(self.work_experiences) > 0:
            score += weights['work_experiences']
        
        if self.educations and len(self.educations) > 0:
            score += weights['educations']
        
        if self.skills and len(self.skills) >= 3:
            score += weights['skills']
        elif self.skills and len(self.skills) > 0:
            score += weights['skills'] // 2
        
        if self.certifications and len(self.certifications) > 0:
            score += weights['certifications']
        
        if self.languages and len(self.languages) > 0:
            score += weights['languages']
        
        self.completion_percentage = min(score, 100)
        return self.completion_percentage


class SystemSettings(db.Model):
    """
    Global system settings stored in database.
    Used for admin-configurable options like AI provider selection.
    """
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    @classmethod
    def get(cls, key: str, default: str = None) -> str:
        """Get a setting value by key."""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set(cls, key: str, value: str, description: str = None, user_id: int = None):
        """Set a setting value, creating if it doesn't exist."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_by = user_id
        else:
            setting = cls(key=key, value=value, description=description, updated_by=user_id)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserSearchLimit(db.Model):
    """
    Track search limits per user with timezone support.
    
    Tier-based limits:
    - Free: 5 searches/month (resets 31 days from first search)
    - Standard: 3 searches/day (resets at midnight local time)
    - Premium: Unlimited
    
    Only counts searches that return at least 1 job result.
    """
    __tablename__ = 'user_search_limits'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)  # User's local date
    timezone = db.Column(db.String(50), default='UTC')  # e.g., 'Europe/London'
    successful_searches = db.Column(db.Integer, default=0)  # Daily count
    
    # Monthly tracking for free tier
    first_search_date = db.Column(db.Date, nullable=True)  # When user's monthly cycle started
    monthly_searches = db.Column(db.Integer, default=0)  # Monthly count for free tier
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one record per user per date
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_search_date'),
    )
    
    # Relationship
    user = db.relationship('User', backref=db.backref('search_limits', lazy='dynamic'))
    
    # Constants
    STANDARD_DAILY_LIMIT = 3
    FREE_MONTHLY_LIMIT = 5
    FREE_CYCLE_DAYS = 31
    
    @classmethod
    def get_today_record(cls, user_id: int, timezone: str = 'UTC'):
        """Get or create today's search limit record for user."""
        from datetime import date
        import pytz
        
        try:
            tz = pytz.timezone(timezone)
            today = datetime.now(tz).date()
        except Exception:
            today = date.today()
        
        record = cls.query.filter_by(user_id=user_id, date=today).first()
        if not record:
            # Get the most recent record to carry over monthly data
            latest = cls.query.filter_by(user_id=user_id).order_by(cls.date.desc()).first()
            
            record = cls(user_id=user_id, date=today, timezone=timezone)
            
            # Carry over monthly tracking from previous record
            if latest:
                record.first_search_date = latest.first_search_date
                record.monthly_searches = latest.monthly_searches
            
            db.session.add(record)
            db.session.commit()
        return record
    
    @classmethod
    def should_reset_monthly(cls, first_search_date, timezone: str = 'UTC') -> bool:
        """Check if monthly limit should reset (31 days have passed)."""
        if not first_search_date:
            return False
        
        from datetime import date
        import pytz
        
        try:
            tz = pytz.timezone(timezone)
            today = datetime.now(tz).date()
        except Exception:
            today = date.today()
        
        days_since = (today - first_search_date).days
        return days_since >= cls.FREE_CYCLE_DAYS
    
    @classmethod
    def get_remaining_searches(cls, user_id: int, timezone: str = 'UTC', tier: str = 'free') -> dict:
        """
        Get remaining searches based on tier.
        
        Returns dict with:
        - remaining: number of searches left (-1 for unlimited)
        - limit: the limit value
        - used: searches used in current period
        - is_unlimited: whether searches are unlimited
        - limit_type: 'daily', 'monthly', or 'unlimited'
        - resets_at: when the limit resets (ISO string or None)
        """
        from subscription_config import normalize_tier
        import pytz
        
        tier = normalize_tier(tier)
        
        # Premium: unlimited
        if tier == 'premium':
            return {
                'remaining': -1,
                'limit': -1,
                'used': 0,
                'is_unlimited': True,
                'limit_type': 'unlimited',
                'resets_at': None
            }
        
        record = cls.get_today_record(user_id, timezone)
        
        # Standard: daily limit
        if tier == 'standard':
            remaining = max(0, cls.STANDARD_DAILY_LIMIT - record.successful_searches)
            
            # Calculate reset time (midnight local time)
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
                tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                resets_at = tomorrow.isoformat()
            except Exception:
                resets_at = None
            
            return {
                'remaining': remaining,
                'limit': cls.STANDARD_DAILY_LIMIT,
                'used': record.successful_searches,
                'is_unlimited': False,
                'limit_type': 'daily',
                'resets_at': resets_at
            }
        
        # Free: monthly limit
        # Check if monthly cycle should reset
        if cls.should_reset_monthly(record.first_search_date, timezone):
            record.first_search_date = None
            record.monthly_searches = 0
            db.session.commit()
        
        remaining = max(0, cls.FREE_MONTHLY_LIMIT - record.monthly_searches)
        
        # Calculate reset time (31 days from first search)
        resets_at = None
        if record.first_search_date:
            reset_date = record.first_search_date + timedelta(days=cls.FREE_CYCLE_DAYS)
            resets_at = reset_date.isoformat()
        
        return {
            'remaining': remaining,
            'limit': cls.FREE_MONTHLY_LIMIT,
            'used': record.monthly_searches,
            'is_unlimited': False,
            'limit_type': 'monthly',
            'resets_at': resets_at
        }
    
    @classmethod
    def increment_search_count(cls, user_id: int, timezone: str = 'UTC', tier: str = 'free'):
        """
        Increment successful search count. Called when search returns ≥1 job.
        Updates both daily count (for standard) and monthly count (for free).
        """
        from subscription_config import normalize_tier
        from datetime import date
        import pytz
        
        tier = normalize_tier(tier)
        
        # Premium users don't need tracking
        if tier == 'premium':
            return 0
        
        record = cls.get_today_record(user_id, timezone)
        
        # Standard tier: increment daily count
        if tier == 'standard':
            record.successful_searches += 1
            db.session.commit()
            return record.successful_searches
        
        # Free tier: increment monthly count
        # Check if monthly cycle should reset first
        if cls.should_reset_monthly(record.first_search_date, timezone):
            record.first_search_date = None
            record.monthly_searches = 0
        
        # Set first search date if not set
        if not record.first_search_date:
            try:
                tz = pytz.timezone(timezone)
                today = datetime.now(tz).date()
            except Exception:
                today = date.today()
            record.first_search_date = today
        
        record.monthly_searches += 1
        db.session.commit()
        return record.monthly_searches
    
    @classmethod
    def can_search(cls, user_id: int, timezone: str = 'UTC', tier: str = 'free') -> tuple:
        """
        Check if user can perform a search.
        
        Returns: (can_search, remaining, message)
        """
        from subscription_config import normalize_tier
        
        tier = normalize_tier(tier)
        
        # Premium: always allowed
        if tier == 'premium':
            return True, -1, None
        
        limit_info = cls.get_remaining_searches(user_id, timezone, tier)
        remaining = limit_info['remaining']
        
        # Standard tier: daily limit
        if tier == 'standard':
            if remaining <= 0:
                return False, 0, "You've used all 3 searches for today. Upgrade to Premium for unlimited searches!"
            if remaining == 1:
                return True, 1, "This is your last search for today."
            return True, remaining, None
        
        # Free tier: monthly limit
        if remaining <= 0:
            return False, 0, "You've used all 5 searches this month. Upgrade to Standard for daily searches or Premium for unlimited!"
        if remaining == 1:
            return True, 1, "This is your last search this month."
        return True, remaining, None
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if self.date else None,
            'timezone': self.timezone,
            'successful_searches': self.successful_searches,
            'first_search_date': self.first_search_date.isoformat() if self.first_search_date else None,
            'monthly_searches': self.monthly_searches,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InterviewPrepSession(db.Model):
    """
    Interview preparation session for a job application.
    AI-powered mock interview with 10 questions and scoring.
    Available for Standard and Premium tiers.
    """
    __tablename__ = 'interview_prep_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_result_id = db.Column(db.Integer, db.ForeignKey('job_results.id'), nullable=False, index=True)
    
    # Session status
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, abandoned
    current_question = db.Column(db.Integer, default=0)  # 0-9 for 10 questions
    
    # Questions and answers (ENCRYPTED - contains interview content)
    questions = db.Column(EncryptedJSON())  # List of 10 AI-generated questions
    answers = db.Column(EncryptedJSON())  # List of user's answers
    
    # AI Scoring and Feedback (ENCRYPTED)
    question_scores = db.Column(EncryptedJSON())  # Score per question (1-10)
    question_feedback = db.Column(EncryptedJSON())  # Feedback per question
    overall_score = db.Column(db.Integer)  # 1-100 overall score
    overall_feedback = db.Column(EncryptedText())  # Final comprehensive feedback
    strengths = db.Column(EncryptedJSON())  # List of identified strengths
    areas_to_improve = db.Column(EncryptedJSON())  # List of areas to work on
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('interview_prep_sessions', lazy='dynamic'))
    job_result = db.relationship('JobResult', backref=db.backref('interview_prep_sessions', lazy='dynamic'))
    
    def to_dict(self, include_details=True):
        """Convert to dictionary for API responses."""
        data = {
            'id': self.id,
            'job_result_id': self.job_result_id,
            'status': self.status,
            'current_question': self.current_question,
            'overall_score': self.overall_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        if include_details:
            data.update({
                'questions': self.questions or [],
                'answers': self.answers or [],
                'question_scores': self.question_scores or [],
                'question_feedback': self.question_feedback or [],
                'overall_feedback': self.overall_feedback,
                'strengths': self.strengths or [],
                'areas_to_improve': self.areas_to_improve or []
            })
        
        return data


class RecruiterContact(db.Model):
    """
    Recruiter/Hiring Manager contact information for a job application.
    Premium feature only - stores publicly available business contact info.
    """
    __tablename__ = 'recruiter_contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_result_id = db.Column(db.Integer, db.ForeignKey('job_results.id'), nullable=False, index=True)
    
    # Company info (user-confirmed)
    company_name = db.Column(db.String(255), nullable=False)
    company_name_confirmed = db.Column(db.Boolean, default=False)
    
    # Contact info (ENCRYPTED - contains PII)
    recruiter_name = db.Column(EncryptedText())
    recruiter_email = db.Column(EncryptedText())  # Business email only
    recruiter_position = db.Column(EncryptedText())
    linkedin_url = db.Column(EncryptedText())
    
    # Search metadata
    search_source = db.Column(db.String(50))  # 'linkedin', 'company_website', 'google', etc.
    confidence_score = db.Column(db.Integer)  # 1-100, how confident we are this is correct
    
    # User actions
    contacted = db.Column(db.Boolean, default=False)
    contacted_at = db.Column(db.DateTime)
    follow_up_sent = db.Column(db.Boolean, default=False)
    follow_up_sent_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('recruiter_contacts', lazy='dynamic'))
    job_result = db.relationship('JobResult', backref=db.backref('recruiter_contacts', lazy='dynamic'))
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'job_result_id': self.job_result_id,
            'company_name': self.company_name,
            'company_name_confirmed': self.company_name_confirmed,
            'recruiter_name': self.recruiter_name,
            'recruiter_email': self.recruiter_email,
            'recruiter_position': self.recruiter_position,
            'linkedin_url': self.linkedin_url,
            'search_source': self.search_source,
            'confidence_score': self.confidence_score,
            'contacted': self.contacted,
            'contacted_at': self.contacted_at.isoformat() if self.contacted_at else None,
            'follow_up_sent': self.follow_up_sent,
            'follow_up_sent_at': self.follow_up_sent_at.isoformat() if self.follow_up_sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ApplicationChaseUp(db.Model):
    """
    Track chase-up reminders for job applications.
    Sends email reminder 10 days after marking as applied.
    """
    __tablename__ = 'application_chase_ups'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_result_id = db.Column(db.Integer, db.ForeignKey('job_results.id'), nullable=False, unique=True)
    
    # Chase-up status
    reminder_due_at = db.Column(db.DateTime, nullable=False)  # applied_at + 10 days
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime)
    
    # User response
    dismissed = db.Column(db.Boolean, default=False)  # User chose not to chase up
    dismissed_at = db.Column(db.DateTime)
    chase_up_completed = db.Column(db.Boolean, default=False)  # User sent follow-up
    chase_up_completed_at = db.Column(db.DateTime)
    
    # Generated follow-up content (ENCRYPTED)
    generated_email_subject = db.Column(EncryptedText())
    generated_email_body = db.Column(EncryptedText())
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('application_chase_ups', lazy='dynamic'))
    job_result = db.relationship('JobResult', backref=db.backref('chase_up', uselist=False))
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'job_result_id': self.job_result_id,
            'reminder_due_at': self.reminder_due_at.isoformat() if self.reminder_due_at else None,
            'reminder_sent': self.reminder_sent,
            'reminder_sent_at': self.reminder_sent_at.isoformat() if self.reminder_sent_at else None,
            'dismissed': self.dismissed,
            'chase_up_completed': self.chase_up_completed,
            'generated_email_subject': self.generated_email_subject,
            'generated_email_body': self.generated_email_body,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    with app.app_context():
        # Import customizer models to ensure their tables are created
        from customizer_models import (
            CustomizedDocument,
            DocumentEdit,
            UserWritingPreferences,
            CVTemplate,
            init_default_templates
        )
        
        db.create_all()
        
        # Initialize default CV templates if they don't exist
        try:
            init_default_templates()
        except Exception as e:
            print(f"[DB] Note: Template initialization: {e}")



