FROM node:22-alpine AS dev

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
# Source files are bind-mounted at runtime; node_modules lives only in this layer
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM dev AS build
RUN npm run build

FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
