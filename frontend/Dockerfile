FROM node:22-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM dev AS build
# 拷贝前端所有源码
COPY . .
# 接收高德密钥参数
ARG VITE_AMAP_JS_KEY
ENV VITE_AMAP_JS_KEY=$VITE_AMAP_JS_KEY
ARG VITE_EDGE_MODEL_URLS
ENV VITE_EDGE_MODEL_URLS=$VITE_EDGE_MODEL_URLS
ARG VITE_EDGE_MODEL_SIZE_BYTES
ENV VITE_EDGE_MODEL_SIZE_BYTES=$VITE_EDGE_MODEL_SIZE_BYTES
# 生产环境使用相对路径，由 Nginx 统一转发请求
ENV VITE_API_BASE=""
RUN npm run build

FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
