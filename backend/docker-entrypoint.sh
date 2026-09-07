#!/usr/bin/env sh
set -e

# In deployed environments App Runner passes APP_SECRET_ARN. Load that secret's
# JSON into the environment before the app starts, so no secret is ever baked
# into the image or the task definition.
if [ -n "$APP_SECRET_ARN" ]; then
  eval "$(python -c "import boto3,json,os,shlex; s=json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=os.environ['APP_SECRET_ARN'])['SecretString']); print('\n'.join(f'export {k}={shlex.quote(str(v))}' for k,v in s.items()))")"
fi

# Apply migrations, then serve.
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
