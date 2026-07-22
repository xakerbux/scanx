# CV-модуль САТК — Lichee Pi 4A

Модуль компьютерного зрения для анализа **локальных видеофайлов** по ТЗ хакатона.

Цикл: **видеофайл → детекция → событие → REST API → demo UI**

## Быстрый старт (Windows)

```powershell
cd C:\Users\16092007\lichee-pi-4a-cv
.\scripts\setup.ps1
.\.venv\Scripts\python.exe main.py
```

Откройте http://127.0.0.1:8080

## Локальное хранилище видео

Положите файлы в папку `videos/`:

```
videos/
├── demo.mp4          # создаётся скриптом setup
└── your_video.mp4    # ваши файлы (.mp4, .avi, .mkv, .mov)
```

В интерфейсе:
1. Выберите файл из списка **или** укажите полный путь
2. Нажмите **Применить**
3. **Старт**

## Структура

```
lichee-pi-4a-cv/
├── main.py
├── config/default.yaml
├── videos/              # локальное хранилище видео
├── models/yolov8n.onnx
├── cv_module/
│   ├── input/           # чтение видеофайлов
│   ├── preprocessing/   # resize, frame skip
│   ├── inference/       # YOLO ONNX + эвристики
│   ├── events/          # JSON + кадры событий
│   ├── pipeline/        # фоновая обработка
│   ├── api/             # REST API
│   └── ui/static/       # demo UI
└── scripts/
```

## Классы детекции (ТЗ)

| Класс | Метод |
|-------|-------|
| person | YOLOv8n ONNX |
| vehicle | YOLOv8n ONNX |
| fire | HSV-эвристика |
| smoke | HSV-эвристика |
| water | HSV-эвристика |

## REST API

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /health | Проверка сервиса |
| GET | /status | Статус, FPS, latency |
| GET | /videos | Список файлов в videos/ |
| GET | /events | Журнал событий |
| POST | /start | Запуск обработки |
| POST | /stop | Остановка |
| POST | /config | Смена видео/confidence |
| GET | /frame/latest | Последний кадр (JPEG) |
| GET | /metrics | Метрики |

## Конфигурация

`config/default.yaml`:

```yaml
videos_dir: videos
video_path: videos/demo.mp4
confidence_threshold: 0.45
model_path: models/yolov8n.onnx
frame_skip: 0
loop_video: true
```

## Перенос на Lichee Pi 4A

```bash
# На плате
cd ~/lichee-pi-4a-cv
python3 -m venv ~/ort && source ~/ort/bin/activate
pip install -r requirements.txt
python scripts/create_demo_video.py
python scripts/download_model.py
python main.py --config config/edge.yaml
```

Рекомендации edge: `input_size: [416,416]`, `frame_skip: 1`, видео в `videos/`.

## Mock-режим (без модели)

```powershell
python main.py --mock
```

## Ограничения

- Источник MVP: **только локальные видеофайлы**
- ONNX на RISC-V — через prebuilt wheels (см. wiki Sipeed)
- Эвристики огня/разлива требуют калибровки под реальное видео
