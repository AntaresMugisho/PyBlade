build-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --tree-shaking=true --outfile=pyblade/live/static/pyblade.min.js

watch-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --tree-shaking=true --watch --outfile=pyblade/live/static/pyblade.min.js

test-js:
	node --test tests/live/*.mjs

test-py:
	uv run pytest tests

test: test-py test-js

pre-commit:
	uv run pre-commit run --all-files


.PHONY: build-js watch-js test-js test-py test pre-commit
