build-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --tree-shaking=true --outfile=pyblade/live/static/pyblade.min.js

watch-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --tree-shaking=true --watch --outfile=pyblade/live/static/pyblade.min.js

test-js:
	node --test tests/live/*.mjs

test-py:
	pytest tests

test: test-py test-js

.PHONY: build-js watch-js test-js test-py test
