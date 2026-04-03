FROM node:20-alpine AS development

WORKDIR /app
ENV TZ=Asia/Shanghai

RUN npm install -g pnpm@latest

COPY web/package*.json ./web/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY web/src ./src
COPY web/public ./public
COPY web/vite.config.js ./

EXPOSE 5173

CMD ["pnpm", "run", "dev"]


FROM node:20-alpine AS build

WORKDIR /app

RUN npm install -g pnpm@latest

COPY web/package*.json ./web/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY web/ ./
RUN pnpm run build


FROM nginx:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]