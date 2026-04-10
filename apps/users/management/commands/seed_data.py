"""
Management command to seed the database with realistic dummy data.
Usage: python manage.py seed_data
"""

import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

FIRST_NAMES_MALE = [
    "James", "Robert", "Michael", "David", "Daniel",
    "Alexander", "Ethan", "Benjamin", "Lucas", "Mason",
    "Noah", "Liam", "Oliver", "William", "Henry",
]
FIRST_NAMES_FEMALE = [
    "Emma", "Sophia", "Olivia", "Ava", "Isabella",
    "Mia", "Charlotte", "Amelia", "Harper", "Evelyn",
    "Aria", "Chloe", "Lily", "Grace", "Zoe",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Anderson", "Taylor", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson", "Robinson", "Clark",
    "Lewis", "Lee", "Walker", "Hall", "Allen",
    "Young", "King", "Wright", "Lopez", "Hill",
]

COURSES = [
    {
        "title": "Python Programming",
        "description": "Learn Python from basics to advanced topics including OOP, decorators, generators, and real-world project development.",
        "price": Decimal("149.99"),
        "lessons": [
            ("Introduction to Python", "Getting started with Python: installation, REPL, variables, and data types."),
            ("Control Flow & Functions", "Conditionals, loops, function definitions, *args/**kwargs, and scope."),
            ("Data Structures", "Lists, tuples, sets, dictionaries, comprehensions, and when to use each."),
            ("Object-Oriented Programming", "Classes, inheritance, polymorphism, dunder methods, and design patterns."),
            ("File I/O & Error Handling", "Reading/writing files, context managers, exception handling, and logging."),
        ],
    },
    {
        "title": "JavaScript Fundamentals",
        "description": "Master modern JavaScript including ES6+, async programming, DOM manipulation, and Node.js basics.",
        "price": Decimal("129.99"),
        "lessons": [
            ("JavaScript Basics", "Variables, data types, operators, and type coercion in modern JS."),
            ("Functions & Closures", "Arrow functions, higher-order functions, closures, and the event loop."),
            ("DOM Manipulation", "Selecting elements, event listeners, creating dynamic UIs without frameworks."),
            ("Async JavaScript", "Promises, async/await, fetch API, and handling concurrent operations."),
        ],
    },
    {
        "title": "Data Science with Python",
        "description": "Explore data analysis, visualization, and machine learning foundations using pandas, matplotlib, and scikit-learn.",
        "price": Decimal("199.99"),
        "lessons": [
            ("NumPy & Pandas Basics", "Array operations, DataFrame creation, indexing, filtering, and groupby."),
            ("Data Cleaning & Wrangling", "Handling missing data, merging datasets, reshaping, and feature engineering."),
            ("Data Visualization", "Matplotlib, Seaborn, and Plotly for creating insightful charts and dashboards."),
            ("Intro to Machine Learning", "Supervised vs unsupervised learning, train/test split, and scikit-learn pipelines."),
            ("Regression & Classification", "Linear regression, logistic regression, decision trees, and model evaluation."),
        ],
    },
    {
        "title": "Web Development Bootcamp",
        "description": "Full-stack web development covering HTML, CSS, JavaScript, React, Node.js, and deployment.",
        "price": Decimal("249.99"),
        "lessons": [
            ("HTML & CSS Foundations", "Semantic HTML, CSS Grid, Flexbox, responsive design, and accessibility."),
            ("Responsive Design", "Media queries, mobile-first approach, CSS variables, and modern layout techniques."),
            ("React Fundamentals", "Components, JSX, state, props, hooks, and the virtual DOM."),
            ("Backend with Node.js", "Express.js, REST APIs, middleware, authentication, and database integration."),
        ],
    },
    {
        "title": "Machine Learning",
        "description": "Deep dive into ML algorithms, neural networks, and practical model deployment with TensorFlow and PyTorch.",
        "price": Decimal("299.99"),
        "lessons": [
            ("ML Foundations", "Feature engineering, bias-variance tradeoff, cross-validation, and hyperparameter tuning."),
            ("Ensemble Methods", "Random forests, gradient boosting, XGBoost, and stacking strategies."),
            ("Neural Networks", "Perceptrons, backpropagation, activation functions, and building networks from scratch."),
            ("Deep Learning with TensorFlow", "Keras API, CNNs, transfer learning, and model saving/serving."),
            ("Model Deployment", "Flask/FastAPI serving, Docker containers, and cloud deployment patterns."),
        ],
    },
    {
        "title": "Database Systems",
        "description": "Relational and NoSQL databases: SQL mastery, PostgreSQL, MongoDB, indexing, and query optimization.",
        "price": Decimal("159.99"),
        "lessons": [
            ("SQL Fundamentals", "SELECT, JOINs, subqueries, aggregation, and window functions."),
            ("Database Design", "Normalization, ER diagrams, constraints, and schema design best practices."),
            ("PostgreSQL Advanced", "CTEs, JSON operations, full-text search, extensions, and performance tuning."),
        ],
    },
]

