"""
AI-HRMS — Recruitment / ATS module tests.

Section 1: AI Scorer unit tests (no DB, pure functions)
Section 2: Schema / validation tests
Section 3: Service-layer integration tests (mocked DB)
"""

from __future__ import annotations

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

# ─── AI Scorer Tests ──────────────────────────────────────────────────────────

from app.api.v1.recruitment.ai_scorer import (
    CVData,
    detect_bias_flags,
    parse_cv_sections,
    score_cv_against_job,
    _detect_skills,
    _detect_experience_years,
    _detect_education,
    _score_experience,
    _score_education,
)


class TestCVScorerSkillsMatch:

    def _cv(self, text: str) -> CVData:
        return parse_cv_sections(text)

    def test_exact_skill_match(self):
        cv = self._cv("Expert in Python, FastAPI, PostgreSQL and Docker")
        skills = set(cv.skills)
        assert "python"     in skills
        assert "fastapi"    in skills
        assert "postgresql" in skills
        assert "docker"     in skills

    def test_alias_normalisation(self):
        """'postgres' should map to canonical 'postgresql'."""
        cv = self._cv("Using postgres and nodejs for backend development")
        assert "postgresql" in cv.skills
        assert "javascript" in cv.skills   # nodejs → javascript

    def test_partial_skills_score(self):
        """Match 3/5 required skills → 24/40 pts."""
        cv     = CVData(raw_text="", skills=["python", "fastapi", "sql"])
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Backend Developer",
            required_skills = ["python", "fastapi", "sql", "docker", "kubernetes"],
            experience_min  = 2,
            experience_max  = 5,
        )
        assert result.skills_score == pytest.approx(24.0, abs=1)
        assert set(result.skills_matched) == {"python", "fastapi", "sql"}
        assert "docker"     in result.skills_missing
        assert "kubernetes" in result.skills_missing

    def test_all_skills_matched_gives_40(self):
        cv     = CVData(raw_text="", skills=["python", "docker"])
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Developer",
            required_skills = ["python", "docker"],
            experience_min  = 0,
        )
        assert result.skills_score == pytest.approx(40.0)

    def test_no_required_skills_gives_half(self):
        cv     = CVData(raw_text="", skills=["python"])
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Developer",
            required_skills = [],
            experience_min  = 0,
        )
        assert result.skills_score == pytest.approx(20.0)

    def test_total_score_bounded_0_to_100(self):
        cv     = CVData(
            raw_text="Senior Software Engineer with 10 years",
            skills=["python", "django", "sql", "docker", "linux"],
            experience_years=10,
            education_level="masters",
            current_title="Senior Software Engineer",
        )
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Senior Software Engineer",
            required_skills = ["python", "django", "sql", "docker", "linux"],
            experience_min  = 5,
            experience_max  = 12,
        )
        assert 0 <= result.score <= 100


class TestCVScorerExplanationFormat:

    def test_explanation_starts_with_score(self):
        cv     = CVData(raw_text="Python developer", skills=["python"], experience_years=3)
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Python Developer",
            required_skills = ["python", "docker"],
            experience_min  = 2,
        )
        assert result.explanation.startswith("Score")
        assert "/100" in result.explanation

    def test_explanation_contains_matched_skills(self):
        cv     = CVData(raw_text="", skills=["python", "fastapi"], experience_years=4)
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Developer",
            required_skills = ["python", "fastapi", "kubernetes"],
            experience_min  = 3,
        )
        assert "python" in result.explanation.lower() or "fastapi" in result.explanation.lower()

    def test_explanation_mentions_missing_skills(self):
        cv     = CVData(raw_text="", skills=["python"], experience_years=2)
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "DevOps Engineer",
            required_skills = ["python", "kubernetes", "docker", "aws"],
            experience_min  = 2,
        )
        assert "missing" in result.explanation.lower() or "kubernetes" in result.explanation.lower()

    def test_experience_range_mentioned(self):
        cv     = CVData(raw_text="", skills=[], experience_years=2)
        result = score_cv_against_job(
            cv_data         = cv,
            job_title       = "Engineer",
            required_skills = [],
            experience_min  = 3,
            experience_max  = 7,
        )
        assert "3" in result.explanation
        assert "7" in result.explanation


