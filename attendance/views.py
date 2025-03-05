from datetime import timedelta, datetime
import calendar
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib import messages
from .models import EmployeeDetails,Attendance,LeaveApplication,Profile
from django.contrib.auth import logout
from django.utils.timezone import now
import qrcode
import uuid
import os
from django.conf import settings



def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        employee_id = request.POST['employee_id']
        date_of_birth = request.POST.get('date_of_birth', '')  # Optional field
        phone_number = request.POST.get('phone_number', '')
        address = request.POST.get('address', '')
        designation = request.POST.get('designation', '')

        # Save employee details (hashing password for security)
        employee = EmployeeDetails(
            username=username,
            email=email,
            password=password,  
            employee_id=employee_id,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
            address=address,
            designation=designation
        )
        employee.save()

        return redirect('login_view')  # Redirect to login page after successful registration

    return render(request, 'register.html')

# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        # Authenticate user
        try:
            user = EmployeeDetails.objects.get(username=username)
            if user.password == password:  # Ensure you're handling password properly (not hashed here)
                # Manually create the session
                request.session['user_id'] = user.id  # Store user ID in session
                request.session['username'] = user.username  # Optionally, store username
                
                return redirect('dashboard')  # Redirect to dashboard
            else:
                messages.error(request, 'Invalid username or password')
        except EmployeeDetails.DoesNotExist:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    user = EmployeeDetails.objects.get(id=user_id)  # Get EmployeeDetails instead of User

    # Fetch the profile picture from the Profile table
    profile = Profile.objects.filter(employee=user).first()  # Use 'employee' instead of 'user'
    profile_picture_url = profile.profile_picture.url if profile and profile.profile_picture else '/static/images/default_profile.jpg'

    # Fetch all attendance records for the user
    attendance_records = Attendance.objects.filter(user=user)

    # Get current month and year
    current_month = now().month
    current_year = now().year

    # Filter attendance for the current month
    monthly_attendance = attendance_records.filter(date__year=current_year, date__month=current_month)

    # Calculate monthly working days (days with check-in)
    monthly_working_days = monthly_attendance.filter(check_in__isnull=False).count()

    # Get the number of days in the current month
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    
    calendar_data = []
    total_hours = timedelta(0)  # Track total working hours

    for day in range(1, days_in_month + 1):
        date = datetime(current_year, current_month, day)
        day_name = date.strftime('%A')  # Get the weekday name

        record = monthly_attendance.filter(date=date).first()
        
        if record and record.check_in and record.check_out:
            worked_hours = record.check_out - record.check_in
            status = "P"  # Present
            total_hours += worked_hours
        else:
            worked_hours = timedelta(0)
            status = "H" if day_name == "Sunday" else "A"  # Mark Sundays as Holiday
        
        calendar_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'day': day_name,
            'status': status,
            'hours': str(worked_hours) if worked_hours > timedelta(0) else "00:00:00"
        })

    context = {
        'user': user,
        'monthly_working_days': monthly_working_days,
        'calendar_data': calendar_data,
        'total_hours': str(total_hours),
        'profile_picture_url': profile_picture_url  # Include profile picture in context
    }

    return render(request, 'dashboard.html', context)

def check_in(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')  # Redirect if session is missing

    try:
        user = EmployeeDetails.objects.get(id=user_id)  # ✅ Use EmployeeDetails, not User
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    today = now().date()
    attendance, created = Attendance.objects.get_or_create(
        user=user, date=today, defaults={'check_in': now()}
    )

    if not created and not attendance.check_in:
        attendance.check_in = now()
        attendance.save()

    return redirect('dashboard')

def check_out(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        user = EmployeeDetails.objects.get(id=user_id)  # ✅ Fix reference
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    today = now().date()
    try:
        attendance = Attendance.objects.get(user=user, date=today)
        if not attendance.check_out:
            attendance.check_out = now()
            attendance.save()
    except Attendance.DoesNotExist:
        pass  

    return redirect('dashboard')


# Logout view
def user_logout(request):
    logout(request)
    return redirect('login_view')  # Redirect to login page after logging out

def apply_leave(request):
    if request.method == "POST":
        leave_type = request.POST.get("leave_type")
        start_date = request.POST.get("from_date")
        end_date = request.POST.get("to_date")
        reason = request.POST.get("reason")

        if not leave_type or not start_date or not end_date or not reason:
            messages.error(request, "⚠️ All fields are required!")
            return redirect("apply_leave")

        # ✅ Get EmployeeDetails instance for the logged-in user
        try:
            employee = EmployeeDetails.objects.get(username=request.session.get("username"))  # Fetch using session
        except EmployeeDetails.DoesNotExist:
            messages.error(request, "Employee details not found. Please contact admin.")
            return redirect("apply_leave")

        # ✅ Save leave application
        LeaveApplication.objects.create(
            user=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        ).save()

        messages.success(request, "✅ Leave request submitted successfully!")
        return redirect("apply_leave")

    return render(request, "apply_leave.html")

def profile_view(request):
    user_id = request.session.get('user_id')  # Get user ID from session
    if not user_id:
        return redirect('login')  # Redirect to login if not authenticated

    try:
        user = EmployeeDetails.objects.get(id=user_id)  # Fetch user details
        profile, created = Profile.objects.get_or_create(employee=user)  # Ensure profile exists
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        # Update profile picture if uploaded
        if 'profile_image' in request.FILES:
            profile.profile_picture = request.FILES['profile_image']
            profile.save()  # Save only if a new profile picture is uploaded

        return redirect('profile')  # Refresh profile page

    return render(request, 'profile.html', {'user': user, 'profile': profile})
def generate_qr(request):
    # Generate a unique registration URL
    unique_id = uuid.uuid4()
    registration_url = f"http://127.0.0.1:8000/register/{unique_id}/"

    # Generate QR code
    qr = qrcode.make(registration_url)

    # Define the QR code file path
    qr_dir = os.path.join(settings.MEDIA_ROOT, "qr_codes")
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)

    qr_path = os.path.join(qr_dir, f"{unique_id}.png")
    qr.save(qr_path)

    # Get the media URL for the QR code
    qr_url = f"{settings.MEDIA_URL}qr_codes/{unique_id}.png"

    return render(request, "qr_display.html", {"qr_url": qr_url})

