FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для Playwright и GUI
RUN apt-get update && apt-get install -y \
    # Зависимости Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # Зависимости для Tkinter (GUI)
    python3-tk \
    tk-dev \
    # Утилиты
    wget \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузеры Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Копируем исходный код
COPY . .

# Создаем директорию для результатов
RUN mkdir -p ymaps_parse_results

# Переменная окружения для DISPLAY (нужна для GUI)
ENV DISPLAY=:0

# Команда по умолчанию - запуск GUI
CMD ["python", "gui.py"]
