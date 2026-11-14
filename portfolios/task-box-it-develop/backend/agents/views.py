from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PromptTemplate


class TemplateListView(APIView):
    def get(self, request):
        templates = PromptTemplate.objects.filter(is_active=True)
        return Response(
            {"templates": [{"id": t.id, "label": t.label, "prompt": t.prompt} for t in templates]}
        )
