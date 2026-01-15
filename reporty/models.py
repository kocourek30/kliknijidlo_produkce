from django.db import models

class ReportDummy(models.Model):
    """Dummy pro admin – netvorí tabulku."""
    title = models.CharField(max_length=100, default='Částky z objednávek')

    class Meta:
        managed = False
        verbose_name = 'Report Částky'
        verbose_name_plural = 'Reporty Částky'
