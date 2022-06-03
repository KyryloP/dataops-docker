# Course Replicated Log Project

Это задание из курса "Распределенные системы" по построению сервисов репликции сообщений.
Есть одна мастер-нода (фронт-сервер) и 2 другие ноды, на которе реплицирубтя сооющения.
Более подробно требования к реализации можно увидеть в документе
https://docs.google.com/document/d/13akys1yQKNGqV9dGzSEDCGbHPDiKmqsZFOxKhxz841U/edit

После запуска, сервисы доступны по следующим адресам:
- фронт-сервер  localhost:8000
- реплика 1     localhost:8001
- реплика 2     localhost:8002

##### Отправка сообщений на фронт-сервер:

- Метод:        POST
- Endpoint:     http://localhost:8000/append
- Content-type: application/json
- Body:         {"text": "Your message here", "w": 3} 

##### Проверка сообщений на узлах:

- Метод:        GET
- Endpoint:     http://{node_host_here}/list

##### Конфигурация нод
Для симуляции задержек репликации без пересборки контейнеров на каждой реплике есть дополнительный метод установки времени задержки в секундах

- Метод:        POST
- Endpoint:     http://{node_host_here}/setdelay
- Content-type: application/json
- Body:         {"delay": 5}

##### Проверка состояния нод:

- Метод:        GET
- Endpoint:     http://localhost:8000/health
