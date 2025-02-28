#!/usr/bin/env bash

include .env
export $(shell sed 's/=.*//' .env)

DOCKER_COMPOSE = docker compose -p $(BASE_PROJECT_NAME)

CONTAINER_SE := $(shell docker container ls -f "name=$(BASE_PROJECT_NAME)-video-formatter" -q)

SE := docker exec -ti $(CONTAINER_SE)

fix:
	$(SE) ruff check --fix --exclude src/Protobuf
	$(SE) black src --exclude "src/Protobuf"
