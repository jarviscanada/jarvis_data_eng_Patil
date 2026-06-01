#!/bin/bash

# Setup and validate arguments
cmd=$1
db_username=$2
db_password=$3

# Validate number of arguments
if [ "$#" -ne 3 ]; then
  echo "Illegal number of parameters"
  echo "Usage: ./psql_docker.sh create|start|stop db_username db_password"
  exit 1
fi

# Check if docker is running
systemctl status docker || systemctl start docker

# Create a docker volume for data persistence
docker volume create pgdata

case $cmd in
  create)
    # Check if container already exists
    docker container inspect jrvs-psql > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo "Container already exists"
      exit 1
    fi

    # Create the container
    docker run --name jrvs-psql \
      -e POSTGRES_USER=$db_username \
      -e POSTGRES_PASSWORD=$db_password \
      -d \
      -v pgdata:/var/lib/postgresql/data \
      -p 5432:5432 \
      postgres:9.6-alpine
    exit $?
    ;;

  start)
    docker container start jrvs-psql
    exit $?
    ;;

  stop)
    docker container stop jrvs-psql
    exit $?
    ;;

  *)
    echo "Invalid command. Use create, start, or stop"
    exit 1
    ;;
esac
