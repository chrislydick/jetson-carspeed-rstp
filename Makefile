# -*- coding: utf-8 -*-
PLUGIN=libspeedtrack.so
CFLAGS=-Wall -fPIC
LIBS=$(shell pkg-config --cflags --libs gstreamer-1.0 gstreamer-base-1.0) -lnvds_meta -lsqlite3

$(PLUGIN): speed_plugin.c
$(CC) $(CFLAGS) -shared $< -o $@ $(LIBS)

all: $(PLUGIN)

clean:
rm -f $(PLUGIN)
