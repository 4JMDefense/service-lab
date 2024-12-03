# Use the official Nginx image
FROM nginx

# Copy the static files (your web application)
COPY . /usr/share/nginx/html

# Copy the custom nginx configuration into the Nginx conf.d directory
COPY my_custom_config.conf /etc/nginx/conf.d/

# Expose port 8888
EXPOSE 8888

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]

