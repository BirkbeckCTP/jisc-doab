DOAB_DB_PORT=5432
DOAB_DB_HOST=doab-postgres
DOAB_DB_USER=doab
DOAB_DB_PASSWORD=doab
DOAB_DB_VOLUME=db/postgres-data
CLI_COMMAND=psql --username=$(DOAB_DB_USER) $(DOAB_DB_NAME)

ifdef VERBOSE
	_VERBOSE=--verbose
endif

export DOAB_DB_USER
export DOAB_DB_PASSWORD
export DOAB_DB_NAME
export DOAB_DB_HOST
export DOAB_DB_PORT

all: doab-cli
help:		## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
doab-cli:	## Run DOAB commands in a container
	docker-compose $(_VERBOSE) run --rm doab $(CMD)
install:	## Initialises the database
	@docker-compose run --rm --entrypoint="echo 'Starting Installation'" doab
	@make db-client DB_QUERY="-c 'CREATE EXTENSION pg_trgm;'" | true
	@make migrate
migrate:	## Runs the database migrations
	@docker-compose run --rm --entrypoint=alembic doab upgrade head
rebuild:	## Rebuild the doab docker image.
	docker-compose build --no-cache doab
shell:		## Starts an interactive shell within a docker container build from the same image as the one used by the CLI
	docker-compose run --entrypoint=/bin/bash --rm doab
db-client:	## runs the database CLI client interactively within the database container
	@docker exec -ti `docker ps -q --filter 'name=doab-postgres'` $(CLI_COMMAND) $(DB_QUERY)
uninstall:	## Removes all doab related docker containers, docker images and database volumes
	@bash -c "rm -rf volumes/*"
	@bash -c "docker rm -f `docker ps --filter 'name=doab*' -aq` >/dev/null 2>&1 | true"
	@bash -c "docker rmi `docker images -q doab*` >/dev/null 2>&1 | true"
	@echo " DOAB Intersect has been uninstalled"
check:		## Runs the test suite
	bash -c "docker-compose run --rm --entrypoint=python doab doab/tests"
revisions:	## Creates the database revisions according to changes to the models. The MSG variable is used to passed the the description of the revision
	@test -n "$(MSG)" || (echo "The MSG variable must be passed" ; exit 1)
	@docker-compose run --rm --entrypoint=alembic doab revision -m "$(MSG)"
