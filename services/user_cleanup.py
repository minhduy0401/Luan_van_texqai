"""Delete a user account and all related data (respecting FK order)."""
from extensions import db
from models import (
    User,
    Document,
    QAResult,
    Transaction,
    UserAuthProvider,
    Feedback,
    Agent1EvaluationLog,
    Agent2EvaluationLog,
    Agent3EvaluationLog,
)


def delete_user_account(user_id: int) -> str:
    """
    Permanently delete a user and associated rows.
    Returns the user's display name before deletion.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError('user_not_found')

    name = user.display
    doc_ids = [
        row[0]
        for row in db.session.query(Document.id).filter_by(user_id=user_id).all()
    ]

    QAResult.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    if doc_ids:
        QAResult.query.filter(QAResult.document_id.in_(doc_ids)).delete(synchronize_session=False)

    for model in (Agent1EvaluationLog, Agent2EvaluationLog, Agent3EvaluationLog):
        model.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        if doc_ids:
            model.query.filter(model.document_id.in_(doc_ids)).delete(synchronize_session=False)

    Transaction.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Feedback.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Document.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    UserAuthProvider.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    db.session.delete(user)
    db.session.commit()
    return name
