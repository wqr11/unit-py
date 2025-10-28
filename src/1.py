from sqlalchemy import create_engine, text

# Подключение к базе данных
# Замени строку подключения на свою:
# postgresql://username:password@host:port/database
DATABASE_URL = "postgresql://postgres:123@localhost:5432/stage"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Проверяем, есть ли колонка name в таблице labs
    result = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'labs' AND column_name = 'name';
    """))
    column_exists = result.fetchone()

    if not column_exists:
        print("Добавляю колонку 'name' в таблицу 'labs'...")
        conn.execute(text("ALTER TABLE labs ADD COLUMN name VARCHAR;"))
        conn.commit()
        print("✅ Колонка 'name' успешно добавлена.")
    else:
        print("Колонка 'name' уже существует, ничего делать не нужно.")
