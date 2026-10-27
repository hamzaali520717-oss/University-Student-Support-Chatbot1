import django.db.models.deletion
from django.db import migrations, models


def backfill_program_department(apps, schema_editor):
    Department = apps.get_model("academics", "Department")
    Program = apps.get_model("academics", "Program")
    unset = Program.objects.filter(department__isnull=True)
    if not unset.exists():
        return
    default_department, _ = Department.objects.get_or_create(
        code="GEN", defaults={"name": "General"}
    )
    unset.update(department=default_department)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=150, unique=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="program",
            name="department",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="programs",
                to="academics.department",
            ),
        ),
        migrations.RunPython(backfill_program_department, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="program",
            name="department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="programs",
                to="academics.department",
            ),
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, unique=True)),
                ("title", models.CharField(max_length=150)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="courses",
                        to="academics.department",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Subject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("semester", models.PositiveSmallIntegerField()),
                ("credit_hours", models.PositiveSmallIntegerField()),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subjects",
                        to="academics.course",
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subjects",
                        to="academics.program",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
                "unique_together": {("program", "course", "semester")},
            },
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="accounts.studentprofile",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enrollments",
                        to="academics.subject",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
                "unique_together": {("student", "subject")},
            },
        ),
        migrations.CreateModel(
            name="SemesterPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("semester", models.PositiveSmallIntegerField()),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="semester_plans",
                        to="accounts.studentprofile",
                    ),
                ),
                (
                    "subjects",
                    models.ManyToManyField(related_name="semester_plans", to="academics.subject"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
                "unique_together": {("student", "semester")},
            },
        ),
        migrations.CreateModel(
            name="Attendance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("present", "Present"), ("absent", "Absent"), ("leave", "Leave")],
                        default="present",
                        max_length=10,
                    ),
                ),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_records",
                        to="academics.enrollment",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
                "unique_together": {("enrollment", "date")},
            },
        ),
    ]
