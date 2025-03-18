## Prerequisites
If you followed the installation guide you should now have a python project with Reagent installed and Docker on your system.

At the very least, Reagent needs a Postgres database to work properly. Future guides will show you how to setup other infrastructure to extend Reagent's capabilities. First let's setup a local Postgres database.

## Setting Up Postgres

### Step 1. Create a `compose.yaml` File
Before starting, let's organize our project by creating a dedicated folder for Docker-related files. Inside that folder create a file named `compose.yaml`.

```
your-project/
├── docker/
│   └── compose.yaml
├── your-project/
├── tests
└── pyproject.toml
```

### Step 2: Configure `compose.yaml`
Add the following contents to the compose file.

```yaml
services:
  app_postgres:
    image: postgres:15.6
    command: postgres -c 'max_connections=200'
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d app -U postgres"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 10s
    ports:
      - "5432:5432"

volumes:
    postgres_data:
```

### Step 3: Start the PostgreSQL Container
Run the following command in the directory containing your `compose.yaml` file:

```bash
docker-compose -f compose.yaml up
```

This will download the PostgreSQL image (if not already available) and start the container.

## Environment Setup

Reagent uses environment variables to configure itself. These variables can be provided from a variety of sources, but for local development the most convenient is a .env file. 

```
your-project/
├── docker/
├── your-project/
├── tests
└── pyproject.toml
```

## Cleanup
When you're done with your work, you should stop the Docker containers to free up resources:

### Using Ctrl+C
If the Docker Compose process is running in the foreground, you can press Ctrl+C in your terminal to stop the containers.

### Using Docker Compose Down Command
To completely stop and remove the containers, networks, and volumes defined in your compose file, run:

```bash
docker-compose -f compose.yaml down
```

If you want to preserve your PostgreSQL data for future use but stop the containers, use:

```bash
docker-compose -f compose.yaml stop
```