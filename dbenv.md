# Change the name of this file to .env after updating it!

############
# [required] Add commentMore actions
# n8n credentials - use the command `openssl rand -hex 32` to generate both
#   openssl is available by default on Linux/Mac
#   For Windows, you can use the 'Git Bash' terminal installed with git
#   Or run the command: python -c "import secrets; print(secrets.token_hex(32))"
############

N8N_ENCRYPTION_KEY=asddaydgwo78327832yg87387
N8N_USER_MANAGEMENT_JWT_SECRET=07287egqe87ggbhuasdba87dgq978fo


############
# [required] 
# Supabase Secrets

# YOU MUST CHANGE THESE BEFORE GOING INTO PRODUCTION
# Read these docs for any help: https://supabase.com/docs/guides/self-hosting/docker
# For the JWT Secret and keys, see: https://supabase.com/docs/guides/self-hosting/docker#generate-api-keys
# For the other secrets, see: https://supabase.com/docs/guides/self-hosting/docker#update-secrets
# You can really decide any value for POOLER_TENANT_ID like 1000.

# Note that using special symbols (like '%') can complicate things a bit for your Postgres password.
# If you use special symbols in your Postgres password, you must remember to percent-encode your password later if using the Postgres connection string, for example, postgresql://postgres.projectref:p%3Dword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
############

POSTGRES_PASSWORD=temp123
JWT_SECRET=yDejaLG2aDrnO96rnablmkeEOfMuBtfDnUYc9fsB
ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzYzNTU3MjAwLCJleHAiOjE5MjEzMjM2MDB9.mSsPwG1VGKhcpjmowS2DQQqitf-fC6lnp5pHaOf_2ts
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3NjM1NTcyMDAsImV4cCI6MTkyMTMyMzYwMH0.VBtWtMcBx0q1UA2fOgCv6UxT4os39Cqy4VrS2mXTJyE
DASHBOARD_USERNAME=supabase
DASHBOARD_PASSWORD=supa123
POOLER_TENANT_ID=66888
PG_META_CRYPTO_KEY=8b4d36e031bc3597d45634338408c3b5

############
# [required] 
# Neo4j username and password
# Replace "neo4j" with your chosen username and "password" with your chosen password.
# Keep the "/" as a separator between the two.
############

NEO4J_AUTH=localai/localpass

############
# [required] 
# Langfuse credentials
# Each of the secret keys you can set to whatever you want, just make it secure!
# For the encryption key, use the command `openssl rand -hex 32`
#   openssl is available by defualt on Linux/Mac
#   For Windows, you can use the 'Git Bash' terminal installed with git 
############

CLICKHOUSE_PASSWORD=ashdgawd8796atrasydg543543
MINIO_ROOT_PASSWORD=asd98ha9d8asdasdyad78
LANGFUSE_SALT=aklsdjaludsaghsfilugau34323dsd
NEXTAUTH_SECRET=asodhjap978ayd0a78sddas87
ENCRYPTION_KEY=D07B68AE15854AD67F8A7169232E7CB3 # generate via `openssl rand -hex 32`
MINIO_API_PORT=19012
MINIO_CONSOLE_PORT=19013

############
# [required for prod] 
# Caddy Config

# By default listen on https://localhost:[service port] and don't use an email for SSL
# To change this for production:
# Uncomment all of these environment variables for the services you want exposed
# Note that you might not want to expose Ollama or SearXNG since they aren't secured by default
# Replace the placeholder value with the host for each service (like n8n.yourdomain.com)
# Replace internal by your email (require to create a Let's Encrypt certificate)
############

# N8N_HOSTNAME=n8n.yourdomain.com
# WEBUI_HOSTNAME=openwebui.yourdomain.com
# FLOWISE_HOSTNAME=flowise.yourdomain.com
# SUPABASE_HOSTNAME=supabase.yourdomain.com
# LANGFUSE_HOSTNAME=langfuse.yourdomain.com
# OLLAMA_HOSTNAME=ollama.yourdomain.com
# SEARXNG_HOSTNAME=searxng.yourdomain.com
# NEO4J_HOSTNAME=neo4j.yourdomain.com
# LETSENCRYPT_EMAIL=internal



# Everything below this point is optional.
# Default values will suffice unless you need more features/customization.

   #
   #
#######
 #####
   #

