from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import random
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import (User, TestSession, Question, Submission, Result,
    StudentProfile, CategoryEnum, DomainEnum, TechnologyEnum, EligibilityStatusEnum, DifficultyEnum)
from app.schemas.schemas import StartTestRequest, SubmitTestRequest

router = APIRouter()

CATEGORY_MAP = {
    "profile_fit": None,
    "it_technical": CategoryEnum.IT,
    "management": CategoryEnum.MANAGEMENT,
    "non_it": CategoryEnum.NON_IT,
    "hr": CategoryEnum.HR,
    "finance": CategoryEnum.FINANCE,
    "creative": CategoryEnum.CREATIVE,
    "engineering": CategoryEnum.ENGINEERING,
}

DURATION_MAP = {
    "profile_fit": 45,
    "it_technical": 50,
    "management": 45,
    "non_it": 40,
    "hr": 35,
    "finance": 45,
    "creative": 35,
    "engineering": 45,
}

def get_questions_for_test(db: Session, session_type: str, domain: str = None,
                            technology: str = None, count: int = 30):
    query = db.query(Question)
    if session_type == "profile_fit":
        query = query.filter(Question.is_profile_question == True)
    else:
        query = query.filter(Question.is_profile_question == False)
        category = CATEGORY_MAP.get(session_type)
        if category:
            query = query.filter(Question.category == category)
        if domain:
            try:
                query = query.filter(Question.domain == DomainEnum(domain))
            except Exception:
                pass
        if technology:
            try:
                query = query.filter(Question.technology == TechnologyEnum(technology))
            except Exception:
                pass

    questions = query.all()

    if session_type == "profile_fit":
        # Discovery test: this is the very first thing a person with zero
        # exposure to any of this ever sees. It must never feel like a
        # placement exam. Interest-signal questions ("what energizes you")
        # carry no difficulty and are always included in full — they're what
        # actually drives the category recommendation. The remaining slots
        # are filled mostly with easy/medium aptitude questions, with only a
        # light sprinkling of hard/expert as a stretch, not the norm.
        signal = [q for q in questions if q.is_interest_signal]
        aptitude = [q for q in questions if not q.is_interest_signal]
        remaining = max(0, count - len(signal))
        easy = [q for q in aptitude if q.difficulty in [DifficultyEnum.EASY, DifficultyEnum.MEDIUM]]
        hard = [q for q in aptitude if q.difficulty in [DifficultyEnum.HARD, DifficultyEnum.EXPERT]]
        hard_count = min(len(hard), int(remaining * 0.25))
        easy_count = min(len(easy), remaining - hard_count)
        selected = signal + random.sample(easy, easy_count) + random.sample(hard, hard_count)
        random.shuffle(selected)
        # Progressive ramp: start with a couple of low-pressure questions so
        # nobody bounces off a hard question in the first 30 seconds.
        selected.sort(key=lambda q: {"easy": 0, "medium": 1, "hard": 2, "expert": 3}.get(
            q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty, 1))
        return selected

    if len(questions) > count:
        # Domain tests assume the person already knows they're interested in
        # this track (they were routed here) — keep a real difficulty ramp
        # rather than front-loading hard questions, but don't water it down
        # to the point it stops being a genuine signal for placement-readiness.
        hard = [q for q in questions if q.difficulty in [DifficultyEnum.HARD, DifficultyEnum.EXPERT]]
        easy = [q for q in questions if q.difficulty in [DifficultyEnum.EASY, DifficultyEnum.MEDIUM]]
        hard_count = min(len(hard), int(count * 0.5))
        easy_count = count - hard_count
        selected = random.sample(hard, hard_count) + random.sample(easy, min(len(easy), easy_count))
        selected.sort(key=lambda q: {"easy": 0, "medium": 1, "hard": 2, "expert": 3}.get(
            q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty, 1))
        return selected
    return questions

def compute_section_scores(submissions_data, questions_map):
    section_scores = {}
    for qid, answer_data in submissions_data.items():
        q = questions_map.get(qid)
        if not q:
            continue
        sec = q.section_tag or "General"
        if sec not in section_scores:
            section_scores[sec] = {"obtained": 0, "max": 0, "correct": 0, "total": 0}
        section_scores[sec]["max"] += q.marks
        section_scores[sec]["total"] += 1
        if answer_data.get("is_correct"):
            section_scores[sec]["obtained"] += answer_data.get("marks", 0)
            section_scores[sec]["correct"] += 1
    return section_scores

