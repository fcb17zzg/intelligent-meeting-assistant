# JWT 认证系统 - 快速开始指南

## 1️⃣ 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

## 2️⃣ 配置环境

复制环境变量示例：
```bash
cp .env.example .env
```

修改 `.env` 文件中的配置（特别是 `SECRET_KEY`）

## 3️⃣ 初始化数据库

```bash
python -c "from database import init_db; init_db()"
```

## 4️⃣ 启动服务

### 后端
```bash
# 方式1：直接运行
python app.py

# 方式2：使用 uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
npm run dev
```

## 5️⃣ 访问应用

- 前端：http://localhost:3000
- API 文档：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 📝 测试流程

### 创建新账户
1. 访问 http://localhost:3000/register
2. 填写用户名、邮箱、密码
3. 点击注册

### 登录
1. 访问 http://localhost:3000/login
2. 输入用户名和密码
3. 点击登录

### 使用受保护资源
- 登录后可访问 /meetings 等页面
- 访问受保护页面时会自动发送 Token
- Token 过期时自动刷新

## 👨‍💻 创建管理员账户（可选）

```python
from database import SessionLocal
from models import User, UserRole
from src.auth import hash_password

db = SessionLocal()

# 创建管理员
admin = User(
    username="admin",
    email="admin@example.com",
    hashed_password=hash_password("admin123"),
    role=UserRole.ADMIN,
    is_active=True
)

db.add(admin)
db.commit()
print(f"✅ 管理员创建成功")
```

## 🔍 API 测试

使用 curl 或 Postman 测试：

### 注册
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

### 登录
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

响应中的 `access_token` 用于后续请求。

### 获取当前用户信息
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## 🚀 部署到生产环境

### 生产环境检查清单

- [ ] 修改 `SECRET_KEY` 为强加密密钥
- [ ] 关闭 `RELOAD` 模式
- [ ] 配置 HTTPS/SSL
- [ ] 使用 PostgreSQL 数据库
- [ ] 配置日志系统
- [ ] 设置 CORS 白名单
- [ ] 实现速率限制
- [ ] 添加审计日志
- [ ] 配置备份策略
- [ ] 启用密钥轮换

### Docker 部署

```dockerfile
# 后端 Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📚 参考资源

- [完整实现指南](./AUTH_IMPLEMENTATION_GUIDE.md)
- [FastAPI 安全文档](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP 认证检查清单](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

## ❓ 常见问题

**Q: 如何重置密码？**
A: 暂未实现，需要添加邮件验证功能

**Q: Token 保存在哪里？**
A: localStorage（建议改为 httpOnly Cookie 更安全）

**Q: 如何实现自动登出？**
A: 可以实现 Token 过期时的自动刷新或重定向到登录

**Q: 支持多设备登录吗？**
A: 支持，每个设备获得独立的 Token

---

🎉 现在你可以开始使用认证系统了！
