build-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --tree-shaking=true --outfile=pyblade/live/static/pyblade.min.js

watch-js:
	esbuild pyblade/live/static/src/index.js --bundle --minify --tree-shaking=true --watch --outfile=pyblade/live/static/pyblade.min.js