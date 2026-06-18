# models.py – SQLAlchemy ORM models and Flask-Login user loader
from flask_login import UserMixin
from extensions import db, login_manager

# --- MODELS ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(100), unique=True, nullable=True)   # nullable: Google users may not have one
    email        = db.Column(db.String(255), unique=True, nullable=True)
    display_name = db.Column(db.String(255), nullable=True)
    is_active    = db.Column(db.Boolean, default=True, nullable=False)
    is_admin     = db.Column(db.Boolean, default=False, nullable=False)
    credits      = db.Column(db.Integer, default=5, nullable=False)        # credits (câu hỏi), mặc định 5 dùng thử
    created_at   = db.Column(db.DateTime, default=db.func.now())
    terms_agreed_at = db.Column(db.DateTime, nullable=True)                # NULL = chưa đồng ý điều khoản

    # Relationship to auth providers
    auth_providers = db.relationship('UserAuthProvider', backref='user', lazy='dynamic')

    @property
    def display(self):
        """Best available display name: display_name > username > email prefix."""
        if self.display_name:
            return self.display_name
        if self.username:
            return self.username
        if self.email:
            return self.email.split('@')[0]
        return f'User {self.id}'

    @property
    def has_google_auth(self):
        """True if user linked Google login (query trực tiếp, tránh lazy-load lỗi session)."""
        try:
            uid = self.id
        except Exception:
            return False
        return db.session.query(UserAuthProvider.id).filter_by(
            user_id=uid, provider='google'
        ).first() is not None

class UserAuthProvider(db.Model):
    """One row per (user, provider) pair.
    provider = 'local' → password_hash is used.
    provider = 'google' → provider_user_id (Google sub) is used.
    """
    __tablename__ = 'user_auth_providers'
    id                 = db.Column(db.Integer, primary_key=True)
    user_id            = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider           = db.Column(db.String(50), nullable=False)        # 'local' | 'google'
    provider_user_id   = db.Column(db.String(255), nullable=True)        # Google sub
    provider_email     = db.Column(db.String(255), nullable=True)        # email from provider
    password_hash      = db.Column(db.String(255), nullable=True)        # only for local
    created_at         = db.Column(db.DateTime, default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user'),
    )

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255))
    content = db.Column(db.Text)  # Nội dung PDF đã trích xuất
    upload_date = db.Column(db.DateTime, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class QAResult(db.Model):
    __tablename__ = 'qa_results'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    question = db.Column(db.Text)
    answer = db.Column(db.Text)
    bloom_level = db.Column(db.String(50))
    algorithm = db.Column(db.String(50))
    process_time = db.Column(db.Float)
    section_mapping = db.Column(db.String(500))  # Lưu thông tin mục được sử dụng
    total_points = db.Column(db.Float, default=0)  # Tổng điểm của câu hỏi
    sub_points_count = db.Column(db.Integer, default=0)  # Số ý (mỗi ý 0.25 điểm)
    points_breakdown = db.Column(db.Text)  # Chi tiết điểm từng ý
    batch_id = db.Column(db.String(20), nullable=True)  # ID nhóm lần sinh (YYYYMMDDHHMMSS)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))  # Liên kết với Document

# --- AGENT EVALUATION LOG MODELS ---
class Agent1EvaluationLog(db.Model):
    __tablename__ = 'agent1_evaluation_logs'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    source_type = db.Column(db.String(32))
    attempt = db.Column(db.Integer, default=1)
    extraction_method = db.Column(db.String(32))
    decision = db.Column(db.String(16), nullable=False)
    terminal_status = db.Column(db.String(32))
    quality_score = db.Column(db.Float, default=0)
    reasons_json = db.Column(db.Text, nullable=False)
    metrics_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Agent2EvaluationLog(db.Model):
    __tablename__ = 'agent2_evaluation_logs'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    attempt = db.Column(db.Integer, default=1)
    decision = db.Column(db.String(16), nullable=False)
    terminal_status = db.Column(db.String(32))
    quality_score = db.Column(db.Float, default=0)
    reasons_json = db.Column(db.Text, nullable=False)
    structure_summary_json = db.Column(db.Text)
    plan_summary_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Agent3EvaluationLog(db.Model):
    __tablename__ = 'agent3_evaluation_logs'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    plan_item_id = db.Column(db.String(64))
    attempt = db.Column(db.Integer, default=1)
    decision = db.Column(db.String(16), nullable=False)
    terminal_status = db.Column(db.String(32))
    quality_score = db.Column(db.Float, default=0)
    reasons_json = db.Column(db.Text, nullable=False)
    target_bloom = db.Column(db.String(32))
    generated_bloom = db.Column(db.String(32))
    validated_bloom = db.Column(db.String(32))
    bloom_match_type = db.Column(db.String(32))
    source_faithfulness_score = db.Column(db.Float, default=0)
    scoreability_score = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())

