# Course Replicated Log Project

Все сервисы запускаются через Docker Compose 

Для запуска сервисов в терминале в каталоге проекта необходимо сбилдить и запустить сервисы посредством команд:

`docker-copmose build`

`docker-compose up`

После запуска, сервисы доступны по следующим адресам:

- Фронт-сервер  localhost:8000
- Реплика 1     localhost:8001
- Реплика 2     localhost:8002

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

##### Проверка здоровья нод:

- Метод:        GET
- Endpoint:     http://localhost:8000/health

##### Симуляция отключения нод
Для отключения связи с мастером, можно использовать следующте команды (приведенные наименования нод могут отличаться):

Отключение ноды (на примере 1) от сети 
`docker network disconnect code_default code_secondary1_1`

Подключение
`docker network connect --allias secondary1 code_default code_secondary1_1`