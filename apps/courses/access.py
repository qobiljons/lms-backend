def student_has_assigned_course(user, course):
    return course.groups.filter(students=user).exists()

def instructor_has_assigned_course(user, course):
    return course.groups.filter(instructor=user).exists()

def student_has_purchased_course(user, course):
    from apps.payments.models import CoursePurchase
    return CoursePurchase.objects.filter(user=user, course=course).exists()

def get_course_access_denial_message(user, course):
    if user.role == "admin":
        return None
    if user.role == "instructor":
        if instructor_has_assigned_course(user, course):
            return None
        return "This course is not assigned to you."
    if user.role != "student":
        return "You do not have access to this course."
    if not student_has_assigned_course(user, course):
        return "This course is not assigned to your group."
    if course.price > 0 and not student_has_purchased_course(user, course):
        return "Please make a purchase to see the course content."
    return None

def user_has_course_access(user, course):
    return get_course_access_denial_message(user, course) is None
