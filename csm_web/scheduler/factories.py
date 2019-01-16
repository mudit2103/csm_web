import factory
import factory.fuzzy
from datetime import timedelta
from django.utils import timezone
import random
from django.core import management
from django.conf import settings
from .models import Course, Section, Spacetime, Profile, User, Attendance, Override


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Sequence(lambda n: "CS%d" % n)
    valid_until = factory.Faker("date_between", start_date="-1y", end_date="+1y")
    enrollment_start = factory.LazyAttribute(
        lambda o: timezone.make_aware(factory.Faker(
            "date_time_between_dates",
            datetime_start=o.valid_until - timedelta(weeks=17),
            datetime_end=o.valid_until - timedelta(weeks=10),
        ).generate({}))
    )
    enrollment_end = factory.LazyAttribute(
        lambda o: timezone.make_aware(factory.Faker(
            "date_time_between_dates",
            datetime_start=o.enrollment_start,
            datetime_end=o.valid_until,
        ).generate({}))
    )


BUILDINGS = ("Cory", "Soda", "Kresge", "Moffitt")
DAY_OF_WEEK_DB_CHOICES = [
    db_value for db_value, display_name in Spacetime.DAY_OF_WEEK_CHOICES
]


class SpacetimeFactory(factory.DjangoModelFactory):
    class Meta:
        model = Spacetime

    location = factory.LazyFunction(
        lambda: "%s %d" % (random.choice(BUILDINGS), random.randint(1, 500))
    )
    start_time = factory.Faker("time_object")
    duration = factory.LazyFunction(lambda: timedelta(minutes=random.choice((60, 90))))
    day_of_week = factory.fuzzy.FuzzyChoice(DAY_OF_WEEK_DB_CHOICES)


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(
        lambda n: "%s%d" % (factory.Faker("name").generate({}).replace(" ", "_"), n)
    )


ROLE_DB_CHOICES = [db_value for db_value, display_name in Profile.ROLE_CHOICES]


class ProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = Profile

    leader = factory.SubFactory("scheduler.factories.ProfileFactory")
    course = factory.SubFactory(CourseFactory)
    role = factory.fuzzy.FuzzyChoice(ROLE_DB_CHOICES)
    user = factory.SubFactory(UserFactory)
    section = factory.SubFactory(
        "scheduler.factories.SectionFactory", course=factory.SelfAttribute("..course")
    )


class SectionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Section

    course = factory.SubFactory(CourseFactory)
    default_spacetime = factory.SubFactory(SpacetimeFactory)
    capacity = factory.LazyFunction(lambda: random.randint(3, 6))
    mentor = factory.SubFactory(
        ProfileFactory, course=factory.SelfAttribute("..course")
    )


class AttendanceFactory(factory.DjangoModelFactory):
    class Meta:
        model = Attendance

    presence = factory.fuzzy.FuzzyChoice(Attendance.PRESENCE_CHOICES)
    section = factory.SubFactory(SectionFactory)
    attendee = factory.SubFactory(ProfileFactory)


class OverrideFactory(factory.DjangoModelFactory):
    class Meta:
        model = Override

    @factory.lazy_attribute
    def week_start(obj):
        start_date = factory.Faker(
            "date_between_dates",
            date_start=obj.section.course.enrollment_start.date(),
            date_end=obj.section.course.valid_until,
        ).generate({})
        start_date -= timedelta(days=start_date.weekday())
        return start_date

    spacetime = factory.SubFactory(SpacetimeFactory)
    section = factory.SubFactory(SectionFactory)


WEEKDAY_MAP = {
    number: pair[0] for number, pair in enumerate(Spacetime.DAY_OF_WEEK_CHOICES)
}


def create_attendances_for(student):
    today = timezone.datetime.today().date()
    current_date = student.course.enrollment_start.date()
    while (
        WEEKDAY_MAP[current_date.weekday()]
        != student.section.default_spacetime.day_of_week
    ):
        current_date += timedelta(days=1)
    while current_date < student.course.valid_until:
        if current_date < today:
            AttendanceFactory.create(
                attendee=student,
                section=student.section,
                week_start=current_date - timedelta(days=current_date.weekday()),
            )
        else:
            # Students cannot have attended or not attended sections that haven't happened yet
            AttendanceFactory.create(
                attendee=student,
                section=student.section,
                week_start=current_date - timedelta(days=current_date.weekday()),
                presence="",
            )
        current_date += timedelta(weeks=1)


def create_section_for(mentor):
    section = SectionFactory.create(course=mentor.course, mentor=mentor)
    students = ProfileFactory.create_batch(
        random.randint(1, section.capacity),
        course=section.course,
        leader=mentor,
        section=section,
        role=Profile.STUDENT,
    )
    for student in students:
        create_attendances_for(student)
    return section


def complicate_data():
    for course in Course.objects.all():
        mentors = course.profile_set.filter(
            role__in=(Profile.JUNIOR_MENTOR, Profile.SENIOR_MENTOR)
        )
        other_course_sections = Section.objects.exclude(course=course)
        for _ in range(mentors.count() // 4):
            # randomly make 25% of mentors students in other courses
            mentor = random.choice(mentors)
            section = random.choice(other_course_sections)
            if section.current_student_count < section.capacity:
                mentor_student_profile = Profile.objects.create(
                    section=section,
                    leader=section.mentor,
                    course=section.course,
                    user=mentor.user,
                    role=Profile.STUDENT,
                )
                section.students.add(mentor_student_profile)
        for _ in range(mentors.count() // 4):
            # randomly assign 25% of mentors an additional section
            create_section_for(random.choice(mentors))
    for _ in range(Section.objects.count() // 4):
        # randomly create Overrides for 25% of sections
        OverrideFactory.create(section=random.choice(Section.objects.all()))


def generate_test_data(complicate=False):
    if not settings.DEBUG:
        print("This cannot be run in production! Aborting.")
        return
    management.call_command("flush", interactive=True)
    course_names = ("CS70", "CS61A", "CS61B", "CS61C", "EE16A")
    for course in (CourseFactory.create(name=name) for name in course_names):
        coordinators = ProfileFactory.create_batch(
            2, course=course, leader=None, section=None, role=Profile.COORDINATOR
        )
        senior_mentors = ProfileFactory.create_batch(
            random.randint(4, 10),
            course=course,
            leader=random.choice(coordinators),
            section=None,
            role=Profile.SENIOR_MENTOR,
        )
        for senior_mentor in senior_mentors:
            junior_mentors = ProfileFactory.create_batch(
                random.randint(4, 6),
                course=course,
                leader=senior_mentor,
                section=None,
                role=Profile.JUNIOR_MENTOR,
            )
            for junior_mentor in junior_mentors:
                create_section_for(junior_mentor)
    if complicate:
        complicate_data()
