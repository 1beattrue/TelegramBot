#!/bin/bash

# Обновление кода
git pull origin master

# Удаление старого контейнера, если он существует
docker rm -f my-telegram-bot || true

# Построение нового образа из Dockerfile
docker build -t telegram-bot .

# Запуск нового контейнера
docker run -d --name my-telegram-bot --restart unless-stopped telegram-bot