# --- PAYMENT MODELS ---
class CreditPackage(db.Model):
    """Các gói credit có thể mua."""
    __tablename__ = 'credit_packages'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)    # "Starter", "Standard", ...
    credits     = db.Column(db.Integer, nullable=False)        # số câu hỏi
    price_vnd   = db.Column(db.Integer, nullable=False)        # giá VNĐ
    is_active   = db.Column(db.Boolean, default=True)
    is_popular  = db.Column(db.Boolean, default=False)         # highlight "Phổ biến"

class SubscriptionPackage(db.Model):
    """Các gói thuê bao tháng."""
    __tablename__ = 'subscription_packages'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    credits    = db.Column(db.Integer, nullable=False)
    price_vnd  = db.Column(db.Integer, nullable=False)
    period     = db.Column(db.String(20), default='tháng')   # tháng / năm
    is_active  = db.Column(db.Boolean, default=True)

class Transaction(db.Model):
    """Lịch sử giao dịch mua credit."""
    __tablename__ = 'transactions'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    package_id      = db.Column(db.Integer, db.ForeignKey('credit_packages.id'), nullable=True)
    sub_package_id  = db.Column(db.Integer, db.ForeignKey('subscription_packages.id'), nullable=True)
    order_code      = db.Column(db.String(64), unique=True, nullable=False)  # mã PayOS
    amount_vnd      = db.Column(db.Integer, nullable=False)
    credits_added   = db.Column(db.Integer, nullable=False)
    status          = db.Column(db.String(20), default='pending')  # pending|paid|cancelled|failed
    payment_method  = db.Column(db.String(50), nullable=True)      # bank_transfer|momo|...
    payos_data      = db.Column(db.Text, nullable=True)            # raw JSON từ PayOS webhook
    created_at      = db.Column(db.DateTime, default=db.func.now())
    paid_at         = db.Column(db.DateTime, nullable=True)

    user         = db.relationship('User', backref=db.backref('transactions', lazy='dynamic'))
    package      = db.relationship('CreditPackage', backref=db.backref('transactions', lazy='dynamic'))
    sub_package  = db.relationship('SubscriptionPackage', backref=db.backref('transactions', lazy='dynamic'))

class Feedback(db.Model):
    """Phản hồi từ người dùng gửi qua form trên landing page."""
    __tablename__ = 'feedbacks'
    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(255), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    is_read    = db.Column(db.Boolean, default=False, nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', backref=db.backref('feedbacks', lazy='dynamic'))


@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)


# --- SYSTEM SETTINGS ---
class SystemSetting(db.Model):
    """Key-value store for runtime admin settings."""
    __tablename__ = 'system_settings'
    key   = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @staticmethod
    def get(key, default=''):
        row = SystemSetting.query.get(key)
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = SystemSetting.query.get(key)
        if row:
            row.value = str(value)
        else:
            db.session.add(SystemSetting(key=key, value=str(value)))
        db.session.commit()
