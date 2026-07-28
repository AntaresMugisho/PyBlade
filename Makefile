build-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --outfile=pyblade/live/static/pyblade.min.js

watch-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --watch --outfile=pyblade/live/static/pyblade.min.js