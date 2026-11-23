PREFIX ?= $(HOME)/.local

.PHONY: check test install
check:
	bash -n bin/wt-switch
	shellcheck bin/wt-switch
	python3 -m unittest discover -s tests -v

test:
	python3 -m unittest discover -s tests -v

install:
	install -d "$(DESTDIR)$(PREFIX)/bin"
	install -m 755 bin/wt-switch "$(DESTDIR)$(PREFIX)/bin/wt-switch"
