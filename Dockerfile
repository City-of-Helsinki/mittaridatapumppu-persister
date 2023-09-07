# Use the BusyBox base image
FROM busybox

# Create a directory for serving the HTML file
RUN mkdir -p /data

# Copy the index.html file to the /data directory in the container
COPY index.html /data/index.html

# Create an unprivileged user
RUN adduser -D -H -s /bin/sh httpuser

# Change ownership of the /data directory to the unprivileged user
RUN chown -R httpuser /data

# Expose port 8080 for the HTTP server to listen on
EXPOSE 8080

# Switch to the unprivileged user and start the BusyBox HTTP server
USER httpuser
CMD httpd -p 8080 -h /data
