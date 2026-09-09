# cloud-fullstack-intern

The repo is used for interns of Cloud Fullstack program to practice following the training plan

## Project Overview

- Project is under development. The main theme will be announce in the near future.

## TechStack

- **Frontend:** Angular
- **Backend:** Python, FastAPI
- **Cloud:** AWS
- **DevOps:** Docker, Terraform, Kubernetes
- **Database:** PostgreSQL, MongoDB

## Start the servers

- Frontend: `npm start`
- Backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Backend-v2: `docker compose up --build`

```
cloud-fullstack-intern
├─ backend
│  ├─ app
│  │  ├─ core
│  │  │  ├─ config.py
│  │  │  ├─ database.py
│  │  │  └─ security.py
│  │  ├─ main.py
│  │  └─ modules
│  │     ├─ auth
│  │     │  ├─ dependencies.py
│  │     │  ├─ models.py
│  │     │  ├─ queries.py
│  │     │  ├─ repository.py
│  │     │  ├─ router.py
│  │     │  ├─ schemas.py
│  │     │  ├─ service.py
│  │     │  └─ __init__.py
│  │     ├─ files
│  │     │  ├─ dependencies.py
│  │     │  ├─ models.py
│  │     │  ├─ purge_trashed.py
│  │     │  ├─ queries.py
│  │     │  ├─ repository.py
│  │     │  ├─ router.py
│  │     │  ├─ schemas.py
│  │     │  ├─ service.py
│  │     │  ├─ tables
│  │     │  │  ├─ apply_tables.py
│  │     │  │  └─ design_tables.txt
│  │     │  ├─ utils
│  │     │  │  └─ convert_ltree_uuid.py
│  │     │  └─ __init__.py
│  │     └─ share
│  │        ├─ dependencies.py
│  │        ├─ models.py
│  │        ├─ queries.py
│  │        ├─ repository.py
│  │        ├─ router.py
│  │        ├─ schemas.py
│  │        ├─ service.py
│  │        └─ __init__.py
│  ├─ pytest.ini
│  └─ tests
│     ├─ test_main.py
│     ├─ test_r2.py
│     ├─ test_storage_quota.py
│     └─ test_upload_pipeline.py
├─ backend-v2
│  ├─ api-gateway
│  │  ├─ Dockerfile
│  │  ├─ nginx.conf
│  │  ├─ nginx2.conf
│  │  └─ nginx3.conf
│  ├─ auth-service
│  │  ├─ app
│  │  │  ├─ core
│  │  │  │  ├─ config.py
│  │  │  │  ├─ database.py
│  │  │  │  ├─ exceptions.py
│  │  │  │  ├─ rabbitmq.py
│  │  │  │  ├─ rate_limit.py
│  │  │  │  ├─ redis.py
│  │  │  │  └─ security.py
│  │  │  ├─ main.py
│  │  │  └─ modules
│  │  │     └─ auth
│  │  │        ├─ cache.py
│  │  │        ├─ dependencies.py
│  │  │        ├─ internal_router.py
│  │  │        ├─ models.py
│  │  │        ├─ queries.py
│  │  │        ├─ repository.py
│  │  │        ├─ router.py
│  │  │        ├─ schemas.py
│  │  │        ├─ service.py
│  │  │        ├─ tables
│  │  │        │  ├─ apply_tables.py
│  │  │        │  └─ auth_design_tables.txt
│  │  │        └─ __init__.py
│  │  └─ Dockerfile
│  ├─ docker-compose.yml
│  ├─ migrations
│  │  ├─ create_deleteion_jobs_table.sql
│  │  ├─ fix_storage_trigger.sql
│  │  ├─ migrate_v1_to_v2.sql
│  │  └─ separate_storage_quota_tracking.sql
│  ├─ package
│  └─ storage-service
│     ├─ app
│     │  ├─ core
│     │  │  ├─ cache.py
│     │  │  ├─ config.py
│     │  │  ├─ database.py
│     │  │  ├─ dependencies.py
│     │  │  ├─ events.py
│     │  │  ├─ exceptions.py
│     │  │  ├─ hash_reader.py
│     │  │  ├─ jobs.py
│     │  │  ├─ object_bucket.py
│     │  │  ├─ queries.py
│     │  │  ├─ rabbitmq.py
│     │  │  ├─ rate_limit.py
│     │  │  ├─ redis.py
│     │  │  ├─ repository.py
│     │  │  └─ security.py
│     │  ├─ main.py
│     │  └─ modules
│     │     ├─ files
│     │     │  ├─ dependencies.py
│     │     │  ├─ models.py
│     │     │  ├─ purge_trashed.py
│     │     │  ├─ queries.py
│     │     │  ├─ repositories
│     │     │  │  ├─ base.py
│     │     │  │  ├─ file_management_repository.py
│     │     │  │  ├─ file_query_repository.py
│     │     │  │  ├─ storage_quota_repository.py
│     │     │  │  ├─ trash_repository.py
│     │     │  │  └─ __init__.py
│     │     │  ├─ repository.py
│     │     │  ├─ router.py
│     │     │  ├─ schemas.py
│     │     │  ├─ services
│     │     │  │  ├─ base.py
│     │     │  │  ├─ file_management_service.py
│     │     │  │  ├─ file_query_service.py
│     │     │  │  ├─ file_upload_service.py
│     │     │  │  ├─ storage_quota_service.py
│     │     │  │  ├─ trash_service.py
│     │     │  │  └─ __init__.py
│     │     │  ├─ tables
│     │     │  │  ├─ apply_tables.py
│     │     │  │  └─ storage_design_tables.txt
│     │     │  ├─ utils
│     │     │  │  ├─ db_retry.py
│     │     │  │  └─ sanitization.py
│     │     │  └─ __init__.py
│     │     └─ share
│     │        ├─ dependencies.py
│     │        ├─ models.py
│     │        ├─ queries.py
│     │        ├─ repository.py
│     │        ├─ router.py
│     │        ├─ schemas.py
│     │        ├─ service.py
│     │        └─ __init__.py
│     ├─ aws_lambda_handler.py
│     └─ Dockerfile
├─ frontend
│  ├─ .editorconfig
│  ├─ .prettierignore
│  ├─ .prettierrc
│  ├─ angular.json
│  ├─ package.json
│  ├─ proxy.conf.json
│  ├─ proxy.docker.conf.json
│  ├─ public
│  │  └─ favicon.ico
│  ├─ src
│  │  ├─ app
│  │  │  ├─ app.config.ts
│  │  │  ├─ app.html
│  │  │  ├─ app.routes.ts
│  │  │  ├─ app.scss
│  │  │  ├─ app.spec.ts
│  │  │  ├─ app.ts
│  │  │  ├─ core
│  │  │  │  ├─ auth
│  │  │  │  │  ├─ endpoints
│  │  │  │  │  │  └─ auth-endpoints.ts
│  │  │  │  │  ├─ guards
│  │  │  │  │  │  └─ auth.guard.ts
│  │  │  │  │  ├─ interceptors
│  │  │  │  │  │  └─ auth-refresh.interceptor.ts
│  │  │  │  │  └─ services
│  │  │  │  │     ├─ auth.service.ts
│  │  │  │  │     └─ token-refresh-state.service.ts
│  │  │  │  ├─ file-operations
│  │  │  │  │  ├─ endpoints
│  │  │  │  │  │  └─ file-operations-endpoints.ts
│  │  │  │  │  └─ services
│  │  │  │  │     ├─ file-chunking.ts
│  │  │  │  │     ├─ file-operations.service.ts
│  │  │  │  │     ├─ storage-state.service.ts
│  │  │  │  │     └─ upload-queue.service.ts
│  │  │  │  ├─ share
│  │  │  │  │  ├─ interceptors
│  │  │  │  │  │  └─ share-password.interceptor.ts
│  │  │  │  │  └─ services
│  │  │  │  │     ├─ share-password.service.ts
│  │  │  │  │     └─ share.service.ts
│  │  │  │  └─ tests
│  │  │  │     ├─ auth.service.spec.ts
│  │  │  │     ├─ file-operations.service.spec.ts
│  │  │  │     ├─ share-password.service.spec.ts
│  │  │  │     ├─ share.service.spec.ts
│  │  │  │     ├─ storage-state.service.spec.ts
│  │  │  │     └─ upload-queue.service.spec.ts
│  │  │  ├─ features
│  │  │  │  ├─ auth
│  │  │  │  │  └─ components
│  │  │  │  │     ├─ login
│  │  │  │  │     │  ├─ login.html
│  │  │  │  │     │  ├─ login.scss
│  │  │  │  │     │  ├─ login.spec.ts
│  │  │  │  │     │  └─ login.ts
│  │  │  │  │     └─ register
│  │  │  │  │        ├─ register.html
│  │  │  │  │        ├─ register.scss
│  │  │  │  │        ├─ register.spec.ts
│  │  │  │  │        └─ register.ts
│  │  │  │  ├─ dashboard
│  │  │  │  │  ├─ dashboard.html
│  │  │  │  │  ├─ dashboard.scss
│  │  │  │  │  ├─ dashboard.spec.ts
│  │  │  │  │  └─ dashboard.ts
│  │  │  │  ├─ drive
│  │  │  │  │  ├─ drive.html
│  │  │  │  │  ├─ drive.scss
│  │  │  │  │  ├─ drive.spec.ts
│  │  │  │  │  └─ drive.ts
│  │  │  │  ├─ file-preview
│  │  │  │  │  ├─ file-preview.html
│  │  │  │  │  ├─ file-preview.scss
│  │  │  │  │  ├─ file-preview.spec.ts
│  │  │  │  │  └─ file-preview.ts
│  │  │  │  ├─ landing
│  │  │  │  │  ├─ landing.html
│  │  │  │  │  ├─ landing.scss
│  │  │  │  │  ├─ landing.spec.ts
│  │  │  │  │  └─ landing.ts
│  │  │  │  ├─ public-share
│  │  │  │  │  ├─ public-share.html
│  │  │  │  │  ├─ public-share.scss
│  │  │  │  │  ├─ public-share.spec.ts
│  │  │  │  │  └─ public-share.ts
│  │  │  │  ├─ share-dialog
│  │  │  │  │  ├─ share-dialog.html
│  │  │  │  │  ├─ share-dialog.scss
│  │  │  │  │  ├─ share-dialog.spec.ts
│  │  │  │  │  └─ share-dialog.ts
│  │  │  │  ├─ shared-link
│  │  │  │  │  ├─ shared-link.html
│  │  │  │  │  ├─ shared-link.scss
│  │  │  │  │  ├─ shared-link.spec.ts
│  │  │  │  │  └─ shared-link.ts
│  │  │  │  ├─ shared-with-me
│  │  │  │  │  ├─ shared-with-me.html
│  │  │  │  │  ├─ shared-with-me.spec.ts
│  │  │  │  │  └─ shared-with-me.ts
│  │  │  │  ├─ trash
│  │  │  │  │  ├─ trash.html
│  │  │  │  │  ├─ trash.scss
│  │  │  │  │  ├─ trash.spec.ts
│  │  │  │  │  └─ trash.ts
│  │  │  │  ├─ upload-dialog
│  │  │  │  │  ├─ upload-dialog.html
│  │  │  │  │  ├─ upload-dialog.scss
│  │  │  │  │  ├─ upload-dialog.spec.ts
│  │  │  │  │  └─ upload-dialog.ts
│  │  │  │  ├─ upload-widget
│  │  │  │  │  ├─ upload-widget.html
│  │  │  │  │  ├─ upload-widget.scss
│  │  │  │  │  ├─ upload-widget.spec.ts
│  │  │  │  │  └─ upload-widget.ts
│  │  │  │  └─ user-profile
│  │  │  │     ├─ user-profile.html
│  │  │  │     ├─ user-profile.scss
│  │  │  │     ├─ user-profile.spec.ts
│  │  │  │     └─ user-profile.ts
│  │  │  └─ shared
│  │  │     ├─ components
│  │  │     │  ├─ breadcrumb
│  │  │     │  │  ├─ breadcrumb.html
│  │  │     │  │  ├─ breadcrumb.scss
│  │  │     │  │  ├─ breadcrumb.spec.ts
│  │  │     │  │  └─ breadcrumb.ts
│  │  │     │  ├─ change-password-dialog
│  │  │     │  │  ├─ change-password-dialog.html
│  │  │     │  │  ├─ change-password-dialog.scss
│  │  │     │  │  └─ change-password-dialog.ts
│  │  │     │  ├─ confirm-dialog
│  │  │     │  │  ├─ confirm-dialog.html
│  │  │     │  │  ├─ confirm-dialog.scss
│  │  │     │  │  └─ confirm-dialog.ts
│  │  │     │  ├─ dashboard-header
│  │  │     │  │  ├─ dashboard-header.html
│  │  │     │  │  ├─ dashboard-header.scss
│  │  │     │  │  ├─ dashboard-header.spec.ts
│  │  │     │  │  └─ dashboard-header.ts
│  │  │     │  ├─ drive-item-card
│  │  │     │  │  ├─ drive-item-card.html
│  │  │     │  │  ├─ drive-item-card.scss
│  │  │     │  │  ├─ drive-item-card.spec.ts
│  │  │     │  │  ├─ drive-item-card.ts
│  │  │     │  │  └─ drive-item.model.ts
│  │  │     │  ├─ mobile-bottom-nav
│  │  │     │  │  ├─ mobile-bottom-nav.html
│  │  │     │  │  ├─ mobile-bottom-nav.scss
│  │  │     │  │  ├─ mobile-bottom-nav.spec.ts
│  │  │     │  │  └─ mobile-bottom-nav.ts
│  │  │     │  ├─ password-prompt
│  │  │     │  │  ├─ password-prompt.html
│  │  │     │  │  ├─ password-prompt.scss
│  │  │     │  │  ├─ password-prompt.spec.ts
│  │  │     │  │  └─ password-prompt.ts
│  │  │     │  └─ side-panel
│  │  │     │     ├─ side-panel.html
│  │  │     │     ├─ side-panel.scss
│  │  │     │     ├─ side-panel.spec.ts
│  │  │     │     └─ side-panel.ts
│  │  │     ├─ pipes
│  │  │     │  ├─ file-size.pipe.ts
│  │  │     │  └─ mime-icon.pipe.ts
│  │  │     ├─ styles
│  │  │     │  └─ brand-logo.scss
│  │  │     └─ utils
│  │  │        ├─ file-size-formatting.utils.ts
│  │  │        ├─ folder-traversal.ts
│  │  │        └─ mime.utils.ts
│  │  ├─ assets
│  │  │  ├─ full_nephos_logo.png
│  │  │  └─ icon_nephos_logo.png
│  │  ├─ environments
│  │  │  ├─ environment.development.ts
│  │  │  └─ environment.ts
│  │  ├─ index.html
│  │  ├─ main.ts
│  │  └─ styles.scss
│  ├─ stylelint.config.mjs
│  ├─ tsconfig.app.json
│  ├─ tsconfig.json
│  └─ tsconfig.spec.json
├─ k8s
│  ├─ auth-service.yaml
│  ├─ aws-secrets-provider.yaml
│  ├─ configmap.yaml
│  ├─ ingress.yaml
│  ├─ namespace.yaml
│  ├─ rabbitmq.yaml
│  ├─ redis.yaml
│  └─ storage-service.yaml
├─ start-backend-v2.bat
├─ terraform
│  ├─ addons.tf
│  ├─ ecr.tf
│  ├─ eks.tf
│  ├─ frontend_hosting.tf
│  ├─ iam.tf
│  ├─ lambda_cron.tf
│  ├─ main.tf
│  ├─ outputs.tf
│  ├─ rds.tf
│  ├─ s3_storage.tf
│  ├─ secrets_manager.tf
│  ├─ variables.tf
│  └─ vpc.tf
└─ terraform-v2
   ├─ compute
   │  ├─ addons.tf
   │  ├─ eks.tf
   │  ├─ iam.tf
   │  ├─ main.tf
   │  ├─ outputs.tf
   │  ├─ peering.tf
   │  ├─ variables.tf
   │  ├─ versions.tf
   │  └─ vpc.tf
   └─ data
      ├─ ecr.tf
      ├─ frontend.tf
      ├─ iam.tf
      ├─ lambda.tf
      ├─ outputs.tf
      ├─ rds.tf
      ├─ secrets.tf
      ├─ storage.tf
      ├─ variables.tf
      ├─ versions.tf
      └─ vpc.tf

```