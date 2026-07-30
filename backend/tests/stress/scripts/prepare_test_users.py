"""批量创建压力测试用户 + 预创建会话。

用法：
    cd backend
    venv/Scripts/python tests/stress/scripts/prepare_test_users.py

这会在数据库中创建 100 个测试用户（stresstest001 ~ stresstest100），
并为每个用户预创建 1 个会话（避免首条消息触发额外 LLM 调用）。
"""

import asyncio
import sys
import os

# 添加 backend 到 Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import async_session
from app.services.auth_service import create_user
from app.models.user import User
from app.models.session import Session
from sqlalchemy import select


TOTAL_USERS = 100
PASSWORD = "LoadTest@123"


async def main():
    async with async_session() as db:
        # 1. 检查已有测试用户数量
        result = await db.execute(
            select(User).where(User.username.like("stresstest%"))
        )
        existing = result.scalars().all()
        existing_count = len(existing)
        print(f"已有测试用户: {existing_count} 个")

        # 2. 创建缺失的用户
        created = 0
        for i in range(1, TOTAL_USERS + 1):
            username = f"stresstest{i:03d}"
            # 检查是否已存在
            result = await db.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none() is not None:
                continue

            user = await create_user(db, username, PASSWORD)
            if user:
                created += 1
                if created % 20 == 0:
                    print(f"  已创建 {created} 个用户...")

        if created > 0:
            await db.commit()
            print(f"✅ 新建测试用户: {created} 个")
        else:
            print("✅ 所有测试用户已存在，无需创建")

        # 3. 为每个测试用户预创建 1 个会话
        sessions_created = 0
        for i in range(1, TOTAL_USERS + 1):
            username = f"stresstest{i:03d}"
            result = await db.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if user is None:
                continue

            # 检查是否已有会话
            result = await db.execute(
                select(Session).where(Session.user_id == user.id)
            )
            existing_sessions = result.scalars().all()
            if existing_sessions:
                continue

            # 创建会话
            session = Session(user_id=user.id, title="压力测试会话")
            db.add(session)
            sessions_created += 1

        if sessions_created > 0:
            await db.commit()
            print(f"✅ 预创建会话: {sessions_created} 个")
        else:
            print("✅ 所有用户已有会话，无需创建")

    # 4. 汇总
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.username.like("stresstest%"))
        )
        total_users = len(result.scalars().all())
        result = await db.execute(
            select(Session).where(Session.title == "压力测试会话")
        )
        total_sessions = len(result.scalars().all())

    print(f"\n{'='*50}")
    print(f"  测试用户: {total_users} 个")
    print(f"  测试会话: {total_sessions} 个")
    print(f"  用户密码: {PASSWORD}")
    print(f"{'='*50}")
    print("准备完成！可以开始压力测试。")
    print()
    print("启动命令:")
    print("  STRESS_TEST_MOCK=true uvicorn app.main:app --port 8000 --workers 4")
    print()
    print("Locust 命令:")
    print("  locust -f tests/stress/locustfile.py --host http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(main())
