# JWT 认证系统实现指南

## 概述

本项目已实现完整的 JWT 认证系统，包括：
- 用户注册和登录
- JWT Token 管理
- 权限角色控制
- 前后端集成

## 后端实现

### 1. 数据库模型 (models.py)

#### UserRole 枚举
```python
class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"          # 管理员
    MANAGER = "manager"      # 经理
    USER = "user"            # 普通用户
    GUEST = "guest"          # 访客
```

#### User 模型
```python
class User(UserBase, table=True):
    id: Optional[int]
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
```

### 2. 认证模块 (src/auth/)

#### JWT 处理 (jwt_handler.py)
```python
from src.auth import create_access_token, verify_token

# 创建 Token
token = create_access_token(
    data={
        "sub": user.id,
        "username": user.username,
        "role": user.role.value
    },
    expires_delta=timedelta(minutes=60)
)

# 验证 Token
token_data = verify_token(token)
if token_data:
    print(f"User ID: {token_data.user_id}")
```

#### 密码处理 (password.py)
```python
from src.auth import hash_password, verify_password

# 哈希密码
hashed = hash_password("my_password")

# 验证密码
is_valid = verify_password("my_password", hashed)
```

#### 依赖注入和权限管理 (dependencies.py)
```python
from src.auth import get_current_user, require_role
from models import UserRole

# 在路由中使用
@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user)
):
    # current_user 是当前认证用户
    return {"user": current_user}

# 角色检查
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    # 只有 ADMIN 可以访问
```

### 3. API 端点 (src/api/routes/auth.py)

#### 注册
```
POST /api/auth/register
Content-Type: application/json

{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
}

Response: 201 Created
{
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
}
```

#### 登录
```
POST /api/auth/login
Content-Type: application/json

{
    "username": "john_doe",
    "password": "secure_password"
}

Response: 200 OK
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        ...
    }
}
```

#### 获取当前用户
```
GET /api/auth/me
Authorization: Bearer <access_token>

Response: 200 OK
{
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    ...
}
```

#### 刷新 Token
```
POST /api/auth/refresh
Authorization: Bearer <access_token>

Response: 200 OK
{
    "access_token": "new_token...",
    "token_type": "bearer",
    "user": {...}
}
```

#### 用户管理
```
# 获取用户列表（仅限管理员）
GET /api/users?skip=0&limit=10
Authorization: Bearer <access_token>

# 获取特定用户
GET /api/users/{user_id}
Authorization: Bearer <access_token>

# 更新用户信息
PUT /api/users/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json
{
    "full_name": "Jane Doe",
    "email": "jane@example.com"
}

# 删除用户（仅限管理员）
DELETE /api/users/{user_id}
Authorization: Bearer <access_token>
```

## 前端实现

### 1. API 客户端配置 (src/api/client.js)

自动处理请求/响应拦截：
- 自动添加 Authorization 头
- 处理 401/403 错误
- 自动重定向到登录页

### 2. 认证 API (src/api/auth.js)

```javascript
import { register, login, logout, getCurrentUser } from '@/api/auth'

// 注册
await register({
    username: 'john_doe',
    email: 'john@example.com',
    password: 'secure_password',
    full_name: 'John Doe'
})

// 登录
const response = await login({
    username: 'john_doe',
    password: 'secure_password'
})

// 获取当前用户
const user = await getCurrentUser()

// 登出
logout()
```

### 3. 用户状态管理 (src/stores/authStore.js)

Pinia Store 包含：
```javascript
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()

// 状态
authStore.user              // 当前用户
authStore.token             // Access Token
authStore.loading           // 加载状态
authStore.error             // 错误信息

// 计算属性
authStore.isAuthenticated   // 是否已认证
authStore.userRole          // 用户角色
authStore.isAdmin           // 是否是管理员
authStore.isManager         // 是否是经理

// 方法
await authStore.register(userData)      // 注册
await authStore.login(loginData)        // 登录
await authStore.logout()                // 登出
await authStore.initAuth()              // 初始化认证
authStore.hasRole('admin')              // 检查角色
```

### 4. 路由守卫 (src/router/index.js)

```javascript
// 自动重定向到登录
// 未认证用户访问受保护路由 -> /login
// 已认证用户访问登录/注册页面 -> /meetings

// 路由元数据
{
    path: '/meetings',
    meta: { requiresAuth: true }        // 需要认证
}
```

### 5. 组件

#### 用户菜单 (src/components/UserMenu.vue)
```vue
<UserMenu />

<!-- 显示用户信息和操作菜单（登出、个人资料等） -->
```

