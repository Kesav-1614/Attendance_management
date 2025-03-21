from datetime import timedelta, datetime
import calendar
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib import messages
from django.urls import reverse
from .models import EmployeeDetails,Attendance,LeaveApplication,Profile,Role,Payroll,Break
from django.contrib.auth import logout
from django.utils.timezone import now
import qrcode
import uuid
import os
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .forms import PayrollForm
from django.db.models import Sum
from django.template.loader import get_template
from xhtml2pdf import pisa

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

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        try:
            user = EmployeeDetails.objects.get(username=username)

            if user.password == password:  # Ensure secure password handling
                # Store session data
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['designation'] = user.designation  # Store role

                # ✅ Fix: Ensure `designation` is not None
                designation = user.designation.lower() if user.designation else ""

                # Redirect based on designation
                if designation == "admin":
                    return redirect('admin_dashboard')  # Admin Panel
                else:
                    return redirect('dashboard')  # Employee Dashboard
                
            else:
                messages.error(request, 'Invalid username or password')
        
        except EmployeeDetails.DoesNotExist:
            messages.error(request, 'Invalid username or password')

    return render(request, 'login.html')

def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    user = EmployeeDetails.objects.get(id=user_id)

    profile = Profile.objects.filter(employee=user).first()
    profile_picture_url = profile.profile_picture.url if profile and profile.profile_picture else '/static/images/default_profile.jpg'

    current_month = now().month
    current_year = now().year
    attendance_records = Attendance.objects.filter(user=user)
    monthly_attendance = attendance_records.filter(date__year=current_year, date__month=current_month)
    monthly_working_days = monthly_attendance.filter(check_in__isnull=False).count()
    days_in_month = calendar.monthrange(current_year, current_month)[1]

    calendar_data = []
    total_hours = timedelta(0)

    for day in range(1, days_in_month + 1):
        date = datetime(current_year, current_month, day)
        day_name = date.strftime('%A')

        record = monthly_attendance.filter(date=date).first()
        if record:
            worked_hours = (record.check_out - record.check_in) if record.check_in and record.check_out else timedelta(0)
            total_hours += worked_hours

            # Get all breaks for this day
            breaks = record.break_set.all()
            break_details = []
            total_break_time = timedelta(0)

            for b in breaks:
                if b.break_in and b.break_out:
                    break_time = b.break_out - b.break_in
                    total_break_time += break_time
                    break_details.append({
                        'break_in': b.break_in.strftime('%H:%M:%S'),
                        'break_out': b.break_out.strftime('%H:%M:%S'),
                        'break_duration': str(break_time)
                    })

            status = "Present" if record.check_in and record.check_out else "Absent"
            calendar_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': day_name,
                'status': status,
                'hours': str(worked_hours) if worked_hours > timedelta(0) else "00:00:00",
                'total_break_time': str(total_break_time),
                'break_details': break_details
            })
        else:
            status = "Holiday" if day_name == "Sunday" else "Absent"
            calendar_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': day_name,
                'status': status,
                'hours': "00:00:00",
                'total_break_time': "00:00:00",
                'break_details': []
            })

    context = {
        'user': user,
        'monthly_working_days': monthly_working_days,
        'calendar_data': calendar_data,
        'total_hours': str(total_hours),
        'profile_picture_url': profile_picture_url
    }
    return render(request, 'dashboard.html', context)


