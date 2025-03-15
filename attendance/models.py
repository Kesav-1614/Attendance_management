# attendance/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from datetime import timedelta

class EmployeeDetails(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    employee_id = models.CharField(max_length=50, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)  # Date picker support
    phone_number = models.CharField(max_length=15, null=True, blank=True)  # Store phone number
    address = models.TextField(null=True, blank=True)  # Address field
    designation = models.CharField(max_length=100, null=True, blank=True)  # Employee designation

    def __str__(self):
        return self.username
    
class Attendance(models.Model):
    user = models.ForeignKey("EmployeeDetails", on_delete=models.CASCADE)
    username = models.CharField(max_length=150, editable=False)
    date = models.DateField(default=now)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    working_hours = models.IntegerField(null=True, blank=True)  # Store as seconds

    def calculate_working_hours(self):
        """Calculate working hours and store as seconds (int)."""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in  # timedelta
            self.working_hours = int(delta.total_seconds())  # ✅ Convert timedelta to seconds
        else:
            self.working_hours = None  # Reset if missing data
        self.save()

    def __str__(self):
        if self.working_hours is not None:
            hours = self.working_hours // 3600
            minutes = (self.working_hours % 3600) // 60
            return f"{self.username} - {self.date} ({hours}h {minutes}m)"
        return f"{self.username} - {self.date} (-)"
    
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class LeaveApplication(models.Model):
    LEAVE_TYPES = [
        ('Sick Leave', 'Sick Leave'),
        ('Casual Leave', 'Casual Leave'),
        ('Annual Leave', 'Annual Leave'),
        ('Unpaid Leave', 'Unpaid Leave'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey("EmployeeDetails", on_delete=models.CASCADE)
    username = models.CharField(max_length=150)
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)
    role_type = models.TextField()  # ✅ Change to TextField to store multiple roles as CSV
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
class Profile(models.Model):
    employee = models.OneToOneField(EmployeeDetails, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to="profile_pics/", default="profile_pics/default.jpg", blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.employee.username}"