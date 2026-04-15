from rest_framework.response import Response

def response_builder(success=True, message="", data=None, status_code=200):
    return Response({
        "success": success,
        "message": message,
        "data": data,
        "code": status_code
    }, status=status_code)