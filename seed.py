"""
CareerCompass World-Class Seed Script
Run with: python seed.py
"""
import sys
sys.path.append(".")

from app.core.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Fail fast, before touching the database, if the interest-signal question
# tags have drifted out of balance (see verify_question_balance.py for why
# this matters — it's how an earlier version of this file ended up routing
# almost everyone toward "Management" regardless of what they actually said).
from verify_question_balance import check_balance
_balance_ok, _balance_report = check_balance()
if not _balance_ok:
    print("=" * 60)
    print("⚠️  QUESTION BALANCE CHECK FAILED — refusing to seed")
    print("=" * 60)
    print(_balance_report)
    sys.exit(1)
print("✅ Question balance check passed\n")

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
db_name = db_url.rsplit("/", 1)[-1]
postgres_url = db_url.rsplit("/", 1)[0] + "/postgres"

try:
    tmp_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with tmp_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"✅ Database '{db_name}' created.")
        else:
            print(f"ℹ️  Database '{db_name}' already exists.")
    tmp_engine.dispose()
except Exception as e:
    # Non-fatal: managed providers (Render, Supabase, etc.) create the database
    # for you and often restrict access to the shared `postgres` admin DB, so
    # this check simply can't run there — that's fine, just proceed.
    print(f"ℹ️  Skipped auto-create check (expected on managed hosts like Render): {e}")

from app.core.database import SessionLocal, engine
from app.models.user import Base, User, Question
from app.models.user import CategoryEnum, DomainEnum, TechnologyEnum, QuestionTypeEnum, DifficultyEnum
import app.models.bookings  # noqa: F401 — registers Counselor/booking tables on Base.metadata
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── Admin User ──────────────────────────────────────────────────────────────
admin = db.query(User).filter(User.email == "admin@simplemagics.com").first()
if not admin:
    admin = User(email="admin@simplemagics.com", hashed_password=get_password_hash("Admin@123"), is_admin=True)
    db.add(admin)
    print("✅ Admin user created.")

# ── Demo Counselors ─────────────────────────────────────────────────────────
from app.models.bookings import Counselor

demo_counselors = [
    {"full_name": "Ananya Rao", "email": "ananya.rao@simplemagics.com", "specialties": ["career_counseling", "free_counseling"],
     "bio": "8 years guiding IT and management career switchers."},
    {"full_name": "Vikram Shah", "email": "vikram.shah@simplemagics.com", "specialties": ["student_guidance", "free_counseling"],
     "bio": "Former school counselor specializing in 10th/12th stream selection."},
    {"full_name": "Priya Menon", "email": "priya.menon@simplemagics.com", "specialties": ["career_counseling", "student_guidance", "free_counseling"],
     "bio": "Career coach for career-breakers and homemakers re-entering the workforce."},
]
for c in demo_counselors:
    existing = db.query(Counselor).filter(Counselor.email == c["email"]).first()
    if not existing:
        db.add(Counselor(**c))
if not db.query(Counselor).first():
    print("✅ Demo counselors created.")

from app.models.user import Question

def add_questions(questions_list, is_profile=False, category=None, domain=None, technology=None, difficulty=DifficultyEnum.MEDIUM):
    added = 0
    for q in questions_list:
        if db.query(Question).filter(Question.question_text == q["text"]).first():
            continue  # already seeded — keeps this script safe to re-run (e.g. on redeploy)
        is_signal = q.get("signal", False)
        obj = Question(
            question_text=q["text"],
            question_type=QuestionTypeEnum.MCQ,
            options=q["options"],
            # Interest-signal questions have no right answer, so they're
            # never scored — correct_answer is meaningless for them.
            correct_answer=None if is_signal else q["correct"],
            marks=0 if is_signal else q.get("marks", 2),
            explanation=q.get("explanation", ""),
            section_tag=q.get("section", "General"),
            is_profile_question=is_profile,
            is_interest_signal=is_signal,
            option_tags=q.get("tags") if is_signal else None,
            category=q.get("category") or category,
            domain=q.get("domain") or domain,
            technology=q.get("technology") or technology,
            difficulty=q.get("diff") or difficulty,
        )
        db.add(obj)
        added += 1
    db.flush()
    return added