def determine_eligibility(percentage: float, session_type: str):
    from app.models.user import EligibilityStatusEnum
    if percentage >= 80:
        return EligibilityStatusEnum.EXCEPTIONAL
    elif percentage >= 65:
        return EligibilityStatusEnum.ELIGIBLE
    elif percentage >= 45:
        return EligibilityStatusEnum.MODERATELY_ELIGIBLE
    else:
        return EligibilityStatusEnum.NEEDS_IMPROVEMENT

PROFILE_CATEGORY_INSIGHTS = {
    "IT": {
        "recommendations": ["Your answers point toward IT/Technology careers", "Proceed with a domain-specific technical assessment", "Consider Software Development or Data Science tracks"],
        "learning_path": ["Choose your primary technology stack", "Complete a project-based course", "Build a portfolio project", "Apply for junior roles or internships"],
    },
    "Management": {
        "recommendations": ["Your answers point toward Management or Business Analysis roles", "Good leadership and strategic-thinking indicators", "Consider a Business Analyst or Product path first"],
        "learning_path": ["Study business fundamentals", "Complete an Agile/Scrum certification", "Build stakeholder-management skills", "Network in your target industry"],
    },
    "Non-IT": {
        "recommendations": ["Your answers point toward Non-IT professional careers", "Strong fit for communication and coordination-heavy roles", "Many high-paying careers don't require coding"],
        "learning_path": ["Sharpen quantitative aptitude", "Develop professional communication skills", "Explore a specific non-IT domain", "Get an industry-specific certification"],
    },
    "Finance": {
        "recommendations": ["Your answers point toward Finance/Accounting careers", "Strong analytical and numbers-first thinking"],
        "learning_path": ["Register for CA/CMA foundation or a finance certificate", "Practice financial modeling in Excel", "Follow real company balance sheets to build intuition"],
    },
    "HR": {
        "recommendations": ["Your answers point toward HR / People careers", "Strong people-first, coordination-oriented thinking"],
        "learning_path": ["Take a free HR fundamentals course (SHRM)", "Learn how an ATS/HRIS tool works", "Practice structured interviewing"],
    },
    "Creative": {
        "recommendations": ["Your answers point toward Creative/Design careers", "Strong original-thinking and visual/communication instincts"],
        "learning_path": ["Learn Figma or a content-creation tool", "Build a small portfolio (even 3 pieces is enough to start)", "Study creators/designers you admire and why their work works"],
    },
}


STATUS_FRAMING = {
    "Student": "You're early, which is exactly the right time to explore widely before specializing — don't feel pressure to commit to one path yet.",
    "Fresher": "You're closer to job-ready than it might feel — the fastest path from here is proof-of-work (projects, portfolio) over more studying.",
    "Working Professional": "This isn't about starting from zero — it's about redirecting skills you've already built toward a track that fits you better.",
    "Career Changer": "A pivot works best when you carry your existing experience forward as a strength, not something to hide or discard.",
    "Job Seeker": "Focus on the shortest credible path to your first offer in this track, not the most complete one — you can deepen skills on the job.",
}


def generate_career_insights(percentage: float, session_type: str, section_scores: dict, category_fit: str = None, current_status: str = None):
    strengths, weaknesses, recommendations, learning_path = [], [], [], []

    strong_sections = [s for s, d in section_scores.items() if d["max"] > 0 and (d["obtained"]/d["max"]) >= 0.7]
    weak_sections = [s for s, d in section_scores.items() if d["max"] > 0 and (d["obtained"]/d["max"]) < 0.5]

    if strong_sections:
        strengths = [f"Strong in {s}" for s in strong_sections[:3]]
    if weak_sections:
        weaknesses = [f"Needs improvement in {s}" for s in weak_sections[:3]]

    if session_type == "profile_fit":
        insight = PROFILE_CATEGORY_INSIGHTS.get(
            category_fit.value if hasattr(category_fit, "value") else category_fit,
            PROFILE_CATEGORY_INSIGHTS["Non-IT"],
        )
        recommendations = list(insight["recommendations"])
        learning_path = list(insight["learning_path"])
        # This is the actual point of collecting current_status at onboarding —
        # a student and a working professional pivoting careers need different
        # framing even when they land on the exact same category and score.
        framing = STATUS_FRAMING.get(current_status)
        if framing:
            recommendations.insert(0, framing)
    else:
        learning_resources = {
            "it_technical": ["LeetCode for DSA", "System Design Primer on GitHub", "AWS/GCP Free Tier projects"],
            "management": ["Harvard Business Review case studies", "PMP or Agile certification", "MBA entrance preparation"],
            "non_it": ["RS Aggarwal Quantitative Aptitude", "Communication skills workshops", "Domain-specific certifications"],
            "hr": ["SHRM certification", "LinkedIn Recruiter training", "HR analytics course"],
            "finance": ["ICAI study materials", "CFA curriculum", "Financial modeling with Excel"],
            "creative": ["Google Digital Marketing Certificate", "Meta Blueprint", "Coursera UI/UX design courses"],
        }
        recommendations = [f"Focus on {s} skills" for s in weak_sections[:2]] + ["Build a practical portfolio"]
        learning_path = learning_resources.get(session_type, ["Take domain-specific courses", "Build real projects", "Get certified"])

    return strengths, weaknesses, recommendations, learning_path