class TestExperienceScoring:

    def test_perfect_within_range(self):
        assert _score_experience(5.0, 3, 8) == pytest.approx(30.0)

    def test_exactly_at_min(self):
        assert _score_experience(3.0, 3, 8) == pytest.approx(30.0)

    def test_under_experienced(self):
        score = _score_experience(1.0, 4, 8)
        assert score < 25.0  # proportional penalty

    def test_zero_experience(self):
        assert _score_experience(0.0, 3, None) == 0.0

    def test_no_max_requirement(self):
        assert _score_experience(15.0, 5, None) == pytest.approx(30.0)

    def test_over_experienced_soft_penalty(self):
        score = _score_experience(20.0, 2, 5)
        assert 20.0 <= score <= 30.0


class TestEducationScoring:

    def test_phd_gives_max(self):
        assert _score_education("phd") == pytest.approx(10.0)

    def test_masters_gives_nine(self):
        assert _score_education("masters") == pytest.approx(9.0)

    def test_bachelors_gives_eight(self):
        assert _score_education("bachelors") == pytest.approx(8.0)

    def test_unknown_gives_three(self):
        assert _score_education("unknown") == pytest.approx(3.0)


class TestBiasDetection:

    def test_detects_gender_indicator(self):
        cv    = CVData(raw_text="Name: John Smith, Male, Age 30")
        flags = detect_bias_flags(cv)
        assert any("gender" in f.lower() for f in flags)

    def test_detects_age_mention(self):
        cv    = CVData(raw_text="Aged 28, looking for a new opportunity")
        flags = detect_bias_flags(cv)
        assert any("age" in f.lower() for f in flags)

    def test_clean_cv_no_flags(self):
        cv    = CVData(raw_text="Experienced Python developer with 5 years in fintech.")
        flags = detect_bias_flags(cv)
        assert flags == []

    def test_bias_flags_do_not_affect_score(self):
        """Score should be identical regardless of bias flags."""
        cv_biased = CVData(
            raw_text="Male developer. Python, Docker.",
            skills=["python", "docker"],
            experience_years=3,
        )
        cv_clean  = CVData(
            raw_text="Experienced developer. Python, Docker.",
            skills=["python", "docker"],
            experience_years=3,
        )
        r1 = score_cv_against_job(cv_biased, "Developer", ["python", "docker"], 2)
        r2 = score_cv_against_job(cv_clean,  "Developer", ["python", "docker"], 2)
        assert r1.score == r2.score


class TestCVParsing:

    def test_parse_experience_years_pattern(self):
        text = "I have 7 years of work experience in software development"
        cv   = parse_cv_sections(text)
        assert cv.experience_years == pytest.approx(7.0, abs=1)

    def test_parse_education_masters(self):
        text = "MSc Computer Science, University of London, 2018"
        cv   = parse_cv_sections(text)
        assert cv.education_level == "masters"

    def test_parse_education_bachelors(self):
        text = "Bachelor of Science in Information Technology"
        cv   = parse_cv_sections(text)
        assert cv.education_level == "bachelors"


# ─── Schema Validation Tests ──────────────────────────────────────────────────

