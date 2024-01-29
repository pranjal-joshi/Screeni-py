build:
	docker build -t screeni-py .

run:
	docker run -d --name screeni-py -p 8501:8501 screeni-py

interactive-run:
	docker run -p 8501:8501 screeni-py

shell:
	docker run -it --entrypoint /bin/bash screeni-py

stop-container:
	@if [ "$(shell docker ps -q -f name=screeni-py)" ]; then \
		docker stop screeni-py; \
	else \
		echo "Container screeni-py is not running."; \
	fi

remove-container:
	@if [ "$(shell docker ps -a -q -f name=screeni-py)" ]; then \
		docker rm screeni-py; \
	else \
		echo "Container screeni-py does not exist."; \
	fi

system-clean:
	docker system prune --force

rebuild: stop-container remove-container build system-clean