# ═══════════════════════════════════════════════════════════════════════════
profile_questions = [
    {"text": "You have 2 hours left to submit a project. The code works but isn't clean. You:", "options": ["Submit as-is — it works, that's what matters", "Refactor completely even if you miss the deadline", "Clean the most critical parts, submit on time with a note", "Ask for an extension to perfect it"], "correct": 2, "marks": 3, "section": "Decision Making", "diff": DifficultyEnum.HARD, "explanation": "Best engineers balance quality and deadlines — submit working code, document tech debt."},
    {"text": "If FAST is coded as GBUV, what is the code for SLOW?", "options": ["TMPX", "TNPX", "TOUX", "SLPX"], "correct": 0, "marks": 3, "section": "Logical Reasoning", "diff": DifficultyEnum.HARD, "explanation": "Each letter shifts +1: S→T, L→M, O→P, W→X = TMPX"},
    {"text": "A company's revenue increased 20% but profit fell 10%. What most likely happened?", "options": ["Cost of operations increased significantly", "Sales actually decreased", "Taxes doubled", "Revenue calculation has an error"], "correct": 0, "marks": 3, "section": "Business Acumen", "diff": DifficultyEnum.HARD},
    {"text": "30 people are in a room. Each shakes hands with everyone else exactly once. Total handshakes?", "options": ["435", "870", "900", "30"], "correct": 0, "marks": 3, "section": "Quantitative", "diff": DifficultyEnum.HARD, "explanation": "n(n-1)/2 = 30×29/2 = 435"},
    {"text": "A product's price rises 25% then falls 25%. Net change?", "options": ["0%", "+6.25%", "-6.25%", "-5%"], "correct": 2, "marks": 3, "section": "Percentage", "diff": DifficultyEnum.HARD, "explanation": "100→125→93.75. Net = -6.25%"},
    {"text": "Which activity do you find MOST energizing?", "options": ["Leading meetings, pitching ideas to stakeholders", "Supporting and coordinating a team so everyone stays aligned", "Digging into numbers to find where something is going wrong", "Making something visually or creatively compelling"], "signal": True, "tags": ["Management", "HR", "Finance", "Creative"], "marks": 0, "section": "Energy Mapping", "diff": DifficultyEnum.EASY},
    {"text": "6 workers build a wall in 10 days. How many workers are needed to build it in 4 days?", "options": ["12", "15", "18", "24"], "correct": 1, "marks": 3, "section": "Work & Time", "diff": DifficultyEnum.HARD, "explanation": "Total work = 60 man-days. Workers needed = 60/4 = 15"},
    {"text": "Number series: 3, 6, 11, 18, 27, ___", "options": ["36", "38", "39", "40"], "correct": 2, "marks": 3, "section": "Pattern Recognition", "diff": DifficultyEnum.HARD, "explanation": "Differences increase by 2: +3,+5,+7,+9,+11. Next: 27+12=39"},
    {"text": "Two trains 300km apart approach each other at 60 and 90 km/h. A bird flies at 120 km/h between them until they meet. How far does the bird fly?", "options": ["200km", "240km", "180km", "150km"], "correct": 1, "marks": 4, "section": "Advanced Quantitative", "diff": DifficultyEnum.EXPERT, "explanation": "Trains meet in 300/150=2 hours. Bird flies 2×120=240km"},
    {"text": "You discover your manager made a public mistake affecting the entire team. You:", "options": ["Stay quiet — not your place", "Tell colleagues to protect them", "Approach the manager privately with the correct information", "Escalate immediately to HR"], "correct": 2, "marks": 3, "section": "Leadership & Ethics", "diff": DifficultyEnum.HARD},
    {"text": "In a group project you naturally:", "options": ["Take charge and direct the team", "Talk to people outside the group to get buy-in or resources", "Track the budget and make sure resources aren't wasted", "Handle the creative output — slides, design, the final look"], "signal": True, "tags": ["Management", "Non-IT", "Finance", "Creative"], "marks": 0, "section": "Team Role", "diff": DifficultyEnum.EASY},
    {"text": "Complete: Innovation is to Progress as Stagnation is to ___", "options": ["Development", "Decline", "Movement", "Success"], "correct": 1, "marks": 2, "section": "Verbal Reasoning", "diff": DifficultyEnum.MEDIUM},
    {"text": "A series: A, C, F, J, O, ___", "options": ["T", "U", "V", "S"], "correct": 1, "marks": 3, "section": "Pattern Recognition", "diff": DifficultyEnum.HARD, "explanation": "+2,+3,+4,+5,+6. O(15)+6=U(21)"},
    {"text": "A marketing campaign got 100,000 views, 2,000 clicks, 50 purchases at ₹1,000. You spent ₹30,000. What is the ROI?", "options": ["67%", "50%", "166%", "100%"], "correct": 0, "marks": 4, "section": "Business Math", "diff": DifficultyEnum.EXPERT, "explanation": "ROI = (Revenue-Cost)/Cost = (50,000-30,000)/30,000 = 66.7%"},
    {"text": "Read: 'All sustainable businesses create value for customers. ABC Corp is sustainable.' Therefore:", "options": ["ABC Corp creates customer value", "ABC Corp is profitable", "ABC Corp will never fail", "ABC Corp has the best products"], "correct": 0, "marks": 3, "section": "Critical Thinking", "diff": DifficultyEnum.MEDIUM},
    {"text": "You receive harsh feedback on your work. Your FIRST response:", "options": ["Defend your choices immediately", "Go quiet and feel bad", "Thank them, genuinely reflect, then improve", "Question their judgment internally"], "correct": 2, "marks": 2, "section": "Growth Mindset", "diff": DifficultyEnum.MEDIUM},
    {"text": "CAC = ₹500, LTV = ₹1,500. This business model is:", "options": ["Unsustainable — costs too much to acquire", "Healthy — LTV:CAC of 3:1 is strong", "Breaking even only", "Depends entirely on the industry"], "correct": 1, "marks": 3, "section": "Business Acumen", "diff": DifficultyEnum.HARD, "explanation": "LTV:CAC ratio of 3:1 or higher is the benchmark for healthy SaaS businesses."},
    {"text": "If you could build ANYTHING right now, it would be:", "options": ["A company or business from scratch", "A better way to serve customers or solve an everyday problem", "A program or community that helps people grow", "A stunning design, film, or creative piece"], "signal": True, "tags": ["Management", "Non-IT", "HR", "Creative"], "marks": 0, "section": "Builder Profile", "diff": DifficultyEnum.EASY},
    {"text": "70% of startups fail in year 1. A startup survived 2 years. You conclude:", "options": ["It will definitely succeed now", "The founders are exceptionally talented", "It has beaten the most critical survival odds", "It is already profitable"], "correct": 2, "marks": 3, "section": "Statistical Reasoning", "diff": DifficultyEnum.HARD},
    {"text": "A product sells 500 units/month at ₹1,000. After a 20% price hike, sales drop 30%. New monthly revenue?", "options": ["₹4,20,000", "₹5,00,000", "₹3,50,000", "₹6,00,000"], "correct": 0, "marks": 4, "section": "Business Math", "diff": DifficultyEnum.EXPERT, "explanation": "New price: ₹1,200. New units: 350. Revenue: 1,200×350 = ₹4,20,000"},
    {"text": "Your team is divided 50-50 on a major decision. As the lead, you:", "options": ["Pick the option you personally prefer", "Delay until consensus is reached", "Gather more data, facilitate structured debate, then decide", "Let the senior person decide"], "correct": 2, "marks": 3, "section": "Leadership", "diff": DifficultyEnum.HARD},
    {"text": "When given a complex problem at work, your first instinct is to:", "options": ["Rally the people affected and get everyone moving on a plan", "Just get hands-on and start fixing it practically", "Talk it through with the people involved first", "Break it down into numbers to see what's really going on"], "signal": True, "tags": ["Management", "Non-IT", "HR", "Finance"], "marks": 0, "section": "Cognitive Style", "diff": DifficultyEnum.EASY},
    {"text": "What is O(n log n) time complexity?", "options": ["Quadratic — slower than linear", "Between linear O(n) and quadratic O(n²) — typical of efficient sorting", "Constant time regardless of input", "Same as O(n)"], "correct": 1, "marks": 3, "section": "Technical Aptitude", "diff": DifficultyEnum.HARD},
    {"text": "Three tasks due today: one impacts 10K users, one is requested by CEO, one is your personal KPI. You prioritize:", "options": ["CEO request first — politics matter", "Impact on 10K users first — max business value", "Personal KPI first — your performance review matters", "Easiest task first to gain momentum"], "correct": 1, "marks": 3, "section": "Priority & Planning", "diff": DifficultyEnum.HARD},
    {"text": "Which word is MOST opposite in meaning to 'Perspicacious'?", "options": ["Astute", "Obtuse", "Shrewd", "Vigilant"], "correct": 1, "marks": 3, "section": "Vocabulary", "diff": DifficultyEnum.HARD, "explanation": "Perspicacious = having sharp insight. Obtuse = dull/slow to understand."},

    # ── Additional interest-signal questions (no right/wrong answer — these
    # are what actually route a person to a category. Plain everyday
    # language on purpose: someone who has never had a job should still be
    # able to answer honestly.
    #
    # Tag design note: each of the 6 real categories (IT, Management, Non-IT,
    # HR, Finance, Creative) appears in EXACTLY 8 of these 12 signal questions
    # — verified with a script, not eyeballed. An earlier version of this file
    # had Management in 10/10 questions and Non-IT in just 1/10, which meant
    # Management would win the vote almost by default regardless of what a
    # person actually said about themselves. That's fixed now.) ─────────────
    {"text": "Which sounds like the most satisfying way to spend a workday?", "options": ["Solving one hard technical puzzle for hours until it clicks", "Helping a colleague work through a tough situation", "Going through numbers until a clear pattern emerges", "Producing something people will actually see or use"], "signal": True, "tags": ["IT", "HR", "Finance", "Creative"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "A free Saturday with no plans. You'd most enjoy:", "options": ["Tinkering with a gadget, app, or website until it works right", "Organizing an outing and making sure everyone has a good time", "Planning out a budget or a big purchase carefully", "Making something — a video, a drawing, a playlist, a room makeover"], "signal": True, "tags": ["IT", "Non-IT", "Finance", "Creative"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "Which of these would you enjoy most?", "options": ["Writing code that quietly saves everyone hours of manual work", "Being the go-to person customers trust when something goes wrong", "Coaching someone through a rough patch at work", "Turning a rough idea into something visually polished"], "signal": True, "tags": ["IT", "Non-IT", "HR", "Creative"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "In school/college group work, people usually come to you for:", "options": ["Fixing the technical or logical part nobody else can crack", "Getting things done practically when others are stuck overthinking", "Keeping everyone calm and on the same page", "Making sure the numbers or budget for the project add up"], "signal": True, "tags": ["IT", "Non-IT", "HR", "Finance"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "Which activity would you choose to spend a whole afternoon on?", "options": ["Debugging a tricky problem until it finally works", "Pitching a new idea to leadership and getting buy-in", "Helping someone talk through a personal or work problem", "Designing something until it feels exactly right"], "signal": True, "tags": ["IT", "Management", "HR", "Creative"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "Which everyday skill do you rely on most?", "options": ["Figuring out exactly why something broke", "Getting a room full of people aligned on a plan", "Reading people well and knowing what they need", "Making a spreadsheet of numbers tell a clear story"], "signal": True, "tags": ["IT", "Management", "HR", "Finance"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "Which of these headlines would you click on first?", "options": ["'5 tools every beginner coder should know'", "'How this founder built a business from home'", "'The customer-service trick that turns angry buyers into fans'", "'The design trick top creators use to stop the scroll'"], "signal": True, "tags": ["IT", "Management", "Non-IT", "Creative"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},
    {"text": "A friend asks you to help plan a small event on a tight budget. You naturally focus on:", "options": ["Setting up a simple app or spreadsheet system to track everything", "Taking charge and delegating tasks to get it done", "Handling the logistics and vendors hands-on", "Making sure it doesn't go over budget"], "signal": True, "tags": ["IT", "Management", "Non-IT", "Finance"], "marks": 0, "section": "Everyday Interests", "diff": DifficultyEnum.EASY},

    # ── Additional easy/medium aptitude questions in plain, non-corporate
    # language — for someone who has never seen a P&L or a codebase. ────────
    {"text": "A shop sells pens at ₹10 each. If you buy 3 and get 1 free, how much do 8 pens actually cost you?", "options": ["₹60", "₹70", "₹80", "₹50"], "correct": 0, "marks": 2, "section": "Everyday Math", "diff": DifficultyEnum.EASY, "explanation": "For every 4 pens you pay for 3: 8 pens = 2 sets of 4 = pay for 6 = ₹60"},
    {"text": "Which number continues the pattern? 2, 4, 8, 16, ___", "options": ["20", "24", "32", "18"], "correct": 2, "marks": 2, "section": "Pattern Recognition", "diff": DifficultyEnum.EASY, "explanation": "Each number doubles: 16 × 2 = 32"},
    {"text": "If today is Wednesday, what day will it be 10 days from now?", "options": ["Saturday", "Sunday", "Friday", "Monday"], "correct": 0, "marks": 2, "section": "Everyday Reasoning", "diff": DifficultyEnum.EASY, "explanation": "10 days = 1 week + 3 days. Wednesday + 3 = Saturday"},
    {"text": "'Generous' is to 'Stingy' as 'Brave' is to:", "options": ["Bold", "Cowardly", "Strong", "Confident"], "correct": 1, "marks": 2, "section": "Verbal Reasoning", "diff": DifficultyEnum.EASY},
    {"text": "You're told a task is due 'by end of day Friday.' What's the safest way to read that?", "options": ["Any time before Friday midnight", "Sometime the following Monday", "Whenever you get to it that week", "Only during work hours on Friday, nothing after"], "correct": 0, "marks": 2, "section": "Everyday Reasoning", "diff": DifficultyEnum.MEDIUM},
    {"text": "A recipe needs 2 cups of flour for 4 people. How many cups for 10 people?", "options": ["4", "5", "6", "3"], "correct": 1, "marks": 2, "section": "Everyday Math", "diff": DifficultyEnum.EASY, "explanation": "2 cups ÷ 4 people = 0.5 cups/person. 0.5 × 10 = 5 cups"},
    {"text": "Which word does NOT belong with the others: Apple, Banana, Carrot, Mango", "options": ["Apple", "Banana", "Carrot", "Mango"], "correct": 2, "marks": 2, "section": "Everyday Reasoning", "diff": DifficultyEnum.EASY, "explanation": "Apple, Banana, and Mango are fruits. Carrot is a vegetable."},
    {"text": "You promised to help a friend move houses at 10 AM, but a family emergency needs your attention that morning. You'd:", "options": ["Message them as early as possible, explain honestly, and help find another time or way to help", "Just don't show up and explain later if they ask", "Cancel without giving a reason to avoid a long conversation", "Show up late without telling them anything"], "correct": 0, "marks": 2, "section": "Everyday Judgment", "diff": DifficultyEnum.EASY},
]
_n = add_questions(profile_questions, is_profile=True)
print(f"✅ Added {_n} new Profile Intelligence questions ({len(profile_questions) - _n} already existed)")

# ═══════════════════════════════════════════════════════════════════════════
# IT TECHNICAL QUESTIONS — 30 Hard Questions
# ═══════════════════════════════════════════════════════════════════════════
it_questions = [
    {"text": "An e-commerce page takes 8 seconds to load with millions of users. Your FIRST action?", "options": ["Add more servers immediately", "Profile the bottleneck — DB, CDN, or inefficient code?", "Reduce all image sizes", "Tell the PM 8 seconds is acceptable"], "correct": 1, "marks": 4, "section": "System Design", "diff": DifficultyEnum.HARD, "explanation": "Always profile first. Adding servers without knowing the bottleneck wastes money."},
    {"text": "API returns 200 OK but client doesn't get expected data. You investigate:", "options": ["Database connection", "Response body serialization and DTO mapping", "Restart the server", "Check network logs"], "correct": 1, "marks": 3, "section": "Debugging", "diff": DifficultyEnum.HARD},
    {"text": "Time complexity of finding an element in a balanced BST?", "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"], "correct": 2, "marks": 3, "section": "Data Structures", "diff": DifficultyEnum.MEDIUM},
    {"text": "Your DB has 10M records, a query takes 45 seconds. Best FIRST optimization?", "options": ["Move to NoSQL immediately", "Add a composite index on WHERE clause columns", "Cache all results in Redis", "Upgrade server RAM"], "correct": 1, "marks": 4, "section": "Database Optimization", "diff": DifficultyEnum.HARD, "explanation": "Proper indexing typically reduces query time from seconds to milliseconds."},
    {"text": "In microservices, Service A calls Service B which is down. What pattern prevents cascade failure?", "options": ["Load balancer", "Circuit Breaker pattern", "Retry with exponential backoff only", "Message queue alone"], "correct": 1, "marks": 4, "section": "System Design", "diff": DifficultyEnum.HARD},
    {"text": "console.log(typeof null) outputs:", "options": ["null", "undefined", "object", "NaN"], "correct": 2, "marks": 3, "section": "JavaScript", "diff": DifficultyEnum.HARD, "explanation": "typeof null === 'object' is a known JavaScript bug from 1995, never fixed for backward compatibility."},
    {"text": "Which HTTP method is idempotent but NOT safe?", "options": ["GET", "POST", "PUT", "PATCH"], "correct": 2, "marks": 4, "section": "REST APIs", "diff": DifficultyEnum.EXPERT, "explanation": "Idempotent: same result on repeated calls. Safe: read-only. PUT is idempotent but modifies data (not safe). GET is both."},
    {"text": "The CAP theorem — for a banking system you prioritize:", "options": ["Availability + Partition Tolerance", "Consistency + Partition Tolerance", "Consistency + Availability", "All three — non-negotiable"], "correct": 1, "marks": 4, "section": "Distributed Systems", "diff": DifficultyEnum.EXPERT, "explanation": "Banks need data consistency above all else. Lose a transaction, lose trust."},
    {"text": "Memory leak in Node.js causes crashes every 6 hours. You diagnose it by:", "options": ["Restarting every 5 hours as a workaround", "Taking heap snapshots over time to track object allocation growth", "Increasing server RAM", "Rewriting in a different language"], "correct": 1, "marks": 4, "section": "Performance Engineering", "diff": DifficultyEnum.EXPERT},
    {"text": "You have 1M concurrent users needing sessions. Best approach?", "options": ["Server-side sessions in memory", "JWT (stateless) — scales horizontally with no server state", "Database-stored sessions", "File-based sessions"], "correct": 1, "marks": 4, "section": "Scalability", "diff": DifficultyEnum.HARD},
    {"text": "Senior dev says: 'This is O(n²), fix it.' You're finding matches across two arrays. Optimal solution:", "options": ["Add break statements to nested loops", "Sort both arrays first", "Use a HashMap for O(n) average lookup", "Use binary search on one array"], "correct": 2, "marks": 4, "section": "Algorithm Optimization", "diff": DifficultyEnum.HARD},
    {"text": "git rebase vs git merge — key difference:", "options": ["Rebase is for hotfixes only", "Rebase rewrites history for a linear timeline; merge preserves full history", "Merge is always safer than rebase", "They produce identical results"], "correct": 1, "marks": 3, "section": "Version Control", "diff": DifficultyEnum.MEDIUM},
    {"text": "When should you use Redis over a relational database?", "options": ["Always — Redis is faster for everything", "Caching, sessions, rate limiting, pub/sub — not for complex relations", "SQL is always better for anything important", "Use whatever your team knows best"], "correct": 1, "marks": 3, "section": "Architecture", "diff": DifficultyEnum.HARD},
    {"text": "This code: query = 'SELECT * FROM users WHERE id=' + userId. The vulnerability is:", "options": ["Nothing — it works fine", "SQL injection — userId can contain malicious SQL", "Only a performance issue", "Syntax error in some databases"], "correct": 1, "marks": 3, "section": "Security", "diff": DifficultyEnum.MEDIUM},
    {"text": "For a social network (users follow users), the optimal DB schema is:", "options": ["User table with 'followers' JSON column", "Separate follows table: (follower_id, following_id, created_at)", "Denormalized single table", "Separate database for social graph"], "correct": 1, "marks": 4, "section": "Database Design", "diff": DifficultyEnum.HARD},
    {"text": "In agile, 'As a user I want to reset my password.' Acceptance criteria MUST include:", "options": ["Only the happy path: email received and password updated", "Edge cases: expired links, already-used tokens, rate limiting, clear error states", "Just the UI design mockup", "Backend implementation details"], "correct": 1, "marks": 4, "section": "Product Development", "diff": DifficultyEnum.HARD},
    {"text": "A race condition is:", "options": ["Two servers competing for requests", "Multiple processes accessing shared data simultaneously with unexpected results", "A performance bottleneck", "A CI/CD pipeline conflict"], "correct": 1, "marks": 3, "section": "Concurrency", "diff": DifficultyEnum.HARD},
    {"text": "Docker containers are best described as:", "options": ["Virtual machines with their own OS", "Lightweight, isolated environments packaging app + dependencies", "Just a faster way to deploy code", "A cloud hosting service"], "correct": 1, "marks": 2, "section": "DevOps", "diff": DifficultyEnum.MEDIUM},
    {"text": "WebSockets are preferable to REST APIs for:", "options": ["Fetching user profiles on page load", "Real-time: chat, live notifications, collaborative editing", "Standard CRUD operations", "Static file serving"], "correct": 1, "marks": 3, "section": "Real-time Systems", "diff": DifficultyEnum.MEDIUM},
    {"text": "Startup with 3 engineers: monolith vs microservices?", "options": ["Always microservices — it scales", "Monolith — simpler to build, debug, deploy at early stage", "Serverless functions only", "Whatever investors prefer"], "correct": 1, "marks": 4, "section": "Architecture Decisions", "diff": DifficultyEnum.HARD, "explanation": "Microservices complexity kills small teams. Start monolith, extract services when genuinely needed."},
    {"text": "React: why avoid mutating state directly?", "options": ["It causes syntax errors", "React uses reference equality — mutation bypasses re-render detection", "It's slower", "It breaks routing"], "correct": 1, "marks": 3, "section": "React", "diff": DifficultyEnum.MEDIUM},
    {"text": "ACID in databases: what does Isolation guarantee?", "options": ["Transactions complete fully or roll back", "Data survives system failures", "Concurrent transactions don't interfere with each other", "All data is accurate"], "correct": 2, "marks": 4, "section": "Database Theory", "diff": DifficultyEnum.HARD},
    {"text": "Estimating a feature's development time, you should:", "options": ["Say 1 week for everything to seem consistent", "Break into tasks, estimate each, add 30-50% buffer, state assumptions", "Give the lowest estimate to win the work", "Refuse to estimate without complete specifications"], "correct": 1, "marks": 3, "section": "Engineering Practices", "diff": DifficultyEnum.MEDIUM},
    {"text": "CI/CD pipeline fails but tests pass locally. Most likely cause:", "options": ["Tests are wrong", "Environment differences: missing env vars, different dependency versions", "CI server is broken", "Hidden code bugs"], "correct": 1, "marks": 3, "section": "DevOps", "diff": DifficultyEnum.HARD},
    {"text": "What does SSL/TLS provide?", "options": ["Data stored encrypted on disk", "Encrypted transit + server authentication via certificates", "User authentication only", "Faster data transfer"], "correct": 1, "marks": 2, "section": "Security", "diff": DifficultyEnum.MEDIUM},
    {"text": "A user says 'the website is broken.' Your debugging process:", "options": ["Restart the server immediately", "Reproduce, check scope (1 user or all?), check logs, identify root cause", "Push a hotfix immediately", "Ask the user to clear cache first"], "correct": 1, "marks": 3, "section": "Problem Solving", "diff": DifficultyEnum.MEDIUM},
    {"text": "Authentication vs authorization — correct distinction:", "options": ["They mean the same thing in security", "Auth = verifying who you are; Authorization = what you're allowed to do", "Authentication = login page; Authorization = signup page", "Authentication = token; Authorization = password"], "correct": 1, "marks": 2, "section": "Security", "diff": DifficultyEnum.EASY},
    {"text": "N+1 query problem in ORM: what is it and how do you fix it?", "options": ["Unrelated — just a naming convention", "1 query to get parent records + N separate queries for each child; fix with eager loading (JOIN)", "Running the same query twice", "A database timeout issue"], "correct": 1, "marks": 4, "section": "Database Performance", "diff": DifficultyEnum.EXPERT},
    {"text": "Code review should prioritize:", "options": ["Formatting and style first", "Correctness, security vulnerabilities, and edge case handling first", "Variable naming consistency", "Number of comments"], "correct": 1, "marks": 2, "section": "Engineering Practices", "diff": DifficultyEnum.MEDIUM},
    {"text": "To design a URL shortener (bit.ly) at scale, the core challenge is:", "options": ["Storing the original URLs", "Generating short unique keys with fast read/write at massive scale with no collisions", "Building the website frontend", "Adding click analytics"], "correct": 1, "marks": 4, "section": "System Design", "diff": DifficultyEnum.EXPERT},
]
_n = add_questions(it_questions, category=CategoryEnum.IT, domain=DomainEnum.FULLSTACK, technology=TechnologyEnum.PYTHON)
print(f"✅ Added {_n} new IT Technical questions ({len(it_questions) - _n} already existed)")

# ═══════════════════════════════════════════════════════════════════════════
# MANAGEMENT & BUSINESS QUESTIONS — 25 Hard Questions
# ═══════════════════════════════════════════════════════════════════════════
mgmt_questions = [
    {"text": "Top performer suddenly missing deadlines. Your FIRST step as manager:", "options": ["Issue formal warning immediately", "Have private empathetic 1-on-1 to understand root cause", "Remove from project", "Discuss with the team"], "correct": 1, "marks": 4, "section": "People Management", "diff": DifficultyEnum.HARD},
    {"text": "Project is 2 weeks from launch with critical bugs. CEO says launch on time. You:", "options": ["Launch and fix bugs after — pressure is real", "Launch only if bugs don't harm users; otherwise negotiate timeline with data", "Follow CEO's order without question", "Resign if forced to launch broken product"], "correct": 1, "marks": 4, "section": "Ethical Leadership", "diff": DifficultyEnum.EXPERT},
    {"text": "A stakeholder keeps changing requirements mid-project. Most effective long-term solution:", "options": ["Accept all changes — customer is always right", "Ignore new requests until next release", "Formal change management process with impact assessment and approval", "Reduce stakeholder meetings"], "correct": 2, "marks": 4, "section": "Stakeholder Management", "diff": DifficultyEnum.HARD},
    {"text": "Marketing campaign: 100K views, 2K clicks, 50 sales at ₹1K. Spent ₹30K. ROI:", "options": ["67%", "166%", "50%", "33%"], "correct": 0, "marks": 4, "section": "Marketing Math", "diff": DifficultyEnum.EXPERT, "explanation": "ROI = (Revenue-Cost)/Cost × 100 = (50,000-30,000)/30,000 × 100 = 66.7%"},
    {"text": "LTV:CAC ratio of 1.5:1 for a SaaS business means:", "options": ["Excellent — growing profitably", "Borderline — revenue barely covers acquisition costs", "Healthy — 1.5x is the standard benchmark", "Irrelevant without churn data"], "correct": 1, "marks": 4, "section": "Unit Economics", "diff": DifficultyEnum.HARD, "explanation": "Industry standard is LTV:CAC of 3:1+. At 1.5:1, you're barely breaking even on customer acquisition."},
    {"text": "Porter's Five Forces does NOT include:", "options": ["Threat of substitutes", "Bargaining power of suppliers", "Employee satisfaction scores", "Competitive rivalry"], "correct": 2, "marks": 3, "section": "Strategic Frameworks", "diff": DifficultyEnum.MEDIUM},
    {"text": "B2B sales: 20 deals in pipeline at ₹5L avg each, 90-day average cycle. Monthly revenue forecast:", "options": ["₹33L", "₹10L", "₹100L", "₹5L"], "correct": 0, "marks": 4, "section": "Sales Math", "diff": DifficultyEnum.EXPERT, "explanation": "Pipeline: 20×5L=₹100L over 3 months = ₹33.3L/month"},
    {"text": "Market A: large, competitive. Market B: small, underserved. You choose:", "options": ["Always A — bigger market = more money", "Always B — less competition", "Analyze: if B has sufficient TAM and a path to A, start with B (Blue Ocean)", "Whatever your investors want"], "correct": 2, "marks": 4, "section": "Market Strategy", "diff": DifficultyEnum.HARD},
    {"text": "A team member publicly disagrees with your decision in a meeting. You:", "options": ["Shut it down firmly — you're the manager", "Welcome it: hear them out, respond with reasoning, decide transparently", "Discuss only in private — never in meetings", "Ignore it and move on"], "correct": 1, "marks": 4, "section": "Leadership Under Pressure", "diff": DifficultyEnum.HARD},
    {"text": "Gross Margin % if Revenue = ₹10L, COGS = ₹4L:", "options": ["40%", "60%", "150%", "25%"], "correct": 1, "marks": 3, "section": "Financial Literacy", "diff": DifficultyEnum.MEDIUM, "explanation": "GM% = (Revenue-COGS)/Revenue × 100 = 6L/10L × 100 = 60%"},
    {"text": "What is 'scope creep' and how do you prevent it?", "options": ["When project team expands; hire fewer people", "Requirements expanding beyond original scope; prevent with change control process", "A technical bug type; fix with testing", "Budget overruns; track expenses weekly"], "correct": 1, "marks": 3, "section": "Project Management", "diff": DifficultyEnum.MEDIUM},
    {"text": "Design Thinking's five stages in order:", "options": ["Plan, Design, Build, Test, Launch", "Empathize, Define, Ideate, Prototype, Test", "Research, Wireframe, Design, Develop, Deploy", "Discover, Design, Deliver, Measure, Scale"], "correct": 1, "marks": 2, "section": "Innovation", "diff": DifficultyEnum.EASY},
    {"text": "Most important metric for a SaaS business:", "options": ["Total users", "MRR growth + Net Revenue Retention (NRR)", "Website traffic", "Number of features shipped"], "correct": 1, "marks": 4, "section": "SaaS Metrics", "diff": DifficultyEnum.HARD, "explanation": "NRR >100% means existing customers are growing revenue even without new acquisitions."},
    {"text": "A competitor launched identical product at half your price. Immediate strategic response:", "options": ["Match price immediately to protect market share", "Panic and completely pivot", "Analyze: their cost structure, your differentiation, customer loyalty — then respond", "Do nothing — quality wins itself"], "correct": 2, "marks": 4, "section": "Competitive Strategy", "diff": DifficultyEnum.HARD},
    {"text": "Two candidates: A (brilliant, poor team player) vs B (good, excellent team player). For a critical team role:", "options": ["Always A — talent is irreplaceable", "Always B — culture is everything", "A if the role is solitary; B for collaborative roles — context matters", "Hire both and see who performs"], "correct": 2, "marks": 4, "section": "Hiring Decisions", "diff": DifficultyEnum.HARD},
    {"text": "Net Promoter Score (NPS) is calculated as:", "options": ["(Promoters - Detractors) / Total × 100", "% Promoters - % Detractors", "Total positive reviews / total reviews", "Average rating / 10 × 100"], "correct": 1, "marks": 3, "section": "Customer Success", "diff": DifficultyEnum.MEDIUM},
    {"text": "What is 'burn rate' in startup context?", "options": ["Speed of product development", "Monthly cash spend (negative cash flow)", "Employee turnover rate", "Marketing budget consumption rate"], "correct": 1, "marks": 2, "section": "Startup Finance", "diff": DifficultyEnum.EASY},
    {"text": "OKR methodology: what makes a KEY RESULT different from a task?", "options": ["Key Results are measurable outcomes, not activities", "Key Results are bigger tasks", "Key Results are quarterly goals", "Key Results are the same as KPIs"], "correct": 0, "marks": 4, "section": "Goal Setting", "diff": DifficultyEnum.HARD, "explanation": "KR: 'Reduce churn to 2%' (measurable outcome). Task: 'Send retention emails' (activity)."},
    {"text": "Servant leadership primarily means:", "options": ["Doing whatever your team asks", "Leading by removing obstacles, enabling your team's success", "Being humble and quiet all the time", "Always saying yes to team requests"], "correct": 1, "marks": 2, "section": "Leadership Philosophy", "diff": DifficultyEnum.MEDIUM},
    {"text": "Product has 2% conversion rate. To hit 200 sales, you need how many visitors?", "options": ["400", "1,000", "10,000", "5,000"], "correct": 2, "marks": 3, "section": "Business Math", "diff": DifficultyEnum.MEDIUM, "explanation": "200 / 0.02 = 10,000 visitors"},
    {"text": "Kirkpatrick's 4 levels of training evaluation:", "options": ["Plan, Design, Deliver, Evaluate", "Reaction, Learning, Behavior, Results", "Input, Process, Output, Outcome", "Awareness, Interest, Desire, Action"], "correct": 1, "marks": 3, "section": "L&D", "diff": DifficultyEnum.HARD},
    {"text": "Best way to give constructive feedback:", "options": ["'You always make this mistake'", "SBI: Situation, Behavior, Impact — then ask for their perspective", "Only praise in public, criticize in private always", "Wait for the annual review cycle"], "correct": 1, "marks": 3, "section": "Communication", "diff": DifficultyEnum.MEDIUM},
    {"text": "A product feature validation should happen:", "options": ["After full engineering is complete", "Before full investment — prototype/MVP with real users", "After product launch and user feedback", "Validation is optional for experienced teams"], "correct": 1, "marks": 3, "section": "Product Development", "diff": DifficultyEnum.MEDIUM},
    {"text": "EBITDA stands for:", "options": ["Earnings Before Interest Taxes Depreciation Amortization", "Earnings Based on Income Tax and Debt Assessment", "Effective Business Income Tax Deduction Amount", "Estimated Business Income Through Debt Analysis"], "correct": 0, "marks": 2, "section": "Financial Literacy", "diff": DifficultyEnum.EASY},
    {"text": "Pareto Principle (80/20 rule) applied to business means:", "options": ["80% of your time should be spent on 20% of customers", "80% of results come from 20% of causes — focus on high-impact activities", "Work expands to fill available time (that's Parkinson's Law)", "Teams work best at 80% capacity"], "correct": 1, "marks": 3, "section": "Business Principles", "diff": DifficultyEnum.MEDIUM},
]
_n = add_questions(mgmt_questions, category=CategoryEnum.MANAGEMENT, domain=DomainEnum.BUSINESS_ANALYST)
print(f"✅ Added {_n} new Management questions ({len(mgmt_questions) - _n} already existed)")

# ═══════════════════════════════════════════════════════════════════════════
# NON-IT / APTITUDE QUESTIONS — 25 Questions
# ═══════════════════════════════════════════════════════════════════════════
non_it_questions = [
    {"text": "A train travels A→B at 80 km/h, returns at 60 km/h. Average speed for the whole journey?", "options": ["70 km/h", "68.57 km/h", "72 km/h", "65 km/h"], "correct": 1, "marks": 4, "section": "Quantitative", "diff": DifficultyEnum.HARD, "explanation": "Harmonic mean: 2×80×60/(80+60) = 9600/140 ≈ 68.57 km/h"},
    {"text": "Company has 500 employees: 60% female. 30% of females and 20% of males have MBAs. Total MBAs?", "options": ["130", "140", "150", "125"], "correct": 0, "marks": 4, "section": "Percentage", "diff": DifficultyEnum.HARD, "explanation": "Females: 300 × 0.30 = 90. Males: 200 × 0.20 = 40. Total: 130"},
    {"text": "15 machines produce 900 units in 8 hours. How many units do 20 machines produce in 6 hours?", "options": ["800", "850", "900", "1000"], "correct": 2, "marks": 4, "section": "Work & Time", "diff": DifficultyEnum.EXPERT, "explanation": "Rate = 900/(15×8) = 7.5 units/machine/hour. Output = 20×6×7.5 = 900"},
    {"text": "P(20,5) — selecting 5 people for different roles from 20 candidates:", "options": ["1,860,480", "15,504", "100,000", "3,628,800"], "correct": 0, "marks": 4, "section": "Permutation", "diff": DifficultyEnum.EXPERT, "explanation": "20×19×18×17×16 = 1,860,480"},
    {"text": "20% discount then 10% additional discount on discounted price. Total discount?", "options": ["30%", "28%", "25%", "32%"], "correct": 1, "marks": 4, "section": "Percentage", "diff": DifficultyEnum.HARD, "explanation": "100→80→72. Discount = 100-72 = 28%"},
    {"text": "Price rises 25% then falls 25%. Net change:", "options": ["0%", "-6.25%", "+6.25%", "-2.5%"], "correct": 1, "marks": 3, "section": "Percentage Tricks", "diff": DifficultyEnum.HARD},
    {"text": "'Perspicacious' most nearly means:", "options": ["Confused and hesitant", "Having keen insight; sharp-minded", "Very talkative", "Stubborn"], "correct": 1, "marks": 3, "section": "Vocabulary", "diff": DifficultyEnum.HARD},
    {"text": "Choose grammatically correct: A client angrily complains. Your BEST professional response:", "options": ["Defend your company immediately and firmly", "Apologize, empathize, take ownership, offer immediate solution", "Blame the client for misusing the product", "Escalate to your manager immediately always"], "correct": 1, "marks": 4, "section": "Customer Communication", "diff": DifficultyEnum.MEDIUM},
    {"text": "Correct version: 'The team have decided to changes their approach.'", "options": ["The team has decided to change their approach.", "The team have decided to change their approach.", "The team has decided to changing their approach.", "The sentence has no error."], "correct": 0, "marks": 2, "section": "English Grammar", "diff": DifficultyEnum.MEDIUM},
    {"text": "Series: A, C, F, J, O, ___", "options": ["T", "U", "V", "S"], "correct": 1, "marks": 3, "section": "Pattern Recognition", "diff": DifficultyEnum.HARD},
    {"text": "If all politicians are lawyers and some politicians are honest, then:", "options": ["All lawyers are honest", "Some lawyers are honest politicians", "No lawyers are politicians", "All honest people are politicians"], "correct": 1, "marks": 4, "section": "Logical Deduction", "diff": DifficultyEnum.HARD},
    {"text": "A salesperson targets ₹5L/month. She achieves ₹3.5L. Achievement %:", "options": ["70%", "65%", "75%", "80%"], "correct": 0, "marks": 1, "section": "Calculation", "diff": DifficultyEnum.EASY},
    {"text": "Which does NOT belong: Circle, Sphere, Triangle, Square", "options": ["Circle", "Sphere", "Triangle", "Square"], "correct": 1, "marks": 2, "section": "Spatial Reasoning", "diff": DifficultyEnum.MEDIUM, "explanation": "Circle, Triangle, Square are 2D shapes. Sphere is 3D."},
    {"text": "You discover a colleague consistently takes credit for your work. You:", "options": ["Do the same in return", "Confront them publicly in a meeting", "Document contributions carefully, then address it privately and directly first", "Complain to everyone on the team"], "correct": 2, "marks": 4, "section": "Workplace Situations", "diff": DifficultyEnum.HARD},
    {"text": "Rearrange to chronological order: 1:She applied. 2:She got selected. 3:Resume prepared. 4:Found posting. 5:Interview.", "options": ["4,3,1,5,2", "3,4,1,5,2", "4,1,3,5,2", "1,3,4,5,2"], "correct": 0, "marks": 2, "section": "Verbal Reasoning", "diff": DifficultyEnum.MEDIUM},
    {"text": "Most effective email subject line:", "options": ["Following up", "Action Required: Q4 Report Review by Friday 5PM", "Hi there", "Important: Please Read"], "correct": 1, "marks": 2, "section": "Professional Writing", "diff": DifficultyEnum.MEDIUM},
    {"text": "Active listening BEST practices:", "options": ["Formulate your reply while they speak to save time", "Maintain eye contact, paraphrase to confirm, ask clarifying questions", "Nod continuously to show engagement", "Listen only when you agree with the speaker"], "correct": 1, "marks": 3, "section": "Communication", "diff": DifficultyEnum.MEDIUM},
    {"text": "A project team misses a milestone due to unclear roles. As coordinator, you:", "options": ["Blame the team leads in the report", "Create a RACI matrix (Responsible, Accountable, Consulted, Informed)", "Call a blame-sharing retrospective", "Accept it and move on without action"], "correct": 1, "marks": 4, "section": "Project Coordination", "diff": DifficultyEnum.HARD},
    {"text": "Critical thinking primarily means:", "options": ["Criticizing others' ideas systematically", "Objectively analyzing information to form a well-reasoned, evidence-based judgment", "Thinking about problems in a negative way", "Being skeptical of absolutely everything"], "correct": 1, "marks": 2, "section": "Critical Thinking", "diff": DifficultyEnum.MEDIUM},
    {"text": "SWOT stands for:", "options": ["Sales, Work, Operations, Timeline", "Strengths, Weaknesses, Opportunities, Threats", "Strategy, Workflow, Objectives, Targets", "Systems, Work, Output, Tasks"], "correct": 1, "marks": 1, "section": "Business Basics", "diff": DifficultyEnum.EASY},
    {"text": "You receive a task with unclear instructions. You should:", "options": ["Figure it out yourself — shows initiative", "Ask for clarification immediately with specific questions listed", "Do nothing until clarity arrives on its own", "Make assumptions and proceed without informing anyone"], "correct": 1, "marks": 3, "section": "Workplace Readiness", "diff": DifficultyEnum.MEDIUM},
    {"text": "In formal email writing, BCC is used to:", "options": ["Send an urgent copy", "Include recipients without others knowing — often for compliance/audit trails", "Mark email as confidential", "CC = copy, BCC = bad carbon copy"], "correct": 1, "marks": 2, "section": "Professional Skills", "diff": DifficultyEnum.MEDIUM},
    {"text": "Word MOST opposite to 'Procrastinate':", "options": ["Delay", "Execute", "Plan", "Organize"], "correct": 1, "marks": 2, "section": "Vocabulary", "diff": DifficultyEnum.MEDIUM},
    {"text": "Presentation best practice:", "options": ["Include as many slides as possible to show thoroughness", "Clear structure: hook, insight, call-to-action; visual-first, max 1 idea/slide", "Only use text slides — visuals are distracting", "Exactly 10 slides — no more, no less"], "correct": 1, "marks": 3, "section": "Communication Skills", "diff": DifficultyEnum.MEDIUM},
    {"text": "Time management principle: you have 10 tasks. Which do you do first?", "options": ["Easiest tasks first to build momentum", "Most urgent AND most important (Eisenhower Matrix top-right quadrant)", "Whatever your boss asks first regardless of importance", "Hardest tasks first to get them out of the way"], "correct": 1, "marks": 3, "section": "Priority & Planning", "diff": DifficultyEnum.HARD},
]
_n = add_questions(non_it_questions, category=CategoryEnum.NON_IT)
print(f"✅ Added {_n} new Non-IT Aptitude questions ({len(non_it_questions) - _n} already existed)")

# ═══════════════════════════════════════════════════════════════════════════
# HR / TALENT ACQUISITION — 15 Questions
# ═══════════════════════════════════════════════════════════════════════════
hr_questions = [
    {"text": "Candidate looks perfect on paper but performs poorly in interview. Next step:", "options": ["Reject immediately based on interview", "Try a structured work simulation to see real-world performance", "Hire based on resume strength only", "Check references only"], "correct": 1, "marks": 4, "section": "Talent Acquisition", "diff": DifficultyEnum.HARD},
    {"text": "'Unconscious bias' in hiring refers to:", "options": ["Deliberately discriminating against candidates", "Automatic stereotyping influencing decisions without conscious awareness", "Checking candidate references", "Bias only in salary negotiations"], "correct": 1, "marks": 3, "section": "D&I", "diff": DifficultyEnum.MEDIUM},
    {"text": "Employee files grievance about their manager. HR's FIRST step:", "options": ["Side with the employee — they came to you", "Side with the manager — they're more senior", "Conduct confidential, unbiased investigation following documented policy", "Mediate immediately without investigation"], "correct": 2, "marks": 4, "section": "Employee Relations", "diff": DifficultyEnum.HARD},
    {"text": "EVP (Employee Value Proposition) is:", "options": ["Salary package only", "Total value exchange: rewards, culture, growth, purpose — for skills and time", "Legal employment contract", "Job description and responsibilities"], "correct": 1, "marks": 3, "section": "Employer Branding", "diff": DifficultyEnum.MEDIUM},
    {"text": "Kirkpatrick Model Level 3 (Behavior) measures:", "options": ["How participants felt about the training", "What knowledge was gained", "Whether behavior changed on the job after training", "Business results achieved from training"], "correct": 2, "marks": 4, "section": "L&D", "diff": DifficultyEnum.HARD},
    {"text": "What is 'structured interviewing'?", "options": ["Interviews in a nice office", "All candidates asked identical questions, scored on same rubric", "Only senior HR conducts interviews", "Written tests instead of conversations"], "correct": 1, "marks": 3, "section": "Recruitment", "diff": DifficultyEnum.MEDIUM},
    {"text": "Time-to-hire metric starts from:", "options": ["When candidate applies", "When job req is approved/opened", "When first interview is scheduled", "When offer is made"], "correct": 1, "marks": 3, "section": "Recruitment Metrics", "diff": DifficultyEnum.HARD},
    {"text": "STAR interview method stands for:", "options": ["Skills, Tasks, Actions, Results", "Situation, Task, Action, Result", "Strength, Teamwork, Attitude, Reliability", "Strategy, Training, Accountability, Review"], "correct": 1, "marks": 2, "section": "Interviewing", "diff": DifficultyEnum.EASY},
    {"text": "Offer was accepted but candidate reneges 2 days before joining. Best practice:", "options": ["Blacklist them from future applications forever", "Keep in touch, understand what happened, maintain professionalism, warm up backup candidates", "Sue them for breach of contract", "Post about it on LinkedIn"], "correct": 1, "marks": 4, "section": "Candidate Management", "diff": DifficultyEnum.HARD},
    {"text": "What is 'talent pipelining'?", "options": ["Hiring only from specific colleges", "Building relationships with potential candidates before positions are open", "Using LinkedIn only for recruitment", "Internal promotions only"], "correct": 1, "marks": 3, "section": "Strategic Talent Acquisition", "diff": DifficultyEnum.MEDIUM},
    {"text": "Employee engagement survey shows 40% 'actively disengaged.' This most impacts:", "options": ["Payroll costs primarily", "Productivity, customer satisfaction, and 2-3× higher turnover costs", "Office equipment budgets", "HR team workload only"], "correct": 1, "marks": 4, "section": "Employee Engagement", "diff": DifficultyEnum.HARD},
    {"text": "HRIS stands for:", "options": ["Human Resource Information System", "HR Interview Scheduling Software", "Human Relations Integration Service", "Hiring and Recruitment Intelligence System"], "correct": 0, "marks": 1, "section": "HR Technology", "diff": DifficultyEnum.EASY},
    {"text": "A high-performing team member asks for 40% salary hike. Market data shows 20% is fair. You:", "options": ["Reject immediately — policy is policy", "Accept to retain top talent regardless of market data", "Have transparent conversation with market data, explore total comp, discuss growth path", "Promote them to justify the raise"], "correct": 2, "marks": 4, "section": "Compensation", "diff": DifficultyEnum.HARD},
    {"text": "Succession planning is most important for:", "options": ["Entry-level positions only", "All critical roles where departure would significantly impact operations", "Only C-suite executives", "Roles that are hard to fill externally"], "correct": 1, "marks": 3, "section": "Strategic HR", "diff": DifficultyEnum.MEDIUM},
    {"text": "Culture add vs culture fit in hiring — why prefer 'culture add'?", "options": ["Culture add means less experienced candidates", "Culture add brings diversity of thought; culture fit can create homogeneity and blind spots", "They mean the same thing in modern HR", "Culture fit is always better for team harmony"], "correct": 1, "marks": 4, "section": "D&I", "diff": DifficultyEnum.HARD},
]
_n = add_questions(hr_questions, category=CategoryEnum.HR, domain=DomainEnum.HR_GENERALIST)
print(f"✅ Added {_n} new HR & Talent Acquisition questions ({len(hr_questions) - _n} already existed)")

# ═══════════════════════════════════════════════════════════════════════════
# FINANCE / CA QUESTIONS — 15 Questions
# ═══════════════════════════════════════════════════════════════════════════
finance_questions = [
    {"text": "Closing stock is UNDERSTATED. Effect on net profit:", "options": ["Overstated", "Understated", "No effect", "Cannot determine without tax rate"], "correct": 1, "marks": 4, "section": "Inventory", "diff": DifficultyEnum.HARD, "explanation": "Understated closing stock → overstated COGS → understated gross profit → understated net profit"},
    {"text": "If CA = ₹8L and CL = ₹3L, the current ratio is:", "options": ["2.0", "2.67", "1.5", "3.0"], "correct": 1, "marks": 2, "section": "Ratios", "diff": DifficultyEnum.MEDIUM, "explanation": "Current Ratio = CA/CL = 8/3 = 2.67"},
    {"text": "GST is charged at every stage of value addition. This is because GST is:", "options": ["A cascading tax like old Excise + VAT", "A multi-stage tax with input tax credit eliminating tax-on-tax", "A single-point tax on manufacturer", "A customs duty on imports only"], "correct": 1, "marks": 4, "section": "Taxation", "diff": DifficultyEnum.HARD},
    {"text": "Under Companies Act 2013, books of accounts must be maintained for:", "options": ["5 years", "8 years", "10 years", "Permanently"], "correct": 1, "marks": 3, "section": "Company Law", "diff": DifficultyEnum.HARD},
    {"text": "EBITDA margin formula:", "options": ["Net Profit / Revenue × 100", "EBITDA / Revenue × 100", "Operating Income / EBITDA × 100", "Gross Profit / EBITDA × 100"], "correct": 1, "marks": 3, "section": "Financial Analysis", "diff": DifficultyEnum.MEDIUM},
    {"text": "Deferred tax liability arises when:", "options": ["Accounting profit exceeds taxable profit", "Taxable profit exceeds accounting profit — tax paid now for future benefit", "Tax rate changes", "There are losses"], "correct": 0, "marks": 4, "section": "Taxation", "diff": DifficultyEnum.EXPERT, "explanation": "DTL: when accounting profit > taxable profit, you'll owe more tax later — recognize liability now."},
    {"text": "Debt-to-Equity ratio of 3:1 means:", "options": ["Company has ₹3 equity for every ₹1 debt — very safe", "Company is highly leveraged — ₹3 debt per ₹1 equity — risk dependent on industry", "Ideal ratio for all industries", "Company will definitely default"], "correct": 1, "marks": 3, "section": "Financial Ratios", "diff": DifficultyEnum.HARD},
    {"text": "Which inventory valuation method gives highest profit during inflation?", "options": ["FIFO — first in, first out (older cheaper goods as COGS)", "LIFO — last in, first out (newer expensive goods as COGS)", "Weighted Average", "Specific Identification"], "correct": 0, "marks": 4, "section": "Inventory Accounting", "diff": DifficultyEnum.HARD, "explanation": "FIFO uses older (cheaper) costs as COGS during inflation → lower COGS → higher profit."},
    {"text": "NPV (Net Present Value) rule: invest if NPV is:", "options": ["Negative — means high return", "Positive — project creates value above the discount rate", "Zero — means break even", "Above 10% always"], "correct": 1, "marks": 3, "section": "Investment Appraisal", "diff": DifficultyEnum.MEDIUM},
    {"text": "Working capital cycle improvement means:", "options": ["Longer collection period", "Shorter time from cash invested to cash received from sales", "Higher inventory holding", "Delayed supplier payments always"], "correct": 1, "marks": 3, "section": "Working Capital", "diff": DifficultyEnum.MEDIUM},
    {"text": "A company has ₹50L revenue, 60% gross margin, ₹20L operating expenses. EBIT:", "options": ["₹10L", "₹30L", "₹20L", "₹50L"], "correct": 0, "marks": 4, "section": "P&L Analysis", "diff": DifficultyEnum.EXPERT, "explanation": "Gross Profit = 50L×60% = 30L. EBIT = 30L - 20L = ₹10L"},
    {"text": "AS 9 (Accounting Standard 9) deals with:", "options": ["Fixed Assets", "Revenue Recognition", "Inventories", "Cash Flow Statements"], "correct": 1, "marks": 2, "section": "Accounting Standards", "diff": DifficultyEnum.MEDIUM},
    {"text": "Price-to-Earnings (P/E) ratio of 50 for a company growing at 5% annually suggests:", "options": ["Fairly valued — standard ratio", "Potentially overvalued relative to its growth rate (PEG > 1)", "Massively undervalued — buy immediately", "P/E ratio is irrelevant for valuation"], "correct": 1, "marks": 4, "section": "Equity Valuation", "diff": DifficultyEnum.HARD},
    {"text": "A firm's quick ratio is 0.8. This means:", "options": ["Very strong liquidity position", "Cannot cover current liabilities without selling inventory — liquidity concern", "Perfect ratio for all industries", "Ratio is too high — needs reducing"], "correct": 1, "marks": 3, "section": "Liquidity Analysis", "diff": DifficultyEnum.HARD},
    {"text": "Transfer pricing is most relevant for:", "options": ["SME domestic transactions", "Transactions between related entities across different tax jurisdictions", "Retail pricing strategy", "Government procurement"], "correct": 1, "marks": 4, "section": "International Taxation", "diff": DifficultyEnum.EXPERT},
]
_n = add_questions(finance_questions, category=CategoryEnum.FINANCE, domain=DomainEnum.CA_FINANCE)
print(f"✅ Added {_n} new Finance/CA questions ({len(finance_questions) - _n} already existed)")

# ═══════════════════════════════════════════════════════════════════════════
# SOCIAL MEDIA / CREATIVE — 15 Questions
# ═══════════════════════════════════════════════════════════════════════════
creative_questions = [
    {"text": "Your Instagram Reel: 100K views, 50 new followers. Primary issue:", "options": ["Content quality is bad", "No clear CTA or compelling reason to follow", "Hashtags are wrong", "Wrong posting time"], "correct": 1, "marks": 4, "section": "Growth Strategy", "diff": DifficultyEnum.HARD},
    {"text": "Brand offers collaboration without #ad disclosure. You:", "options": ["Accept — more authentic without disclosure", "Decline or require disclosure per ASCI/FTC guidelines", "Accept if you like the product", "Ask for more money and accept"], "correct": 1, "marks": 4, "section": "Ethics & Compliance", "diff": DifficultyEnum.HARD},
    {"text": "Which metric BEST indicates content quality and depth of engagement?", "options": ["Reach (impressions)", "Saves + Shares — indicate content worth returning to", "Follower count", "Post frequency"], "correct": 1, "marks": 3, "section": "Analytics", "diff": DifficultyEnum.MEDIUM},
    {"text": "YouTube CPM = ₹150, monetizable views = 200,000. Estimated revenue:", "options": ["₹30,000", "₹3,000", "₹15,000", "₹1,50,000"], "correct": 0, "marks": 4, "section": "Monetization", "diff": DifficultyEnum.HARD, "explanation": "(Views/1000) × CPM = 200 × ₹150 = ₹30,000"},
    {"text": "Best content strategy for consistent growth:", "options": ["Post whenever inspired", "Post daily regardless of quality", "Define content pillars, batch-create, schedule, analyze weekly performance", "Copy trending content formats only"], "correct": 2, "marks": 4, "section": "Content Strategy", "diff": DifficultyEnum.HARD},
    {"text": "SEO means:", "options": ["Social Engine Optimization", "Search Engine Optimization — improving organic visibility in search results", "Sales and E-commerce Operations", "Social Engagement Opportunities"], "correct": 1, "marks": 1, "section": "Digital Marketing", "diff": DifficultyEnum.EASY},
    {"text": "A/B testing in digital marketing tests:", "options": ["Two different products simultaneously", "Two versions of content/ad to see which performs better", "AB as in Advanced Backend processes", "Morning vs evening posting times only"], "correct": 1, "marks": 2, "section": "Testing & Optimization", "diff": DifficultyEnum.MEDIUM},
    {"text": "Click-through rate (CTR) formula:", "options": ["Impressions / Clicks × 100", "Clicks / Impressions × 100", "Conversions / Clicks × 100", "Revenue / Clicks × 100"], "correct": 1, "marks": 2, "section": "Analytics", "diff": DifficultyEnum.MEDIUM},
    {"text": "Highest engagement on Instagram typically comes from:", "options": ["Stories only", "Reels (short-form video) — highest organic reach currently", "Carousel posts always", "Text posts"], "correct": 1, "marks": 3, "section": "Platform Strategy", "diff": DifficultyEnum.MEDIUM},
    {"text": "A brand's social media crisis: negative viral post about them. You manage their account. First action:", "options": ["Delete the original negative post", "Acknowledge it publicly, take the conversation offline, resolve transparently", "Post positive content to drown it out", "Ignore it — it will pass"], "correct": 1, "marks": 4, "section": "Crisis Management", "diff": DifficultyEnum.HARD},
    {"text": "What is 'hook' in short-form video content?", "options": ["The closing call-to-action", "The first 1-3 seconds that stop the scroll and compel watching", "The background music choice", "The video thumbnail"], "correct": 1, "marks": 3, "section": "Content Creation", "diff": DifficultyEnum.MEDIUM},
    {"text": "Email marketing open rate industry average is approximately:", "options": ["5-10%", "15-25%", "40-60%", "1-3%"], "correct": 1, "marks": 2, "section": "Email Marketing", "diff": DifficultyEnum.MEDIUM},
    {"text": "Content repurposing means:", "options": ["Copying others' content", "Transforming one piece of content across multiple formats and platforms", "Posting the same content on all platforms simultaneously", "Deleting old content regularly"], "correct": 1, "marks": 3, "section": "Content Strategy", "diff": DifficultyEnum.MEDIUM},
    {"text": "The primary difference between organic and paid reach:", "options": ["Organic is always better", "Organic = earned through content quality; Paid = purchased visibility — both have strategic roles", "Paid reach is more trustworthy to audiences", "They reach identical audiences"], "correct": 1, "marks": 3, "section": "Digital Marketing", "diff": DifficultyEnum.MEDIUM},
    {"text": "Ideal UI/UX principle: 'Don't make me think' refers to:", "options": ["Users should not need to read instructions", "Interfaces should be so intuitive users never feel confused or uncertain", "Designers shouldn't overthink their work", "Products should auto-fill everything"], "correct": 1, "marks": 4, "section": "UI/UX Principles", "diff": DifficultyEnum.HARD},
]
_n = add_questions(creative_questions, category=CategoryEnum.CREATIVE, domain=DomainEnum.SOCIAL_MEDIA)
print(f"✅ Added {_n} new Creative & Social Media questions ({len(creative_questions) - _n} already existed)")

db.commit()
db.close()
print("\n" + "="*60)
print("🚀 CareerCompass World-Class Seed Complete!")
print("="*60)
print(f"✅ Admin: admin@simplemagics.com / Admin@123")
print(f"✅ Profile Questions: {len(profile_questions)}")
print(f"✅ IT Technical: {len(it_questions)}")
print(f"✅ Management: {len(mgmt_questions)}")
print(f"✅ Non-IT Aptitude: {len(non_it_questions)}")
print(f"✅ HR & Talent: {len(hr_questions)}")
print(f"✅ Finance & CA: {len(finance_questions)}")
print(f"✅ Creative & Social: {len(creative_questions)}")
total = len(profile_questions)+len(it_questions)+len(mgmt_questions)+len(non_it_questions)+len(hr_questions)+len(finance_questions)+len(creative_questions)
print(f"\n📊 TOTAL QUESTIONS IN DB: {total}")
print("="*60)
