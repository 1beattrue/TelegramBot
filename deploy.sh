#!/bin/bash

# Обновление кода
git pull origin master

# Перезапуск контейнера
docker-compose down
docker-compose up -d --build