def check_in(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')  # Redirect if session is missing

    try:
        user = EmployeeDetails.objects.get(id=user_id)  # ✅ Get EmployeeDetails
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    today = now().date()
    attendance, created = Attendance.objects.get_or_create(
        user=user, date=today,
        defaults={'check_in': now()}
    )

    # If record exists but check-in is missing, update it
    if not created and not attendance.check_in:
        attendance.check_in = now()
        attendance.save()

    return redirect('dashboard')

def check_out(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        user = EmployeeDetails.objects.get(id=user_id)
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    today = now().date()
    try:
        attendance = Attendance.objects.get(user=user, date=today)
        if not attendance.check_out:
            attendance.check_out = now()
            attendance.calculate_working_hours()  # ✅ Auto-update working hours
    except Attendance.DoesNotExist:
        pass  # No check-in recorded

    return redirect('dashboard')

def break_in(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        user = EmployeeDetails.objects.get(id=user_id)
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    today = now().date()
    attendance, created = Attendance.objects.get_or_create(user=user, date=today)

    # Create a new break entry only if the last break is closed
    last_break = attendance.break_set.filter(break_out__isnull=True).first()
    if not last_break:
        new_break = Break.objects.create(
            attendance=attendance,
            break_in=now()
        )
        new_break.save()

    return redirect('dashboard')


def break_out(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        user = EmployeeDetails.objects.get(id=user_id)
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    today = now().date()
    try:
        attendance = Attendance.objects.get(user=user, date=today)

        # Find the last break with no break_out and close it
        last_break = attendance.break_set.filter(break_out__isnull=True).first()
        if last_break:
            last_break.break_out = now()
            last_break.save()

            # Recalculate working hours to account for break time
            attendance.calculate_working_hours()
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
        role_types = request.POST.getlist("role_type")  # ✅ Get multiple roles
        start_date = request.POST.get("from_date")
        end_date = request.POST.get("to_date")
        reason = request.POST.get("reason")

        if not leave_type or not start_date or not end_date or not reason:
            messages.error(request, "⚠️ All fields are required!")
            return redirect("apply_leave")

        try:
            employee = EmployeeDetails.objects.get(username=request.session.get("username"))
        except EmployeeDetails.DoesNotExist:
            messages.error(request, "Employee details not found. Please contact admin.")
            return redirect("apply_leave")

        # ✅ Convert list to comma-separated string
        selected_roles = ', '.join(Role.objects.filter(id__in=role_types).values_list('name', flat=True))

        # ✅ Save leave application
        LeaveApplication.objects.create(
            user=employee,
            username=employee.username,
            leave_type=leave_type,
            role_type=selected_roles,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )

        messages.success(request, "✅ Leave request submitted successfully!")
        return redirect("apply_leave")

    roles = Role.objects.all()
    return render(request, "apply_leave.html", {"roles": roles})


def profile_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        user = EmployeeDetails.objects.get(id=user_id)
        profile, created = Profile.objects.get_or_create(employee=user)
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    if request.method == 'POST' and request.FILES.get('profile_image'):
        profile.profile_picture = request.FILES['profile_image']
        profile.save()  # Save profile with new image

        return redirect('profile')

    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'profile.html', context)

def admin_profile_view(request):
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

    return render(request, 'admin_profile.html', {'user': user, 'profile': profile})

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

# Admin
def admin_dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')  # Redirect if not logged in

    try:
        admin = EmployeeDetails.objects.get(id=request.session['user_id'])
    except EmployeeDetails.DoesNotExist:
        return redirect('login')

    if admin.designation.lower() != "admin":
        return redirect('dashboard')  # Redirect non-admin users

    employees = EmployeeDetails.objects.all()
    attendance_records = Attendance.objects.all().order_by('-date')
    pending_leaves = LeaveApplication.objects.filter(status="Pending")

    # ✅ Fix working hours calculation
    for record in attendance_records:
        if record.check_in and record.check_out:
            duration = record.check_out - record.check_in
            record.working_hours = duration.total_seconds() / 3600  # Convert seconds to hours
        else:
            record.working_hours = None  # No check-out yet

    context = {
        "admin": admin,
        "employees": employees,
        "attendance_records": attendance_records,
        "pending_leaves": pending_leaves,
    }

    return render(request, "admin_dashboard.html", context)

def leave_management(request):
    leave_requests = LeaveApplication.objects.filter(status="Pending")
    return render(request, 'leave_management.html', {'leave_requests': leave_requests})

def approve_leave(request, leave_id):
    leave = get_object_or_404(LeaveApplication, id=leave_id)
    leave.status = "Approved"
    leave.save()
    messages.success(request, f"Leave request for {leave.user.username} approved.")
    return redirect('leave_management')

def reject_leave(request, leave_id):
    leave = get_object_or_404(LeaveApplication, id=leave_id)
    leave.status = "Rejected"
    leave.save()
    messages.error(request, f"Leave request for {leave.user.username} rejected.")
    return redirect('leave_management')

def manage_employees(request):
    employees = EmployeeDetails.objects.all()  # Fetch all employees
    
    # Fetch profile pictures for employees
    employee_data = []
    for emp in employees:
        profile = Profile.objects.filter(employee=emp).first()
        profile_picture_url = profile.profile_picture.url if profile and profile.profile_picture else '/static/images/default_profile.jpg'
        
        employee_data.append({
            'id': emp.id,
            'name': emp.username,
            'designation': emp.designation,
            'email': emp.email,
            'profile_picture': profile_picture_url
        })

    context = {'employees': employee_data}
    return render(request, 'manage_employees.html', context)

# ✅ View Attendance - Show attendance for all employees
def view_attendance(request):
    attendance_records = Attendance.objects.select_related('user').order_by('check_in')
    
    for record in attendance_records:
        if record.check_in and record.check_out:
            duration = record.check_out - record.check_in
            # Format duration to HH:MM:SS format
            record.working_hours = str(timedelta(seconds=duration.total_seconds()))
        else:
            record.working_hours = 'N/A'  # If check-in or check-out is missing
    
    return render(request, 'view_attendance.html', {'attendance_records': attendance_records})

def select_employee(request):
    employees = EmployeeDetails.objects.all()  # Fetch all employees
    return render(request, 'select_employee.html', {'employees': employees})

def download_employee_attendance(request, employee_id):
    employee = get_object_or_404(EmployeeDetails, employee_id=employee_id)
    attendances = Attendance.objects.filter(user=employee)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{employee.username}_attendance.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Check-in', 'Check-out', 'Working Hours'])

    for attendance in attendances:
        check_in = attendance.check_in.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_in else 'N/A'
        check_out = attendance.check_out.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_out else 'N/A'

        # Calculate working hours dynamically
        if attendance.check_in and attendance.check_out:
            time_diff = attendance.check_out - attendance.check_in
            total_seconds = time_diff.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            working_hours = f"{hours}h {minutes}m"
        else:
            working_hours = 'N/A'

        writer.writerow([attendance.date.strftime('%Y-%m-%d'), check_in, check_out, working_hours])

    return response

def leave_status(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login_view')

    leaves = LeaveApplication.objects.filter(user_id=user_id).order_by('-start_date')

    context = {
        'leaves': leaves
    }
    return render(request, 'leave_status.html', context)

def fetch_employee_details(request, employee_id):
    try:
        employee = EmployeeDetails.objects.get(id=employee_id)

        # Calculate total working hours
        total_working_hours = Attendance.objects.filter(
            user=employee
        ).aggregate(total_hours=Sum('working_hours'))['total_hours'] or 0

        # Prepare employee data
        data = {
            'username': employee.username,
            'email': employee.email,
            'employee_id': employee.employee_id,
            'date_of_birth': employee.date_of_birth.strftime('%Y-%m-%d') if employee.date_of_birth else None,
            'phone_number': employee.phone_number,
            'address': employee.address,
            'designation': employee.designation,
            'total_working_hours': total_working_hours
        }

        return JsonResponse(data)

    except EmployeeDetails.DoesNotExist:
        
        return JsonResponse({'error': 'Employee not found'}, status=404)
    
# def generate_payroll(request):
#     if request.method == 'POST':
#         form = PayrollForm(request.POST)
#         if form.is_valid():
#             payroll = form.save(commit=False)
            
#             # Calculate total amount based on deduction and basic salary
#             payroll.total_amount = payroll.basic_salary - payroll.deduction
#             payroll.save()

#             return redirect('payroll_list')
#     else:
#         form = PayrollForm()

#     employees = EmployeeDetails.objects.all()
#     return render(request, 'generate_payroll.html', {'form': form, 'employees': employees})

def generate_payslip(request, payroll_id):
    payroll = get_object_or_404(Payroll, id=payroll_id)
    template_path = 'payslip_template.html'
    context = {'payroll': payroll}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payslip_{payroll_id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors generating the PDF')

    return response

        
def payroll_list(request):
    payrolls = Payroll.objects.all()
    return render(request, 'payroll_list.html', {'payrolls': payrolls})


def download_payroll_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payroll.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Employee', 'Pay Period Start', 'Pay Period End', 'Payment Date', 'Basic Salary', 'Deduction', 'Total Amount'])

    payrolls = Payroll.objects.all()
    for payroll in payrolls:
        writer.writerow([
            payroll.id,
            payroll.employee.username,
            payroll.pay_period_start,
            payroll.pay_period_end,
            payroll.payment_date,
            payroll.basic_salary if payroll.basic_salary else 0,
            payroll.deduction if payroll.deduction else 0,
            payroll.total_amount if payroll.total_amount else 0
        ])

    return response
