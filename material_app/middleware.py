from django.utils import timezone


class TokenAuthMiddleware:
    """
    Token 認證中間件。
    流程：
      1. 每個請求進來，從 cookie 讀出 'auth_token'
      2. 去資料庫查找對應的 AuthToken
      3. 檢查是否過期 → 過期就刪除該 token
      4. 有效的話，將 Employee 物件掛到 request.employee
      5. 沒有有效 token，設 request.employee = None

    使用方式：
      - views 裡直接用 request.employee 判斷是否登入
      - request.employee is None → 未登入
      - request.employee.EmpID → 打工號
      - request.employee.Name  → 姓名
    """

    # 不需要登入的路徑（允許未登入訪問）
    EXEMPT_PATHS = [
        '/material/login/',
        '/material/logout/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.COOKIES.get('auth_token')
        request.employee = None  # 預設為空

        if token:
            from .models import AuthToken
            auth = AuthToken.objects.filter(Token=token).select_related('Employee').first()
            if auth and not auth.is_expired():  # 假設你有檢查過期的 method
                request.employee = auth.Employee

        return self.get_response(request)
