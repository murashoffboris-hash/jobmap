"""
One-off seed: 60 вакансий по городам Беларуси с координатами для карты.
Запуск: docker cp на VPS → docker exec python seed_vacancies.py
"""
import asyncio
import random
import sys

sys.path.insert(0, '/app')

from sqlalchemy import text

from app.database import engine

CITIES = [
    ("Минск", 53.9000, 27.5667), ("Гомель", 52.4345, 30.9754),
    ("Могилёв", 53.9086, 30.3433), ("Витебск", 55.1904, 30.2049),
    ("Гродно", 53.6778, 23.8293), ("Брест", 52.0976, 23.7341),
    ("Бобруйск", 53.1383, 29.2214), ("Барановичи", 53.1333, 26.0167),
    ("Борисов", 54.2279, 28.5050), ("Пинск", 52.1229, 26.0951),
    ("Орша", 54.5081, 30.4172), ("Мозырь", 52.0489, 29.2583),
    ("Солигорск", 52.7878, 27.5415), ("Новополоцк", 55.5314, 28.6446),
    ("Лида", 53.8883, 25.2994), ("Молодечно", 54.3167, 26.8500),
]

JOBS = [
    "Продавец-консультант", "Водитель категории C", "Бухгалтер",
    "Менеджер по продажам", "Программист Python", "Охранник",
    "Уборщик помещений", "Электрик", "Сварщик", "Повар",
    "Медицинская сестра", "Кладовщик", "Грузчик", "Курьер",
    "Оператор call-центра", "Администратор", "Кассир", "Швея",
    "Маляр-штукатур", "Системный администратор", "Маркетолог",
    "Логист", "HR-менеджер", "Финансовый аналитик", "Дизайнер",
    "Копирайтер", "SMM-менеджер", "Тестировщик ПО", "DevOps инженер",
    "Руководитель отдела продаж", "Торговый представитель",
]

SALARIES = [(300,600),(400,800),(500,1000),(600,1200),(700,1500),(800,2000),(1000,2500),(1500,3000),(2000,4000)]
EMPLOYMENT = ["full_time", "part_time", "shift_work", "remote"]
SCHEDULE = ["5/2", "2/2", "сутки/трое", "гибкий график"]

random.seed(42)

async def seed():
    async with engine.connect() as conn:
        user = await conn.execute(text("SELECT id FROM users ORDER BY created_at LIMIT 1"))
        row = user.fetchone()
        if not row:
            print("ERROR: no users in DB")
            return
        uid = row[0]

        sql = text("""
            INSERT INTO vacancies (title, description, salary_from, salary_to, city,
                location_lat, location_lon, employment_type, schedule_type, employer_id, is_active)
            VALUES (:t, :d, :sf, :st, :city, :lat, :lon, :emp, :sch, :uid, true)
        """)

        for i in range(60):
            city, lat, lon = random.choice(CITIES)
            job = random.choice(JOBS)
            sf, st = random.choice(SALARIES)
            lat_j = round(lat + random.uniform(-0.02, 0.02), 6)
            lon_j = round(lon + random.uniform(-0.02, 0.02), 6)
            desc = f"Требуется {job.lower()} в г. {city}. Опыт работы приветствуется. Соцпакет, оформление по ТК."

            await conn.execute(sql, {
                "t": f"{job} ({city})", "d": desc,
                "sf": sf, "st": st, "city": city,
                "lat": lat_j, "lon": lon_j,
                "emp": random.choice(EMPLOYMENT),
                "sch": random.choice(SCHEDULE),
                "uid": uid,
            })

        await conn.commit()
        print(f"DONE: {60} vacancies seeded")

asyncio.run(seed())
