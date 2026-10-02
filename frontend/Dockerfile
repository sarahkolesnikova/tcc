FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npx react-router build

FROM nginx:1.27-alpine
COPY --from=build /app/build/client /usr/share/nginx/html
# SPA: qualquer rota cai no index.html
RUN printf 'server { listen 80; root /usr/share/nginx/html; location / { try_files $uri /index.html; } }\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
