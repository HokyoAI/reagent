# reagent

To run Hatchet tests:
docker compose -f ./docker/compose.hatchet-lite.yaml up
cat <<EOF >> .env
HATCHET_CLIENT_TOKEN="$(docker compose -f ./docker/compose.hatchet-lite.yaml exec hatchet-lite /hatchet-admin token create --config /config --tenant-id 707d0855-80ab-4e1f-a156-f1c4546cbf52 | xargs)"
HATCHET_CLIENT_TLS_STRATEGY=none
EOF