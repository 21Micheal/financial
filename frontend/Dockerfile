# syntax=docker/dockerfile:1
# Frontend Dockerfile for financial-system

FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine AS development
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
