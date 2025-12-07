# backend/Dockerfile
FROM node:18-alpine

# Create app directory and set permissions for 'node' user
WORKDIR /app
RUN chown -R node:node /app

# Switch to non-root user (REQUIRED for OpenShift)
USER node

# Copy package files (ownership must be set)
COPY --chown=node:node package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY --chown=node:node . .

EXPOSE 4000

CMD ["npm", "start"]