#### 权限检查 (src/components/Permission.vue)
```vue
<!-- 仅管理员显示 -->
<Permission admin>
    <button>删除用户</button>
</Permission>

<!-- 检查特定角色 -->
<Permission :role="['admin', 'manager']">
    <div>只有管理员和经理能看到</div>
</Permission>

<!-- 需要认证 -->
<Permission auth>
    <div>需要登录才能看到</div>
</Permission>
```

## 使用说明

### 1. 后端启动前准备

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量（可选）：
```bash
# .env 或环境变量
SECRET_KEY=your-very-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./meetings.db
```

3. 初始化数据库：
```bash
python -c "from database import init_db; init_db()"
```

### 2. 启动后端服务

```bash
python app.py
# 或
uvicorn app:app --reload
```

### 3. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

### 4. 创建管理员用户（可选）

```bash
# 在 Python shell 中
from database import SessionLocal
from models import User, UserRole
from src.auth import hash_password

db = SessionLocal()
admin_user = User(
    username="admin",
    email="admin@example.com",
    hashed_password=hash_password("admin_password"),
    role=UserRole.ADMIN,
    is_active=True,
)
db.add(admin_user)
db.commit()
db.refresh(admin_user)
print(f"Admin user created: {admin_user.id}")
```

## 安全建议

### 1. 生产环境配置

```python
# 更改默认 SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")

# 设置合适的 Token 过期时间
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 小时

# 启用 HTTPS
ALLOWED_ORIGINS = ["https://yourdomain.com"]
```

### 2. Token 安全

- Token 存储在 localStorage（考虑使用 httpOnly Cookie）
- Token 过期时自动刷新
- 敏感操作需要密码确认

### 3. 密码安全

- 使用 bcrypt 哈希
- 密码长度至少 6 个字符（建议 8+）
- 实现密码重置功能
- 防止暴力破解

### 4. 权限检查

- 后端严格验证权限
- 前端仅用于 UI 显示
- 敏感操作需要特定角色
- 定期审计权限使用

## 常见问题

### Q: Token 过期怎么办？
A: 前端会自动调用 /api/auth/refresh 端点刷新 Token

### Q: 忘记密码怎么办？
A: 需要实现密码重置功能（邮件验证或安全问题）

### Q: 如何实现第三方登录？
A: 可以添加 OAuth2 集成，保留现有 JWT 逻辑

### Q: 如何限制登录次数？
A: 实现速率限制中间件

### Q: 如何实现多设备登出？
A: 维护 Token 黑名单或 Token 版本号

## 扩展功能

### 1. 邮件验证
```python
# 注册时发送验证邮件
# 验证链接包含验证令牌
```

### 2. 两因素认证 (2FA)
```python
# 登录后要求 TOTP 或短信验证码
```

### 3. 密码重置
```python
# POST /api/auth/forgot-password
# POST /api/auth/reset-password
```

### 4. 审计日志
```python
# 记录登录、权限更改等重要操作
```

### 5. 会话管理
```python
# 维护活跃会话列表
# 允许远程登出
```

## 文件结构

```
项目根目录/
├── models.py                          # User 模型定义
├── database.py                        # 数据库连接
├── app.py                             # FastAPI 应用入口
├── requirements.txt                   # 依赖声明
│
├── src/
│   ├── auth/                          # 认证模块
│   │   ├── __init__.py
│   │   ├── jwt_handler.py            # JWT 处理
│   │   ├── password.py               # 密码哈希
│   │   └── dependencies.py           # 依赖注入
│   │
│   └── api/
│       └── routes/
│           ├── auth.py               # 认证路由
│           ├── users.py              # 用户管理路由
│           ├── meetings.py           # 会议路由
│           └── ...
│
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── Login.vue             # 登录页面
        │   ├── Register.vue          # 注册页面
        │   └── ...
        │
        ├── components/
        │   ├── UserMenu.vue          # 用户菜单
        │   ├── Permission.vue        # 权限检查
        │   └── ...
        │
        ├── stores/
        │   ├── authStore.js          # 认证状态管理
        │   └── ...
        │
        ├── api/
        │   ├── client.js             # API 客户端
        │   ├── auth.js               # 认证 API
        │   └── ...
        │
        └── router/
            └── index.js              # 路由定义和守卫
```

## 相关链接

- [FastAPI 认证文档](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT 标准](https://tools.ietf.org/html/rfc7519)
- [Pinia 状态管理](https://pinia.vuejs.org/)
- [Vue Router 守卫](https://router.vuejs.org/guide/advanced/navigation-guards.html)

## 许可证

本项目采用 MIT 许可证
