FROM node:20-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# icons.ts resolves ../../../design/assets/icons from /app/src/app.
COPY design/assets/icons /design/assets/icons
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
