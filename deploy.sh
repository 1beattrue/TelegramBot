#!/bin/bash

# Обновление кода
git pull origin main

# Перезапуск контейнера
docker-compose down
docker-compose up -d --build