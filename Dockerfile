FROM nvcr.io/nvidia/jetpack:6.0-devel

WORKDIR /app

# Install build tools and Python dependencies
RUN apt-get update && \
    apt-get install -y \
        python3-gi python3-pip clang \
        libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install pytest PyYAML

COPY . /app

# Build the speedtrack plugin
RUN make && clang --analyze speed_plugin.c $(pkg-config --cflags --libs gstreamer-1.0 gstreamer-base-1.0)

CMD ["bash"]
