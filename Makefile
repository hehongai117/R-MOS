.PHONY: migrate seed-demo reset-db

DB_HOST ?= localhost
DB_PORT ?= 5432
DB_USER ?= postgres
DB_NAME ?= rmos_dev

migrate:
	@if [ -z "$$DATABASE_URL" ]; then echo "请先设置 DATABASE_URL"; exit 1; fi
	@cd r-mos-backend && .venv/bin/alembic -c alembic.ini upgrade head

seed-demo:
	@if [ -z "$$DATABASE_URL" ]; then echo "请先设置 DATABASE_URL"; exit 1; fi
	@DATABASE_URL="$$DATABASE_URL" r-mos-backend/.venv/bin/python r-mos-backend/scripts/seed_teaching_demo.py --reset

reset-db:
	@echo "警告：将删除并重建数据库 $${DB_NAME}"
	@psql -h $${DB_HOST} -p $${DB_PORT} -U $${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS $${DB_NAME};"
	@psql -h $${DB_HOST} -p $${DB_PORT} -U $${DB_USER} -d postgres -c "CREATE DATABASE $${DB_NAME};"
