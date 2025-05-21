#!/bin/bash

# Apply migrations for alert model
docker-compose exec web python manage.py migrate alerts

# Apply any other pending migrations
docker-compose exec web python manage.py migrate

echo "Migrations applied successfully!" 