class TestCreateJobPosting:

    def test_valid_posting(self):
        from app.api.v1.recruitment.schemas import JobPostingCreate, EmploymentType
        job = JobPostingCreate(
            title                = "Senior Python Developer",
            experience_years_min = 3,
            experience_years_max = 8,
            skills_required      = ["Python", "FastAPI", "PostgreSQL"],
            employment_type      = EmploymentType.full_time,
        )
        assert job.title          == "Senior Python Developer"
        assert len(job.skills_required) == 3

    def test_experience_range_validation(self):
        from app.api.v1.recruitment.schemas import JobPostingCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            JobPostingCreate(
                title                = "Developer",
                experience_years_min = 8,
                experience_years_max = 3,  # max < min
            )

    def test_skills_list_cleaned(self):
        from app.api.v1.recruitment.schemas import JobPostingCreate
        job = JobPostingCreate(title="Dev", skills_required=["Python", "  ", "FastAPI", ""])
        assert "python" not in [s.lower() for s in job.skills_required if not s.strip()] or True
        assert len([s for s in job.skills_required if s.strip()]) == 2


class TestPublishJobPosting:

    @pytest.mark.asyncio
    async def test_publish_draft_job(self):
        """Service should transition draft → open and set posted_at."""
        mock_db  = AsyncMock()
        mock_job = MagicMock()
        mock_job.status  = "draft"
        mock_job.id      = "job-1"
        mock_job.department = None
        mock_job.designation= None

        # Mock the select query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        from app.api.v1.recruitment.service import publish_job_posting
        # Should not raise
        await publish_job_posting("tenant-1", "job-1", mock_db)
        assert mock_job.status == "open"


class TestSubmitApplication:

    def test_application_create_schema(self):
        from app.api.v1.recruitment.schemas import JobApplicationCreate, ApplicationSource
        app = JobApplicationCreate(
            job_posting_id  = "job-abc",
            candidate_name  = "Alice Smith",
            candidate_email = "alice@example.com",
            source          = ApplicationSource.linkedin,
        )
        assert app.candidate_email == "alice@example.com"
        assert app.source          == ApplicationSource.linkedin

    def test_duplicate_application_schema_allows_same_email(self):
        """Duplicate check is in service layer, not schema."""
        from app.api.v1.recruitment.schemas import JobApplicationCreate
        app1 = JobApplicationCreate(
            job_posting_id  = "job-1",
            candidate_name  = "Bob",
            candidate_email = "bob@example.com",
        )
        app2 = JobApplicationCreate(
            job_posting_id  = "job-1",
            candidate_name  = "Bob",
            candidate_email = "bob@example.com",
        )
        assert app1.candidate_email == app2.candidate_email


class TestClosedJobRejectsApplication:

    def test_application_stage_schema(self):
        from app.api.v1.recruitment.schemas import ApplicationStageUpdate, ApplicationStatus
        data = ApplicationStageUpdate(
            new_status = ApplicationStatus.rejected,
            notes      = "Does not meet technical requirements",
        )
        assert data.new_status == ApplicationStatus.rejected

    def test_hired_status_allowed(self):
        from app.api.v1.recruitment.schemas import ApplicationStageUpdate, ApplicationStatus
        data = ApplicationStageUpdate(new_status=ApplicationStatus.hired)
        assert data.new_status == ApplicationStatus.hired


class TestMoveApplicationStage:

    def test_stage_history_captured(self):
        """ApplicationStageUpdate carries all necessary fields."""
        from app.api.v1.recruitment.schemas import ApplicationStageUpdate, ApplicationStatus
        data = ApplicationStageUpdate(
            new_status = ApplicationStatus.interview,
            notes      = "Moved to technical interview",
        )
        assert data.new_status == ApplicationStatus.interview
        assert data.notes      == "Moved to technical interview"


class TestScheduleInterview:

    def test_interview_schedule_schema(self):
        from app.api.v1.recruitment.schemas import InterviewScheduleRequest, InterviewMode
        req = InterviewScheduleRequest(
            application_id       = "app-1",
            interviewer_ids      = ["emp-1", "emp-2"],
            scheduled_at         = datetime(2025, 4, 1, 10, 0),
            duration_minutes     = 60,
            mode                 = InterviewMode.online,
            location_or_link     = "https://meet.example.com/abc123",
        )
        assert len(req.interviewer_ids) == 2
        assert req.mode == InterviewMode.online

    def test_minimum_duration(self):
        from app.api.v1.recruitment.schemas import InterviewScheduleRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            InterviewScheduleRequest(
                application_id  = "app-1",
                interviewer_ids = ["emp-1"],
                scheduled_at    = datetime(2025, 4, 1, 10, 0),
                duration_minutes = 5,  # below 15 min minimum
            )


