from rest_framework.response import Response


def success_response(data=None, status_code=200):
    return Response(
        {
            "status": "success",
            "data": data,
        },
        status=status_code,
    )


def error_response(
    code,
    message,
    details=None,
    status_code=400,
):
    return Response(
        {
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
        status=status_code,
    )