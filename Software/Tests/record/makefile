CC=gcc
CFLAGS=-c -Wall -Wextra $(shell pkg-config gstreamer-1.0 --cflags)  
LDFLAGS= $(shell pkg-config gstreamer-1.0 --libs)

SOURCES=record.c
OBJECTS=$(SOURCES:.c=.o)

EXECUTABLE=record 

all: $(SOURCES) $(EXECUTABLE)
 
$(EXECUTABLE): $(OBJECTS)
	$(CC) $(OBJECTS) -o $@ $(LDFLAGS)
 
.c.o:
	$(CC) $(CFLAGS) $< -o $@
 
clean:
	rm -f $(OBJECTS) $(EXECUTABLE) *.mp4

.PHONY: clean

install:
	sudo apt-get install libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-pulseaudio

