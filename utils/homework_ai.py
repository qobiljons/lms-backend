"""
Utility functions for processing homework data for AI checking/grading.
These functions prepare homework and submission data in a format suitable for AI analysis.
"""

from typing import Dict, List, Optional

from apps.homework.models import Homework, HomeworkSubmission


def extract_homework_content(homework: Homework) -> Dict:
    """
    Extract homework content for AI processing.
    
    Returns:
        Dict with homework structure:
        {
            'id': int,
            'title': str,
            'description': str,
            'questions': List[Dict],
            'total_points': int,
            'lesson': {
                'title': str,
                'course': str,
                'content': str  # lesson content/description
            }
        }
    """
    return {
        'id': homework.id,
        'title': homework.title,
        'description': homework.description,
        'questions': homework.questions,                              
        'total_points': homework.total_points,
        'lesson': {
            'title': homework.lesson.title,
            'course': homework.lesson.course.title if homework.lesson.course else None,
            'content': homework.lesson.content if hasattr(homework.lesson, 'content') else None,
        }
    }


def extract_submission_content(submission: HomeworkSubmission) -> Dict:
    """
    Extract student submission for AI grading.
    
    Returns:
        Dict with submission structure:
        {
            'id': int,
            'student': str,
            'homework_id': int,
            'answers': List[Dict],  # student answers
            'status': str,
            'submitted_at': str,
            'files': List[str]  # file URLs
        }
    """
    return {
        'id': submission.id,
        'student': submission.student.username,
        'student_email': submission.student.email,
        'homework_id': submission.homework_id,
        'answers': submission.answers,                                          
        'status': submission.status,
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
        'files': submission.files,                     
    }


def prepare_for_ai_grading(homework: Homework, submission: HomeworkSubmission) -> Dict:
    """
    Prepare a complete dataset for AI grading.
    
    Combines homework questions with student answers in a format ready for AI processing.
    
    Returns:
        Dict structure:
        {
            'homework': {homework content},
            'submission': {submission content},
            'grading_items': [
                {
                    'question_index': int,
                    'question': str,
                    'expected_points': int,
                    'student_answer': str,
                    'student_files': List[str]
                },
                ...
            ]
        }
    """
    homework_data = extract_homework_content(homework)
    submission_data = extract_submission_content(submission)
    
                              
    answers_by_index = {
        ans.get('question_index', idx): ans 
        for idx, ans in enumerate(submission.answers)
    }
    
    grading_items = []
    for idx, question in enumerate(homework.questions):
        answer_data = answers_by_index.get(idx, {})
        grading_items.append({
            'question_index': idx,
            'question': question.get('question', ''),
            'expected_points': question.get('points', 0),
            'student_answer': answer_data.get('answer', ''),
            'student_files': [answer_data.get('file')] if answer_data.get('file') else [],
        })
    
    return {
        'homework': homework_data,
        'submission': submission_data,
        'grading_items': grading_items,
    }


def prepare_batch_grading(homework_id: int) -> List[Dict]:
    """
    Prepare all submissions for a homework for batch AI grading.
    
    Args:
        homework_id: ID of the homework
        
    Returns:
        List of grading datasets, one per submission
    """
    try:
        homework = Homework.objects.select_related('lesson', 'lesson__course').get(pk=homework_id)
    except Homework.DoesNotExist:
        return []
    
    submissions = HomeworkSubmission.objects.filter(
        homework=homework,
        status='submitted'
    ).select_related('student')
    
    return [
        prepare_for_ai_grading(homework, submission)
        for submission in submissions
    ]


def format_ai_prompt(grading_data: Dict) -> str:
    """
    Format grading data into a text prompt for AI.
    
    This creates a human-readable prompt that can be sent to an AI service
    for automated grading.
    
    Args:
        grading_data: Output from prepare_for_ai_grading()
        
    Returns:
        Formatted string prompt for AI
    """
    homework = grading_data['homework']
    submission = grading_data['submission']
    items = grading_data['grading_items']
    
    prompt = f"""HOMEWORK GRADING REQUEST

Homework: {homework['title']}
Course: {homework['lesson']['course']}
Lesson: {homework['lesson']['title']}
Total Points: {homework['total_points']}

Description:
{homework['description']}

Student: {submission['student']}
Submitted: {submission['submitted_at']}

QUESTIONS AND ANSWERS:

"""
    
    for item in items:
        prompt += f"""
Question {item['question_index'] + 1} ({item['expected_points']} points):
{item['question']}

Student Answer:
{item['student_answer']}

"""
        if item['student_files']:
            prompt += f"Attached Files: {', '.join(item['student_files'])}\n"
        
        prompt += "-" * 80 + "\n"
    
    prompt += """

Please provide:
1. A score for each question (out of the expected points)
2. Specific feedback for each answer
3. Overall feedback for the submission
4. Total score

Format your response as JSON:
{
    "overall_score": <total points earned>,
    "overall_feedback": "<general feedback>",
    "per_question": [
        {
            "question_index": 0,
            "score": <points earned>,
            "feedback": "<specific feedback>"
        },
        ...
    ]
}
"""
    
    return prompt


def extract_lesson_homework_summary(lesson_id: int) -> Dict:
    """
    Get a summary of all homework for a lesson.
    
    Useful for displaying homework overview to students or instructors.
    
    Args:
        lesson_id: ID of the lesson
        
    Returns:
        Dict with homework summary
    """
    from apps.lessons.models import Lesson
    
    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return {}
    
    homework_list = Homework.objects.filter(lesson=lesson).prefetch_related('submissions')
    
    return {
        'lesson_id': lesson.id,
        'lesson_title': lesson.title,
        'homework_count': homework_list.count(),
        'homework': [
            {
                'id': hw.id,
                'title': hw.title,
                'total_points': hw.total_points,
                'due_date': hw.due_date.isoformat() if hw.due_date else None,
                'question_count': len(hw.questions),
                'submission_count': hw.submissions.count(),
            }
            for hw in homework_list
        ]
    }
