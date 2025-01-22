#!/bin/bash

# Обновление кода
git pull origin master

# Удаление старого контейнера, если он существует
docker rm -f my-telegram-bot || true

# Создание volume для базы данных, если его еще нет
docker volume create telegram-bot-db || true

# Построение нового образа из Dockerfile
docker build -t telegram-bot .

# Запуск нового контейнера с примонтированным volume для БД
docker run -d --name my-telegram-bot \
  --restart unless-stopped \
  -v telegram-bot-db:/app \
  telegram-bot
