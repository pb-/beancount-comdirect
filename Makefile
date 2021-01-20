lint:
	pipenv run flake8 beancount_comdirect tests
	pipenv run black --check -S --line-length 79 --diff beancount_comdirect tests
.PHONY: lint

format:
	pipenv run black -S --line-length 79 beancount_comdirect tests
.PHONY: format

test:
	pipenv run py.test tests
.PHONY: test
