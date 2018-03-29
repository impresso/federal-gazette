

target: dl-de dl-it dl-fr

dl-%:
	for y in $$(seq 1849 1 2009) wget --regex-type pcre  --reject-regex "https://www.admin.ch/opc/$*/[^f].*"--accept-regex "https://www.admin.ch/opc/$*/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/$*/federal-gazette/$${y}/index.html
	
	
# --accept-regex urlregex
# --regex-type pcre
