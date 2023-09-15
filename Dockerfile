# Use the BusyBox base image
FROM busybox

# Create a directory for serving the HTML file
RUN mkdir -p /www

# Copy the index.html file to the /www directory in the container
COPY index.html /www/index.html

# Create an unprivileged user
RUN adduser -D -H -s /bin/sh httpuser

# Change ownership of the /www directory to the unprivileged user
RUN chown -R httpuser /www

# Expose port 8080 for the HTTP server to listen on
EXPOSE 8080

# Switch to the unprivileged user and start the BusyBox HTTP server
USER httpuser
CMD httpd -f -p 8080 -h /www
