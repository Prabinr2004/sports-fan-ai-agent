from app.models.prediction import UserMatchPrediction
from app.models.quiz import DailyQuizSnapshot


def test_prediction_result_columns_are_registered():
    columns = UserMatchPrediction.__table__.columns
    assert "actual_outcome" in columns
    assert "result_status" in columns
    assert "home_score" in columns
    assert "away_score" in columns
    assert "result_checked_at" in columns


def test_daily_quiz_snapshot_columns_are_registered():
    columns = DailyQuizSnapshot.__table__.columns
    assert "quiz_date" in columns
    assert "level" in columns
    assert "theme" in columns
    assert "questions_json" in columns
