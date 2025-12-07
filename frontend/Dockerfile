# frontend/Dockerfile
# Stage 1: Build
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx (OpenShift Config)
FROM nginxinc/nginx-unprivileged:alpine
# Uses 'nginx-unprivileged' image which runs on port 8080 by default

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Expose 8080 (Non-root port)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]