from django.db import models

class ReportDummy(models.Model):
    """Dummy pro admin – netvorí tabulku."""
    title = models.CharField(max_length=100, default='Reporty')

    class Meta:
        managed = False
        verbose_name = 'Reporty'
        verbose_name_plural = 'Reporty'
