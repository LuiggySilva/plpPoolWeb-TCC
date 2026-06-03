#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for PostgreSQL..."

    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
        sleep 2
    done

    echo "PostgreSQL started"
fi

python manage.py collectstatic --no-input
python manage.py migrate

if [ -S /var/run/docker.sock ]; then
    echo "[Entrypoint] Socket do Docker detectado. Ajustando permissões..."
    
    DOCKER_SOCKET_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null)
    
    if [ -n "$DOCKER_SOCKET_GID" ]; then
        groupadd -g "$DOCKER_SOCKET_GID" docker_host_group 2>/dev/null || true

        usermod -aG docker_host_group app 
    fi
fi

mkdir -p /tmp/shared_codes
chown -R app:app /tmp/shared_codes

echo "[Entrypoint] Iniciando comando final como app..."
exec gosu app "$@"