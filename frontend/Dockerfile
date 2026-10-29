FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8091
ENV VITE_API_URL=$VITE_API_URL
RUN NITRO_PRESET=node-server npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV PORT=3000 \
    HOST=0.0.0.0
COPY --from=build --chown=node:node /app/.output ./.output
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
