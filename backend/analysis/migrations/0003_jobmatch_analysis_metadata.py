from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analysis", "0002_alter_jobmatch_education_score_and_more")]

    operations = [
        migrations.AddField(
            model_name="jobmatch",
            name="analysis_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
