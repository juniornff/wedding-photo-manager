FROM node:22-alpine AS build
ARG VITE_API_URL
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN VITE_API_URL=${VITE_API_URL:-http://localhost:8000} npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install -g serve
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