############
# Optional Google Authentication for Supabase
# Get these values from the Google Admin Console
############
# ENABLE_GOOGLE_SIGNUP=true
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# GOOGLE_REDIRECT_URI=

############
# Optional SearXNG Config
# If you run a very small or a very large instance, you might want to change the amount of used uwsgi workers and threads per worker
# More workers (= processes) means that more search requests can be handled at the same time, but it also causes more resource usage
############

# SEARXNG_UWSGI_WORKERS=4
# SEARXNG_UWSGI_THREADS=4

############
# Database - You can change these to any PostgreSQL database that has logical replication enabled.
############

POSTGRES_HOST=db
POSTGRES_DB=postgres
POSTGRES_PORT=5432
# default user is postgres
POSTGRES_USER=postgres

############
# Supavisor -- Database pooler and others that can be left as default values
############
POOLER_PROXY_PORT_TRANSACTION=6543
POOLER_DEFAULT_POOL_SIZE=20
POOLER_MAX_CLIENT_CONN=100
SECRET_KEY_BASE=UpNVntn3cDxHJpq99YMc1T1AQgQpc8kfYTuRgBiYa15BLrx8etQoXz3gZv1/u2oq
VAULT_ENC_KEY=your-32-character-encryption-key
# Pool size for internal metadata storage used by Supavisor
# This is separate from client connections and used only by Supavisor itself
POOLER_DB_POOL_SIZE=5


############
# API Proxy - Configuration for the Kong Reverse proxy.
############

KONG_HTTP_PORT=8000
KONG_HTTPS_PORT=8443


############
# API - Configuration for PostgREST.
############

PGRST_DB_SCHEMAS=public,storage,graphql_public

############
# Flowise - Authentication Configuration for Flowise.
############
FLOWISE_USERNAME=flowise_admin
FLOWISE_PASSWORD=97120bdeae4744786c41e996


############
# Auth - Configuration for the GoTrue authentication server.
############

## General
SITE_URL=http://localhost:3000
ADDITIONAL_REDIRECT_URLS=
JWT_EXPIRY=3600
DISABLE_SIGNUP=false
API_EXTERNAL_URL=http://localhost:8000

## Mailer Config
MAILER_URLPATHS_CONFIRMATION="/auth/v1/verify"
MAILER_URLPATHS_INVITE="/auth/v1/verify"
MAILER_URLPATHS_RECOVERY="/auth/v1/verify"
MAILER_URLPATHS_EMAIL_CHANGE="/auth/v1/verify"

## Email auth
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=true
SMTP_ADMIN_EMAIL=admin@example.com
SMTP_HOST=supabase-mail
SMTP_PORT=2500
SMTP_USER=fake_mail_user
SMTP_PASS=fake_mail_password
SMTP_SENDER_NAME=fake_sender
ENABLE_ANONYMOUS_USERS=false

## Phone auth
ENABLE_PHONE_SIGNUP=true
ENABLE_PHONE_AUTOCONFIRM=true


############
# Studio - Configuration for the Dashboard
############

STUDIO_DEFAULT_ORGANIZATION=Default Organization
STUDIO_DEFAULT_PROJECT=Default Project

STUDIO_PORT=3000
# replace if you intend to use Studio outside of localhost
SUPABASE_PUBLIC_URL=http://localhost:8000

# Enable webp support
IMGPROXY_ENABLE_WEBP_DETECTION=true

# Add your OpenAI API key to enable SQL Editor Assistant
OPENAI_API_KEY=


############
# Functions - Configuration for Functions
############
# NOTE: VERIFY_JWT applies to all functions. Per-function VERIFY_JWT is not supported yet.
FUNCTIONS_VERIFY_JWT=false


############
# Logs - Configuration for Analytics
# Please refer to https://supabase.com/docs/reference/self-hosting-analytics/introduction
############

# Change vector.toml sinks to reflect this change
# these cannot be the same value
LOGFLARE_PUBLIC_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-public
LOGFLARE_PRIVATE_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-private

# Docker socket location - this value will differ depending on your OS
DOCKER_SOCKET_LOCATION=/var/run/docker.sock

# Google Cloud Project details
GOOGLE_PROJECT_ID=GOOGLE_PROJECT_ID
GOOGLE_PROJECT_NUMBER=GOOGLE_PROJECT_NUMBER



