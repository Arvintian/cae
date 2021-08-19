FROM nginx:1.14-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY dist /usr/share/nginx/dist
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]