GROUPS = [
    ("Morning Batch A", "Monday/Wednesday/Friday morning sessions, 9:00 AM - 12:00 PM"),
    ("Afternoon Batch B", "Tuesday/Thursday afternoon sessions, 2:00 PM - 5:00 PM"),
    ("Evening Batch C", "Monday/Wednesday evening sessions, 6:00 PM - 9:00 PM"),
    ("Weekend Batch D", "Saturday/Sunday morning sessions, 10:00 AM - 1:00 PM"),
]

HOMEWORK_TEMPLATES = [
    {
        "title": "Practice Exercises",
        "description": "Complete the following practice problems to reinforce what you learned in this lesson.",
        "questions": [
            {"question": "Explain the key concepts covered in this lesson in your own words.", "points": 25},
            {"question": "Write a program that demonstrates the main topic of this lesson.", "points": 40},
            {"question": "What are the common mistakes beginners make with this topic? How can they be avoided?", "points": 15},
            {"question": "Provide a real-world example where this concept is applied.", "points": 20},
        ],
    },
    {
        "title": "Mini Project",
        "description": "Build a small project applying the concepts from this lesson.",
        "questions": [
            {"question": "Design and implement a solution to the given problem statement.", "points": 50},
            {"question": "Write tests for your implementation.", "points": 25},
            {"question": "Document your approach and any trade-offs you considered.", "points": 25},
        ],
    },
]

DIRECT_MESSAGES = [
    ["Hi! I had a question about the last lesson.", "Sure, what's on your mind?", "I didn't understand the part about closures. Could you explain?", "Of course! A closure is a function that remembers variables from its outer scope even after that scope has finished executing.", "Oh that makes sense now! Thank you!"],
    ["Hey, when is the next assignment due?", "It's due next Friday. Make sure to submit before midnight.", "Got it, thanks!"],
    ["Could you review my code when you get a chance?", "Sure, send it over and I'll take a look this evening.", "Awesome, just pushed it to the repo. Thanks!"],
]

GROUP_MESSAGES = [
    "Good morning everyone! Don't forget we have a quiz tomorrow.",
    "Can someone share the notes from last class?",
    "I uploaded the notes to the shared folder.",
    "Thanks! That's really helpful.",
    "Reminder: homework is due by end of day Friday.",
    "Does anyone want to form a study group for the exam?",
    "I'm in! Let's meet at the library at 4 PM.",
    "Great, see you all there.",
    "The instructor just posted new practice problems.",
    "Has anyone started on the mini project yet?",
]


