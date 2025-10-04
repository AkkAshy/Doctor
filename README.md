# 🏥 GluZone - Health Monitoring System

**Система мониторинга здоровья для пациентов с диабетом**

[![Django](https://img.shields.io/badge/Django-5.2.7-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16.1-red.svg)](https://www.django-rest-framework.org/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-blue.svg)](https://swagger.io/specification/)


---

## 📋 Возможности

### 🔐 Авторизация
- ✅ Регистрация и вход через JWT токены
- ✅ Интеграция с Telegram Bot
- ✅ Автоматическое обновление токенов

### 📊 Дневник здоровья
- ✅ Измерения уровня глюкозы
- ✅ События: еда, прогулки, спорт
- ✅ Прием лекарств
- ✅ Заметки о стрессе и самочувствии
- ✅ Напоминания

### 🤖 AI Функции
- ✅ **Анализ фото еды** через GPT-4 Vision
- ✅ **Персональные рекомендации** от AI
- ✅ **Прогноз глюкозы** на неделю вперед

### 📈 Статистика и аналитика
- ✅ Графики глюкозы, активности, питания
- ✅ Тренды и паттерны
- ✅ Экспорт данных

### 👨‍⚕️ Для врачей
- ✅ Просмотр данных всех пациентов
- ✅ Дашборд с критическими случаями
- ✅ Детальная статистика по каждому пациенту

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/AkkAshy/gluzone.git
cd gluzone
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

Создайте файл `.env` в корне проекта:

```env
# OpenAI API Key (обязательно!)
OPENAI_API_KEY=sk-proj-ваш-ключ-здесь

# Django Secret Key
SECRET_KEY=ваш-секретный-ключ

# Database (опционально, по умолчанию SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# Telegram Bot (опционально)
TELEGRAM_BOT_USERNAME=YourBot_Bot
```

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Запустить сервер

```bash
python manage.py runserver
```

### 8. Открыть Swagger UI 🎉

```
http://127.0.0.1:8000/api/docs/
```

---

## 📚 Документация

### Интерактивная документация

- **Swagger UI:** http://127.0.0.1:8000/api/docs/
  - Интерактивное тестирование API
  - Примеры запросов/ответов
  - Авторизация через Bearer token

- **ReDoc:** http://127.0.0.1:8000/api/redoc/
  - Красивая документация
  - Поиск по endpoint'ам
  - Экспорт в PDF

- **OpenAPI Schema:** http://127.0.0.1:8000/api/schema/
  - Сырая схема в формате JSON
  - Для генерации клиентов


---

## 🏗️ Структура проекта

```
gluzone/
├── authapp/              # Авторизация, пользователи
│   ├── models.py        # Employee, TelegramAuthCode
│   ├── views.py         # Регистрация, вход, профиль
│   ├── serializers.py   # UserSerializer
│   └── tasks.py         # AI анализ и рекомендации
│
├── diary/               # Дневник здоровья
│   ├── models.py        # Glucose, Event, Medication...
│   ├── views.py         # CRUD для дневника
│   ├── doctor_views.py  # API для врачей
│   ├── statistics_views.py  # Статистика
│   └── utils.py         # AI анализ фото еды
│
├── healthapp/           # Настройки проекта
│   ├── settings.py      # Конфигурация + Swagger
│   └── urls.py          # Роутинг + документация
│
└── requirements.txt     # Зависимости
```

---

## 🔑 API Endpoints

### Авторизация

```
POST   /api/users/register/           - Регистрация
POST   /api/users/login/              - Вход (JWT)
POST   /api/users/token/refresh/      - Обновить токен
GET    /api/users/my-profile/         - Мой профиль
PUT    /api/users/profile/            - Обновить профиль
```

### Telegram

```
GET    /api/users/telegram/generate_code/    - Сгенерировать код
POST   /api/users/telegram/confirm_code/     - Подтвердить код
GET    /api/users/telegram/profile/{id}/     - Профиль по Telegram ID
```

### Дневник

```
# Глюкоза
GET    /api/diary/glucose/            - Список измерений
POST   /api/diary/glucose/            - Добавить измерение

# События (еда, прогулки, спорт)
GET    /api/diary/events/             - Список событий
POST   /api/diary/events/             - Создать событие
POST   /api/diary/events/preview_meal/           - 🤖 AI анализ фото
POST   /api/diary/events/create_meal_with_photo/ - 🤖 Создать с AI

# Лекарства
GET    /api/diary/medications/        - Список
POST   /api/diary/medications/        - Добавить

# Стресс
GET    /api/diary/stress-notes/       - Список заметок
POST   /api/diary/stress-notes/       - Добавить

# Напоминания
GET    /api/diary/reminders/          - Список
POST   /api/diary/reminders/          - Создать
```

### Статистика

```
GET    /api/statistics/glucose/?period=month     - Статистика глюкозы
GET    /api/statistics/nutrition/?period=month   - Статистика питания
GET    /api/statistics/activity/?period=month    - Статистика активности
```

### AI Рекомендации

```
GET    /api/users/recomended/         - Получить персональные рекомендации
```

### Для врачей

```
GET    /api/doctor/patients/                     - Список пациентов
GET    /api/doctor/patients/{id}/statistics/     - Статистика пациента
GET    /api/doctor/glucose/                      - Глюкоза всех
GET    /api/doctor/events/                       - События всех
GET    /api/doctor/dashboard/                    - Дашборд
```

---

## 💡 Примеры использования

### Python

```python
import requests

# Вход
response = requests.post('http://127.0.0.1:8000/api/users/login/', json={
    'username': 'ivan',
    'password': 'pass123'
})
token = response.json()['access']

# Добавить глюкозу
headers = {'Authorization': f'Bearer {token}'}
requests.post('http://127.0.0.1:8000/api/diary/glucose/', 
    headers=headers, 
    json={'value': 5.8}
)

# Получить рекомендации
recs = requests.get('http://127.0.0.1:8000/api/users/recomended/', 
    headers=headers
).json()

print(recs['analysis'])
```

### JavaScript

```javascript
// Вход
const login = await fetch('http://127.0.0.1:8000/api/users/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'ivan', password: 'pass123' })
});

const { access } = await login.json();

// Добавить глюкозу
await fetch('http://127.0.0.1:8000/api/diary/glucose/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ value: 5.8 })
});
```

### cURL

```bash
# Вход
curl -X POST http://127.0.0.1:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "ivan", "password": "pass123"}'

# Добавить глюкозу
curl -X POST http://127.0.0.1:8000/api/diary/glucose/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 5.8}'
```

Больше примеров в [API_EXAMPLES.md](API_EXAMPLES.md)

---

## 🤖 AI Функции

### 1. Анализ фото еды (GPT-4 Vision)

```python
# Загрузить фото и получить анализ
with open('food.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post(
        'http://127.0.0.1:8000/api/diary/events/preview_meal/',
        headers={'Authorization': f'Bearer {token}'},
        files=files
    )

result = response.json()
# {
#   "food_name": "Борщ",
#   "calories": 320,
#   "carbs": 25,
#   "sugars": 8,
#   "confidence": "high"
# }
```

### 2. Персональные рекомендации

```python
recs = requests.get(
    'http://127.0.0.1:8000/api/users/recomended/',
    headers={'Authorization': f'Bearer {token}'}
).json()

print(recs['analysis'])     # Текстовый анализ от GPT
print(recs['chart_data'])   # Прогноз глюкозы на 7 дней
```

---

## 🛠️ Разработка

### Запуск тестов

```bash
python manage.py test
```

### Генерация тестовых данных

```bash
python manage.py fill_test_month
```

### Создание нового endpoint с документацией

```python
from drf_spectacular.utils import extend_schema

@extend_schema(
    tags=['Название раздела'],
    summary="Краткое описание",
    description="Подробное описание"
)
class MyView(APIView):
    def get(self, request):
        ...
```

---

## 📦 Зависимости

- **Django 5.2.7** - Web framework
- **Django REST Framework 3.16.1** - API framework
- **drf-spectacular 0.27.2** - OpenAPI/Swagger документация
- **djangorestframework-simplejwt 5.5.1** - JWT авторизация
- **Pillow 11.3.0** - Обработка изображений
- **requests 2.32.5** - HTTP клиент для OpenAI
- **python-decouple 3.8** - Управление настройками

Полный список в [requirements.txt](requirements.txt)

---

## 🔒 Безопасность

### Production настройки

1. Измените `SECRET_KEY` в `.env`
2. Установите `DEBUG = False`
3. Настройте `ALLOWED_HOSTS`
4. Используйте PostgreSQL вместо SQLite
5. Настройте HTTPS
6. Включите CORS только для нужных доменов

```python
# settings.py для production
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gluzone',
        ...
    }
}
```

---

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

## 🤝 Контрибьюторы

- **Разработчик:** Your Name
- **Email:** your.email@example.com
- **GitHub:** [@yourusername](https://github.com/yourusername)

---

## 🎯 Roadmap

- [ ] Мобильное приложение (React Native)
- [ ] Push-уведомления
- [ ] Интеграция с фитнес-трекерами
- [ ] Экспорт отчетов в PDF
- [ ] Многоязычность
- [ ] Темная тема

---

## 📞 Поддержка

Нашли баг или есть предложение? Создайте [Issue](https://github.com/yourusername/gluzone/issues)

**Swagger UI:** http://127.0.0.1:8000/api/docs/

**Приятного использования! 🚀**