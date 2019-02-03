# Generated by Django 2.1.5 on 2019-01-27 19:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("scheduler", "0001_initial")]

    operations = [
        migrations.RemoveField(model_name="section", name="mentor"),
        migrations.AlterField(
            model_name="profile",
            name="section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="scheduler.Section",
            ),
        ),
    ]