### Summary
Service ports (private environment / docker-compose.override.private.yml)
                                                                                                     
  - n8n: 127.0.0.1:5678 (container 5678)                                                             
  - Open WebUI: 127.0.0.1:8080 (8080)                                                                
  - Flowise: 127.0.0.1:3001 (3001)                                                                   
  - Qdrant: 127.0.0.1:6333 HTTP, 6334 gRPC                                                           
  - Neo4j: 127.0.0.1:7474 HTTP, 7473 HTTPS, 7687 Bolt                                                
  - Langfuse: web 127.0.0.1:3000 (3000), worker 127.0.0.1:3030                                       
  - ClickHouse: 127.0.0.1:8123 HTTP UI, 9000 native, 9009 inter-server                               
  - Minio: 127.0.0.1:9012 API (9000), 9013 console (9001)
  - Supabase gateway (Kong): 8000 HTTP, 8443 HTTPS (from supabase/docker/docker-compose.yml)         
  - Supabase Studio: 3000 (internal container studio)                                                
  - Postgres (Supabase db): 127.0.0.1:5433 → container db:5432                                       
  - Redis: 127.0.0.1:6379                                                                            
  - SearXNG: 127.0.0.1:8081                                                                          
  - Ollama: 127.0.0.1:11434                                                                          
                                                                                                     
  Credentials / keys (from .env in repo root)                                                        
                                                                                                     
  - Supabase dashboard (Kong basic auth): user supabase, pass supa123                                
  - Supabase API keys:                                                                               
    ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0Ijo    xNzYzNTU3MjAwLCJleHAiOjE5MjEzMjM2MDB9.mSsPwG1VGKhcpjmowS2DQQqitf-fC6lnp5pHaOf_2ts;               
    SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3V    wYWJhc2UiLCJpYXQiOjE3NjM1NTcyMDAsImV4cCI6MTkyMTMyMzYwMH0.VBtWtMcBx0q1UA2fOgCv6UxT4os39Cqy4VrS2mXT    JyE                                                                                              
  - Supabase JWT secret: yDejaLG2aDrnO96rnablmkeEOfMuBtfDnUYc9fsB                                    
  - Supabase Postgres: user postgres, pass temp123, db postgres (host db inside compose,             
    127.0.0.1:5433 from host)                                                                        
  - Supabase pooler tenant: POOLER_TENANT_ID=66888                                                   
  - Supabase PG meta crypto key: PG_META_CRYPTO_KEY=8b4d36e031bc3597d45634338408c3b5                 
  - ClickHouse: user clickhouse, pass ashdgawd8796atrasydg543543                                     
  - Neo4j: localai/localpass                                                                         
  - Flowise auth: user flowise_admin, pass 97120bdeae4744786c41e996                                  
  - Minio: root user minio, pass asd98ha9d8asdasdyad78                                               
  - Langfuse project (Local Dev): public key pk-lf-0lBMFVNpEA-e-z3zPGPZ5g, secret key sk-lf-eaWk_ujfXWuUvNoW_EdH8dilPdLv1nvII0jLQznDU1g, admin langfuse-admin@example.com / 6nc6x7cD32z8R6yltgMNQA (env seeded via LANGFUSE_INIT_* in ~/local-ai-packaged/.env)                                
  - Langfuse ENCRYPTION_KEY: 8fef1a9d35ec537e1631eb93d026111e9db4767df3f8b9660b7422b3ffe54e7b (64-hex)                                                                          
  - Redis/Valkey: requirepass LOCALONLYREDIS                                                         						   
  - Langfuse/NextAuth/crypto: LANGFUSE_SALT=aklsdjaludsaghsfilugau34323dsd,                          
    NEXTAUTH_SECRET=asodhjap978ayd0a78sddas87, ENCRYPTION_KEY=8fef1a9d35ec537e1631eb93d026111e9db4767df3f8b9660b7422b3ffe54e7b       
  - n8n secrets: N8N_ENCRYPTION_KEY=asddaydgwo78327832yg87387,                                       
    N8N_USER_MANAGEMENT_JWT_SECRET=07287egqe87ggbhuasdba87dgq978fo                                   
                                                                                                     
  Note: These values are stored in plain text for local use; rotate/change before any production or  
  shared deployment.
