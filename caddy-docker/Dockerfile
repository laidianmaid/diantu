FROM golang:1.26-alpine AS builder

RUN apk add --no-cache git

RUN go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

RUN xcaddy build v2.11.4 \
    --with github.com/caddy-dns/duckdns

FROM caddy:2.11.4-alpine
COPY --from=builder /go/caddy /usr/bin/caddy
