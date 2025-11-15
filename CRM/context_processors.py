from .models import Doubt, Assessment, Assignment, AssessmentSubmission, AssignmentSubmission, InternProfile

def pending_counts(request):
    if request.user.is_authenticated:
        # -----------------------
        # Pending Doubts
        # -----------------------
        pending_doubts_count = Doubt.objects.filter(resolved=False).count()

        # -----------------------
        # Get InternProfile for logged-in user
        # -----------------------
        try:
            intern_profile = InternProfile.objects.get(user=request.user)
        except InternProfile.DoesNotExist:
            intern_profile = None

        # -----------------------
        # Pending Assessments
        # -----------------------
        if intern_profile:
            submitted_assessments = AssessmentSubmission.objects.filter(
                intern=intern_profile
            ).values_list('assessment_id', flat=True)

            pending_assessments_count = Assessment.objects.exclude(
                id__in=submitted_assessments
            ).count()

            submitted_assignments = AssignmentSubmission.objects.filter(
                intern=intern_profile
            ).values_list('assignment_id', flat=True)

            pending_assignments_count = Assignment.objects.exclude(
                id__in=submitted_assignments
            ).count()
        else:
            pending_assessments_count = 0
            pending_assignments_count = 0

    else:
        pending_doubts_count = 0
        pending_assessments_count = 0
        pending_assignments_count = 0

    return {
        'pending_doubts_count': pending_doubts_count,
        'pending_assessments_count': pending_assessments_count,
        'pending_assignments_count': pending_assignments_count,
    }
