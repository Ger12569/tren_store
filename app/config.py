import os
from pathlib import Path
from dotenv import load_dotenv

# Поднимаем путь из текущей папки (app) на уровень выше (корень проекта)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Загружаем .env явно по этому пути
load_dotenv(dotenv_path=ENV_PATH)

# Теперь берём переменные. Если их нет — будет None, но мы это увидим
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Для быстрой проверки: если ключа нет, сразу кидаем ошибку при старте, а не в запросе
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY не найден в .env! Проверьте файл .env в корне проекта.")