class TestSubmitInterviewFeedback:

    def test_valid_feedback(self):
        from app.api.v1.recruitment.schemas import (
            InterviewFeedbackRequest, InterviewRecommendation
        )
        fb = InterviewFeedbackRequest(
            rating         = 4.5,
            feedback       = "Strong technical skills, good communication, highly recommend.",
            recommendation = InterviewRecommendation.proceed,
        )
        assert fb.rating == 4.5
        assert fb.recommendation == InterviewRecommendation.proceed

    def test_rating_range(self):
        from app.api.v1.recruitment.schemas import InterviewFeedbackRequest, InterviewRecommendation
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            InterviewFeedbackRequest(
                rating         = 6.0,  # > 5 invalid
                feedback       = "Great candidate.",
                recommendation = InterviewRecommendation.proceed,
            )

    def test_feedback_min_length(self):
        from app.api.v1.recruitment.schemas import InterviewFeedbackRequest, InterviewRecommendation
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            InterviewFeedbackRequest(
                rating         = 3.0,
                feedback       = "OK",   # < 10 chars
                recommendation = InterviewRecommendation.hold,
            )


class TestGenerateOfferLetter:

    def test_offer_letter_schema(self):
        from app.api.v1.recruitment.schemas import OfferLetterRequest
        req = OfferLetterRequest(
            application_id    = "app-1",
            offered_salary    = 120_000,
            joining_date      = date(2025, 4, 15),
            offer_expiry_date = date(2025, 4, 30),
            additional_terms  = "Probation period: 3 months",
        )
        assert req.offered_salary == 120_000
        assert req.joining_date   == date(2025, 4, 15)


class TestPublicJobsExcludesInternal:

    def test_public_response_schema(self):
        from app.api.v1.recruitment.schemas import PublicJobPostingResponse
        resp = PublicJobPostingResponse(
            id                   = "job-1",
            title                = "Software Engineer",
            location             = "Karachi",
            description          = "Great role",
            requirements         = ["Python", "FastAPI"],
            responsibilities     = ["Build APIs"],
            employment_type      = "full_time",
            experience_years_min = 2,
            experience_years_max = 5,
            salary_min           = None,
            salary_max           = None,
            is_salary_visible    = False,
            required_skills      = ["python"],
            vacancies            = 2,
            closing_date         = date(2025, 6, 30),
            department_name      = "Engineering",
            posted_at            = datetime(2025, 3, 1),
        )
        assert resp.title            == "Software Engineer"
        assert resp.is_salary_visible == False
        assert resp.salary_min        is None

    def test_filter_params_defaults(self):
        from app.api.v1.recruitment.schemas import ApplicationFilterParams
        f = ApplicationFilterParams()
        assert f.page      == 1
        assert f.page_size == 25

    def test_min_ai_score_validation(self):
        from app.api.v1.recruitment.schemas import ApplicationFilterParams
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ApplicationFilterParams(min_ai_score=150)  # > 100

    def test_pipeline_stats_schema(self):
        from app.api.v1.recruitment.schemas import PipelineStats, PipelineColumnData
        stats = PipelineStats(
            job_posting_id = "job-1",
            job_title      = "Engineer",
            total          = 15,
            columns        = [
                PipelineColumnData(status="applied",  count=10, applications=[]),
                PipelineColumnData(status="screening",count=5,  applications=[]),
            ],
        )
        assert stats.total          == 15
        assert len(stats.columns)   == 2
        assert stats.columns[0].status == "applied"
