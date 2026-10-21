# Сборка статики
FROM node:22.21.1-alpine AS build
WORKDIR /app

COPY package.json package-lock.json .npmrc ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# Раздача статики и прокси к ядру
FROM nginx:1.28.0-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
