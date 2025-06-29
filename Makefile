PLUGIN=libspeedtrack.so
PLUGIN_SRC=speed_plugin.c
PKGS=$(shell pkg-config --cflags --libs gstreamer-1.0 gstreamer-base-1.0)
LIBS=$(PKGS) -lsqlite3 -lm
CFLAGS=-Wall -fPIC -shared -DPACKAGE=\"speedtrack\"
CC=gcc

ifeq ($(USE_DEEPSTREAM),1)
CFLAGS += -DHAVE_NVDS -I/opt/nvidia/deepstream/deepstream/sources/includes
LIBS += -lnvds_meta
endif

$(PLUGIN): $(PLUGIN_SRC)
	$(CC) $(CFLAGS) $(PLUGIN_SRC) -o $(PLUGIN) $(LIBS)

clean:
	rm -f $(PLUGIN) *.o