class Command(BaseCommand):
    help = "Seed the database with realistic dummy data for development"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete all existing data before seeding")

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        from apps.attendance.models import AttendanceRecord, AttendanceSession
        from apps.courses.models import Course
        from apps.groups.models import Group
        from apps.homework.models import Homework, HomeworkSubmission
        from apps.lessons.models import Lesson
        from apps.messaging.models import (
            DirectConversation,
            DirectMessage,
            GroupConversation,
            GroupMessage,
        )
        from apps.payments.models import CoursePurchase, Payment

        User = get_user_model()
        now = timezone.now()

        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            for model in [
                HomeworkSubmission, Homework, AttendanceRecord, AttendanceSession,
                GroupMessage, GroupConversation, DirectMessage, DirectConversation,
                CoursePurchase, Payment, Lesson, Group, Course,
            ]:
                model.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS("Flushed."))

                     
        self.stdout.write("Creating users...")
        all_first_names = FIRST_NAMES_MALE + FIRST_NAMES_FEMALE
        random.shuffle(all_first_names)

        def make_user(first, last, role, idx):
            username = f"{first.lower()}.{last.lower()}"
            email = f"{username}@lms.dev"
                               
            if User.objects.filter(username=username).exists():
                username = f"{username}{idx}"
                email = f"{username}@lms.dev"
            user = User.objects.create_user(
                email=email,
                username=username,
                password="password123",
                first_name=first,
                last_name=last,
                role=role,
            )
                                                       
            user.date_joined = now - datetime.timedelta(days=random.randint(1, 90))
            user.save(update_fields=["date_joined"])
            return user

        admins = []
        for i in range(2):
            first = all_first_names[i]
            last = LAST_NAMES[i]
            admins.append(make_user(first, last, "admin", i))

        instructors = []
        for i in range(5):
            first = all_first_names[2 + i]
            last = LAST_NAMES[2 + i]
            instructors.append(make_user(first, last, "instructor", i))

        students = []
        for i in range(30):
            first = all_first_names[(7 + i) % len(all_first_names)]
            last = LAST_NAMES[(7 + i) % len(LAST_NAMES)]
            students.append(make_user(first, last, "student", i))

        self.stdout.write(self.style.SUCCESS(
            f"  {len(admins)} admins, {len(instructors)} instructors, {len(students)} students"
        ))

                       
        self.stdout.write("Creating courses...")
        courses = []
        for cd in COURSES:
            course, _ = Course.objects.get_or_create(
                title=cd["title"],
                defaults={
                    "description": cd["description"],
                    "price": cd["price"],
                },
            )
            courses.append((course, cd["lessons"]))
        self.stdout.write(self.style.SUCCESS(f"  {len(courses)} courses"))

                       
        self.stdout.write("Creating lessons...")
        all_lessons = []
        for course, lesson_defs in courses:
            instructor = random.choice(instructors)
            for title, content in lesson_defs:
                lesson, _ = Lesson.objects.get_or_create(
                    course=course,
                    title=title,
                    defaults={
                        "content": content,
                        "user": instructor,
                    },
                )
                all_lessons.append(lesson)
        self.stdout.write(self.style.SUCCESS(f"  {len(all_lessons)} lessons"))

                      
        self.stdout.write("Creating groups...")
        groups = []
        student_pool = list(students)
        random.shuffle(student_pool)
        students_per_group = len(student_pool) // len(GROUPS)

        for idx, (name, desc) in enumerate(GROUPS):
            group, created = Group.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "instructor": instructors[idx % len(instructors)],
                },
            )
            if created:
                                 
                start = idx * students_per_group
                end = start + students_per_group
                if idx == len(GROUPS) - 1:
                    end = len(student_pool)
                group_students = student_pool[start:end]
                group.students.set(group_students)
                                    
                group_courses = random.sample([c for c, _ in courses], k=min(3, len(courses)))
                group.courses.set(group_courses)
            groups.append(group)
        self.stdout.write(self.style.SUCCESS(f"  {len(groups)} groups"))

                        
        self.stdout.write("Creating homework assignments...")
        homeworks = []
        for lesson in all_lessons:
                                     
            num_hw = random.randint(1, 2)
            for i in range(num_hw):
                template = HOMEWORK_TEMPLATES[i % len(HOMEWORK_TEMPLATES)]
                total_pts = sum(q["points"] for q in template["questions"])
                due = now + datetime.timedelta(days=random.randint(-14, 14))
                hw, created = Homework.objects.get_or_create(
                    lesson=lesson,
                    title=template["title"],
                    defaults={
                        "description": template["description"],
                        "questions": template["questions"],
                        "total_points": total_pts,
                        "due_date": due,
                        "created_by": random.choice(instructors),
                    },
                )
                if created:
                                                          
                    hw_created = now - datetime.timedelta(days=random.randint(7, 60))
                    Homework.objects.filter(pk=hw.pk).update(created_at=hw_created)
                homeworks.append(hw)
        self.stdout.write(self.style.SUCCESS(f"  {len(homeworks)} homework assignments"))

                                    
        self.stdout.write("Creating homework submissions...")
        submission_count = 0
        for hw in homeworks:
                                              
            submitters = random.sample(students, k=random.randint(5, min(20, len(students))))
            for student in submitters:
                if HomeworkSubmission.objects.filter(homework=hw, student=student).exists():
                    continue
                status = random.choices(
                    ["submitted", "graded", "draft"],
                    weights=[30, 50, 20],
                )[0]
                score = None
                graded_at = None
                graded_by = None
                feedback = ""
                submitted_at = now - datetime.timedelta(days=random.randint(1, 45))

                if status == "graded":
                    score = Decimal(str(round(random.uniform(50, hw.total_points), 2)))
                    graded_at = submitted_at + datetime.timedelta(days=random.randint(1, 5))
                    graded_by = random.choice(instructors)
                    feedback = random.choice([
                        "Good work! Keep it up.",
                        "Nice effort, but review the section on error handling.",
                        "Excellent submission! Very thorough.",
                        "Some improvements needed. See comments above.",
                        "Great progress from your last submission!",
                    ])

                answers = [
                    {"question_index": qi, "answer": f"Student answer for question {qi + 1}"}
                    for qi in range(len(hw.questions))
                ]

                sub = HomeworkSubmission.objects.create(
                    homework=hw,
                    student=student,
                    answers=answers,
                    status=status,
                    score=score,
                    feedback=feedback,
                    submitted_at=submitted_at if status != "draft" else None,
                    graded_at=graded_at,
                    graded_by=graded_by,
                )
                                       
                HomeworkSubmission.objects.filter(pk=sub.pk).update(
                    created_at=submitted_at - datetime.timedelta(hours=random.randint(1, 24))
                )
                submission_count += 1
        self.stdout.write(self.style.SUCCESS(f"  {submission_count} submissions"))

                          
        self.stdout.write("Creating attendance sessions & records...")
        session_count = 0
        record_count = 0
        statuses = ["attended", "attended_online", "late", "absent", "excused"]
        status_weights = [55, 20, 10, 10, 5]

        for group in groups:
            group_courses = list(group.courses.all())
            group_students = list(group.students.all())
            if not group_courses or not group_students:
                continue

                                                   
            num_sessions = random.randint(10, 15)
            session_dates = set()
            while len(session_dates) < num_sessions:
                d = (now - datetime.timedelta(days=random.randint(1, 60))).date()
                if d.weekday() < 6:                
                    session_dates.add(d)

            for sd in sorted(session_dates):
                course = random.choice(group_courses)
                if AttendanceSession.objects.filter(group=group, course=course, session_date=sd).exists():
                    continue
                session = AttendanceSession(
                    group=group,
                    course=course,
                    taken_by=group.instructor,
                    session_date=sd,
                    note="",
                )
                session.save()
                                       
                AttendanceSession.objects.filter(pk=session.pk).update(
                    created_at=timezone.make_aware(datetime.datetime.combine(sd, datetime.time(9, 0)))
                )
                session_count += 1

                                          
                for student in group_students:
                    st = random.choices(statuses, weights=status_weights)[0]
                    AttendanceRecord.objects.create(
                        session=session,
                        student=student,
                        status=st,
                    )
                    record_count += 1

        self.stdout.write(self.style.SUCCESS(f"  {session_count} sessions, {record_count} records"))

                        
        self.stdout.write("Creating payments & course purchases...")
        payment_count = 0
        purchase_count = 0
        for student in students:
                                                
            num_purchases = random.randint(1, 3)
            purchased_courses = random.sample([c for c, _ in courses], k=min(num_purchases, len(courses)))
            for course in purchased_courses:
                if CoursePurchase.objects.filter(user=student, course=course).exists():
                    continue
                pay_date = now - datetime.timedelta(days=random.randint(1, 90))
                payment = Payment(
                    user=student,
                    amount=course.price,
                    currency="usd",
                    status="succeeded",
                    stripe_payment_intent_id=f"pi_seed_{student.pk}_{course.pk}",
                )
                payment.save()
                Payment.objects.filter(pk=payment.pk).update(created_at=pay_date)
                payment_count += 1

                CoursePurchase.objects.create(
                    user=student,
                    course=course,
                    payment=payment,
                    amount=course.price,
                )
                purchase_count += 1
        self.stdout.write(self.style.SUCCESS(f"  {payment_count} payments, {purchase_count} purchases"))

                        
        self.stdout.write("Creating messages...")
        dm_count = 0
        gm_count = 0

                                                               
        for msg_list in DIRECT_MESSAGES:
            instructor = random.choice(instructors)
            student = random.choice(students)
                                                              
            a_id, b_id = sorted([instructor.pk, student.pk])
            user_a = User.objects.get(pk=a_id)
            user_b = User.objects.get(pk=b_id)

            conv, _ = DirectConversation.objects.get_or_create(
                user_a=user_a, user_b=user_b,
            )
            participants = [instructor, student]
            for i, body in enumerate(msg_list):
                sender = participants[i % 2]
                msg_time = now - datetime.timedelta(days=random.randint(1, 30), hours=random.randint(0, 12))
                dm = DirectMessage.objects.create(
                    conversation=conv,
                    sender=sender,
                    body=body,
                    is_read=True,
                )
                DirectMessage.objects.filter(pk=dm.pk).update(created_at=msg_time)
                dm_count += 1

                             
        for group in groups:
            conv, _ = GroupConversation.objects.get_or_create(group=group)
            members = list(group.students.all()) + ([group.instructor] if group.instructor else [])
            if not members:
                continue
            for body in random.sample(GROUP_MESSAGES, k=min(6, len(GROUP_MESSAGES))):
                sender = random.choice(members)
                msg_time = now - datetime.timedelta(days=random.randint(1, 20), hours=random.randint(0, 12))
                gm = GroupMessage.objects.create(
                    conversation=conv,
                    sender=sender,
                    body=body,
                )
                GroupMessage.objects.filter(pk=gm.pk).update(created_at=msg_time)
                gm_count += 1

        self.stdout.write(self.style.SUCCESS(f"  {dm_count} direct messages, {gm_count} group messages"))

        self.stdout.write(self.style.SUCCESS("\nSeeding complete!"))
        self.stdout.write(f"  Login with any seeded user using password: password123")
        self.stdout.write(f"  Admin example: {admins[0].username}")
        self.stdout.write(f"  Instructor example: {instructors[0].username}")
        self.stdout.write(f"  Student example: {students[0].username}")