@router.post("/start")
async def start_test(request: StartTestRequest, current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    existing = db.query(TestSession).filter(
        TestSession.user_id == current_user.id,
        TestSession.session_type == request.session_type,
        TestSession.status == "in_progress"
    ).first()
    if existing:
        from app.schemas.schemas import QuestionResponse
        questions = get_questions_for_test(db, request.session_type, request.domain, request.technology)
        return {"session_id": existing.id, "questions": [QuestionResponse.from_orm(q) for q in questions],
                "duration_minutes": DURATION_MAP.get(request.session_type, 40)}

    questions = get_questions_for_test(db, request.session_type, request.domain, request.technology)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions available for this test. Run seed.py first.")

    session = TestSession(user_id=current_user.id, session_type=request.session_type,
        status="in_progress", started_at=datetime.utcnow(),
        questions_data={"domain": request.domain, "technology": request.technology})
    db.add(session)
    db.commit()
    db.refresh(session)

    from app.schemas.schemas import QuestionResponse
    return {"session_id": session.id, "questions": [QuestionResponse.from_orm(q) for q in questions],
            "duration_minutes": DURATION_MAP.get(request.session_type, 40)}

@router.post("/submit")
async def submit_test(request: SubmitTestRequest, current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == request.test_session_id,
        TestSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Test session not found")
    if session.status == "completed":
        existing_result = db.query(Result).filter(Result.test_session_id == session.id).first()
        if existing_result:
            return {"result_id": existing_result.id, "percentage": existing_result.percentage,
                    "message": "Already submitted"}

    total_score, max_score = 0.0, 0.0
    submissions_data = {}
    questions_map = {}
    category_votes: dict = {}

    for answer in request.answers:
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        if not question:
            continue
        questions_map[question.id] = question

        # Interest-signal questions ("what energizes you", "your natural team
        # role", etc.) have no right answer. They never touch the score —
        # they only vote for a career category based on which option the
        # person picked. This is what actually decides category_fit now,
        # instead of a blind overall-percentage cutoff.
        if question.is_interest_signal:
            sub = Submission(test_session_id=session.id, question_id=question.id,
                user_answer=answer.user_answer, is_correct=None, marks_obtained=0,
                time_spent_seconds=answer.time_spent_seconds)
            db.add(sub)
            try:
                idx = int(answer.user_answer)
                tag = (question.option_tags or [])[idx]
                category_votes[tag] = category_votes.get(tag, 0) + 1
            except (ValueError, TypeError, IndexError):
                pass
            continue

        max_score += question.marks
        is_correct = False
        marks = 0.0

        if question.question_type in ["MCQ", "aptitude", "scenario"]:
            is_correct = str(answer.user_answer) == str(question.correct_answer)
            marks = float(question.marks) if is_correct else 0.0
        elif question.question_type == "multi_select":
            user_set = set(str(x) for x in (answer.user_answer or []))
            correct_set = set(str(x) for x in (question.correct_answer or []))
            if user_set == correct_set:
                is_correct = True
                marks = float(question.marks)
            elif user_set & correct_set:
                marks = float(question.marks) * len(user_set & correct_set) / len(correct_set)

        total_score += marks
        submissions_data[question.id] = {"is_correct": is_correct, "marks": marks}

        sub = Submission(test_session_id=session.id, question_id=question.id,
            user_answer=answer.user_answer, is_correct=is_correct, marks_obtained=marks,
            time_spent_seconds=answer.time_spent_seconds)
        db.add(sub)

    session.status = "completed"
    session.completed_at = datetime.utcnow()
    session.time_taken_seconds = request.time_taken_seconds
    db.commit()

    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    section_scores = compute_section_scores(submissions_data, questions_map)
    eligibility_status = None
    category_fit = None

    if session.session_type == "profile_fit":
        # Route by what the person actually gravitates toward (the
        # interest-signal votes), NOT by how many aptitude questions they got
        # right. Aptitude score measures reasoning ability; it says nothing
        # about whether someone would rather write code or run a team, so it
        # must never be the thing that decides their career category.
        if category_votes:
            top_votes = max(category_votes.values())
            leaders = [cat for cat, v in category_votes.items() if v == top_votes]
            chosen = leaders[0]
            if len(leaders) > 1:
                # Tie-break using aptitude strengths: whichever tied category
                # has the strongest supporting section score wins.
                cat_section_hint = {
                    "IT": ["Logical Reasoning", "Pattern Recognition", "Technical Aptitude"],
                    "Management": ["Business Acumen", "Leadership", "Decision Making"],
                    "Non-IT": ["Verbal Reasoning", "Priority & Planning", "Everyday Reasoning"],
                    "Finance": ["Business Math", "Statistical Reasoning", "Quantitative"],
                    "Creative": ["Pattern Recognition"],
                    "HR": ["Communication", "Growth Mindset"],
                }
                best_cat, best_score = chosen, -1
                for cat in leaders:
                    hints = cat_section_hint.get(cat, [])
                    score = sum(section_scores.get(h, {}).get("obtained", 0) for h in hints)
                    if score > best_score:
                        best_score, best_cat = score, cat
                chosen = best_cat
            try:
                category_fit = CategoryEnum(chosen)
            except ValueError:
                category_fit = None
        if category_fit is None:
            # Fallback for legacy data / a session with no interest-signal
            # questions answered — better than nothing, worse than the real
            # thing, so this path should rarely fire once seed data is current.
            if percentage >= 65:
                category_fit = CategoryEnum.IT
            elif percentage >= 45:
                category_fit = CategoryEnum.MANAGEMENT
            else:
                category_fit = CategoryEnum.NON_IT

        # The aptitude percentage still matters — it tells the person how
        # strong their reasoning fundamentals are, independent of which
        # career category they lean toward.
        eligibility_status = determine_eligibility(percentage, session.session_type)

        profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if profile:
            profile.category_fit = category_fit
            db.commit()
    else:
        eligibility_status = determine_eligibility(percentage, session.session_type)

    strengths, weaknesses, recommendations, learning_path = generate_career_insights(
        percentage, session.session_type, section_scores, category_fit,
        current_status=(db.query(StudentProfile.current_status)
                         .filter(StudentProfile.user_id == current_user.id).scalar()))

    if session.session_type == "profile_fit" and category_votes:
        # Honesty check: if the votes were genuinely split, say so instead of
        # presenting a confident-sounding single answer. A 4-3-3-2 split
        # across categories is real information — collapsing it into "your
        # category is X" throws that away and overstates how clear-cut the
        # result actually is.
        total_votes = sum(category_votes.values())
        sorted_votes = sorted(category_votes.items(), key=lambda x: -x[1])
        top_cat, top_n = sorted_votes[0]
        runner_up = sorted_votes[1] if len(sorted_votes) > 1 else None
        if total_votes > 0 and (top_n / total_votes) < 0.4 and runner_up:
            recommendations.insert(0,
                f"Your answers were fairly split between {top_cat} and {runner_up[0]} — treat this as two "
                f"directions worth exploring, not a single verdict.")

    domain_fit = None
    technology_fit = None
    if session.questions_data:
        try:
            domain_fit = DomainEnum(session.questions_data.get("domain")) if session.questions_data.get("domain") else None
        except Exception:
            pass
        try:
            technology_fit = TechnologyEnum(session.questions_data.get("technology")) if session.questions_data.get("technology") else None
        except Exception:
            pass

    result = Result(test_session_id=session.id, user_id=current_user.id,
        total_score=total_score, max_score=max_score, percentage=percentage,
        category_signal_breakdown=category_votes if category_votes else None,
        category_fit=category_fit, domain_fit=domain_fit, technology_fit=technology_fit,
        eligibility_status=eligibility_status,
        section_scores={s: {"obtained": d["obtained"], "max": d["max"],
                            "percentage": round(d["obtained"]/d["max"]*100) if d["max"] else 0}
                       for s, d in section_scores.items()},
        strengths=strengths, weaknesses=weaknesses,
        recommendations=recommendations, learning_path=learning_path)
    db.add(result)
    db.commit()
    db.refresh(result)

    return {"result_id": result.id, "percentage": round(percentage, 1),
            "category_fit": category_fit, "eligibility_status": eligibility_status,
            "message": "Test submitted successfully"}

@router.get("/history")
async def get_test_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(TestSession).filter(TestSession.user_id == current_user.id).order_by(TestSession.started_at.desc()).all()
    return sessions
