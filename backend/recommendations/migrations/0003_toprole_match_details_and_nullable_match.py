from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("recommendations", "0002_jobrole")]

    operations = [
        migrations.AddField(
            model_name="toprole",
            name="match_details",
            field=models.JSONField(blank=True, default=dict),
        ),
        # Expand the existing value domain to include unknown; preserve every old value.
        migrations.AlterField(
            model_name="toprole",
            name="match_percentage",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
