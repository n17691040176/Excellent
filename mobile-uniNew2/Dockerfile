FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=/
ARG VITE_INVITE_WEB_BASE_URL=/
ARG VITE_APP_ENV=prod
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_INVITE_WEB_BASE_URL=${VITE_INVITE_WEB_BASE_URL}
ENV VITE_APP_ENV=${VITE_APP_ENV}

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build:h5

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/build/h5 /usr/share/nginx/html

EXPOSE 80
