PLUGIN=libspeedtrack.so
PLUGIN_SRC=speed_plugin.c
PKGS=$(shell pkg-config --cflags --libs gstreamer-1.0 gstreamer-base-1.0)
LIBS=$(PKGS) -lnvds_meta -lsqlite3 -lm
CFLAGS=-Wall -fPIC -shared
CC=gcc

$(PLUGIN): $(PLUGIN_SRC)
	$(CC) $(CFLAGS) $(PLUGIN_SRC) -o $(PLUGIN) $(LIBS)

clean:
	rm -f $(PLUGIN) *.o
