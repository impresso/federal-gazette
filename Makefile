

target: dl-de dl-it dl-fr



dl-%:
	for y in $$(seq 1849 1 1998) ; do wget -S -N --limit-rate=14k  --regex-type pcre  --reject-regex "https://www.admin.ch/opc/$*/[^f].*"--accept-regex "https://www.admin.ch/opc/$*/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/$*/federal-gazette/$${y}/index.html ; done
dl-it:
	for y in $$(seq 1971 1 1998) ; do wget -S -N --limit-rate=4k -w 1 --regex-type pcre  --reject-regex "https://www.admin.ch/opc/it/[^f].*"--accept-regex "https://www.admin.ch/opc/it/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/it/federal-gazette/$${y}/index.html ; done
	
	
# --accept-regex urlregex
# --regex-type pcre



SHELL:=/bin/bash
