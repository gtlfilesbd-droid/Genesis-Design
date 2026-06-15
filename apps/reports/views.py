import csv
import io
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.accounts.models import User, UserRole
from apps.designs.models import DesignRequest, DesignStatus
from apps.projects.models import Project


def _designer_performance_data(designer_id=None, project_id=None):
    designers = User.objects.filter(role=UserRole.DESIGNER, is_active=True)
    if designer_id:
        designers = designers.filter(pk=designer_id)
    rows = []
    for d in designers:
        qs = DesignRequest.objects.filter(assigned_designer=d)
        if project_id:
            qs = qs.filter(project_id=project_id)
        assigned = qs.count()
        completed = qs.filter(status=DesignStatus.COMPLETED).count()
        on_time = qs.filter(status=DesignStatus.COMPLETED, completion_date__lte=F('due_date')).count()
        corrections = qs.filter(revision_count__gt=0).count()
        completed_qs = qs.filter(status=DesignStatus.COMPLETED, completion_date__isnull=False)
        day_total, day_count = 0, 0
        for dr in completed_qs[:100]:
            if dr.completion_date and dr.created_at:
                day_total += (dr.completion_date - dr.created_at).total_seconds() / 86400
                day_count += 1
        avg_days_val = round(day_total / day_count, 1) if day_count else 0
        rate = round((completed / assigned * 100) if assigned else 0, 1)
        on_time_rate = round((on_time / completed * 100) if completed else 0, 1)
        score = min(100, round(rate * 0.5 + on_time_rate * 0.5))
        rows.append({
            'designer': d.get_full_name() or d.username,
            'assigned': assigned,
            'completed': completed,
            'on_time': on_time,
            'completion_rate': rate,
            'on_time_rate': on_time_rate,
            'avg_days': avg_days_val,
            'corrections': corrections,
            'score': score,
        })
    return rows


def _sla_compliance_data():
    designs = DesignRequest.objects.exclude(sla_due__isnull=True)
    total = designs.count()
    breached = designs.filter(sla_status='red').count()
    return {
        'total': total,
        'green': designs.filter(sla_status='green').count(),
        'yellow': designs.filter(sla_status='yellow').count(),
        'red': breached,
        'compliance_rate': round(((total - breached) / total * 100) if total else 100, 1),
    }


@login_required
@role_required(UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
def reports_index(request):
    tab = request.GET.get('tab', 'performance')
    designer_filter = request.GET.get('designer')
    project_filter = request.GET.get('project')
    delay_data = DesignRequest.objects.exclude(delay_source='').values(
        'design_number', 'delay_source', 'delay_duration_days', 'status'
    )[:50]
    project_rows = []
    for p in Project.objects.all():
        project_rows.append({
            'code': p.code,
            'name': p.client_name,
            'status': p.get_status_display(),
            'total': p.total_design_requests,
            'completed': p.completed_designs,
            'running': p.running_designs,
            'health': p.health_score,
            'pct': round(p.completed_designs / p.total_design_requests * 100) if p.total_design_requests else 0,
        })
    return render(request, 'reports/index.html', {
        'tab': tab,
        'designer_data': _designer_performance_data(designer_filter, project_filter),
        'sla_data': _sla_compliance_data(),
        'delay_data': delay_data,
        'project_data': project_rows,
        'designers': User.objects.filter(role=UserRole.DESIGNER, is_active=True),
        'projects': Project.objects.all(),
        'designer_filter': designer_filter,
        'project_filter': project_filter,
        'total_projects': Project.objects.count(),
        'total_designs': DesignRequest.objects.count(),
        'pending_designs': DesignRequest.objects.exclude(
            status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]
        ).count(),
    })


@login_required
@role_required(UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
def export_csv(request, report_type):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}.csv"'
    writer = csv.writer(response)

    if report_type == 'designer_performance':
        writer.writerow(['Designer', 'Assigned', 'Completed', 'Completion Rate %', 'Corrections'])
        for row in _designer_performance_data():
            writer.writerow([
                row['designer'], row['assigned'], row['completed'],
                row['completion_rate'], row['corrections'],
            ])
    elif report_type == 'project_progress':
        writer.writerow(['Project Code', 'Name', 'Status', 'Total Designs', 'Completed', 'Health Score'])
        for p in Project.objects.all():
            writer.writerow([
                p.code, p.name, p.status, p.total_design_requests,
                p.completed_designs, p.health_score,
            ])
    elif report_type == 'sla_compliance':
        writer.writerow(['Design Number', 'Project', 'SLA Status', 'Due Date', 'Status'])
        for d in DesignRequest.objects.exclude(sla_due__isnull=True):
            writer.writerow([
                d.design_number, d.project.code, d.sla_status,
                d.sla_due, d.status,
            ])
    elif report_type == 'delay_analysis':
        writer.writerow(['Design Number', 'Delay Source', 'Delay Days', 'Status'])
        for d in DesignRequest.objects.exclude(delay_source=''):
            writer.writerow([
                d.design_number, d.delay_source, d.delay_duration_days, d.status,
            ])
    elif report_type == 'verification':
        writer.writerow(['Design Number', 'Verifier', 'Status', 'Revisions'])
        for d in DesignRequest.objects.filter(verified_by__isnull=False):
            writer.writerow([
                d.design_number,
                d.verified_by.get_full_name() if d.verified_by else '',
                d.status, d.revision_count,
            ])
    else:
        writer.writerow(['Metric', 'Value'])
        sla = _sla_compliance_data()
        writer.writerow(['Total Projects', Project.objects.count()])
        writer.writerow(['Total Designs', DesignRequest.objects.count()])
        writer.writerow(['SLA Compliance %', sla['compliance_rate']])

    return response


@login_required
@role_required(UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
def export_excel(request, report_type):
    try:
        import openpyxl
    except ImportError:
        return export_csv(request, report_type)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = report_type

    if report_type == 'designer_performance':
        ws.append(['Designer', 'Assigned', 'Completed', 'Completion Rate %', 'Corrections'])
        for row in _designer_performance_data():
            ws.append([
                row['designer'], row['assigned'], row['completed'],
                row['completion_rate'], row['corrections'],
            ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{report_type}.xlsx"'
    wb.save(response)
    return response


@login_required
@role_required(UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
def export_pdf(request, report_type):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return export_csv(request, report_type)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont('Helvetica-Bold', 14)
    p.drawString(50, 800, f'Genesis Design - {report_type.replace("_", " ").title()}')
    p.setFont('Helvetica', 10)
    y = 770

    if report_type == 'designer_performance':
        for row in _designer_performance_data():
            p.drawString(50, y, f"{row['designer']}: {row['completed']}/{row['assigned']} ({row['completion_rate']}%)")
            y -= 15
            if y < 50:
                p.showPage()
                y = 800
    elif report_type == 'management_summary':
        sla = _sla_compliance_data()
        lines = [
            f'Total Projects: {Project.objects.count()}',
            f'Total Designs: {DesignRequest.objects.count()}',
            f'SLA Compliance: {sla["compliance_rate"]}%',
            f'Breached SLA: {sla["red"]}',
        ]
        for line in lines:
            p.drawString(50, y, line)
            y -= 15

    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}.pdf"'
    return response
