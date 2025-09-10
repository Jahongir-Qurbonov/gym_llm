FROM nginx:alpine

# Copy static files
COPY frontend/ /usr/share/nginx/html/

# Custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
