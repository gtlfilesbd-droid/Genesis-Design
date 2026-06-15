from django.urls import resolve


class ProjectContextMiddleware:
    """Attach current_project / current_design to the request for permission context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_project = None
        request.current_design = None

        if request.user.is_authenticated:
            try:
                match = resolve(request.path)
                namespace = match.namespace
                url_name = match.url_name
                pk = match.kwargs.get('pk')

                if namespace == 'projects' and pk:
                    from apps.projects.models import Project
                    request.current_project = Project.objects.filter(pk=pk).first()
                elif namespace == 'requests' and pk:
                    from apps.designs.models import DesignRequest
                    design = DesignRequest.objects.select_related('project').filter(pk=pk).first()
                    if design:
                        request.current_design = design
                        request.current_project = design.project
                elif namespace == 'workflow' and pk:
                    from apps.designs.models import DesignRequest
                    design = DesignRequest.objects.select_related('project').filter(pk=pk).first()
                    if design:
                        request.current_design = design
                        request.current_project = design.project
            except Exception:
                pass

        return self.get_response(request)
