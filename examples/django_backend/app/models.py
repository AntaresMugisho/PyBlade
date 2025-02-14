from django.db import models
from django.utils.translation import gettext as _


# Create your models here.
class Task(models.Model):
    class TaskStatus(models.TextChoices):
        PENDING = ("PD", _("Pending"))
        IN_PROGRESS = ("PR", _("In progress"))
        PAUSED = ("PS", _("Paused"))
        FINISHED = ("FN", _("Finished"))

    title = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    status = models.CharField(max_length=2, choices=TaskStatus.choices, default=TaskStatus.PENDING)
