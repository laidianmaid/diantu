FROM golang:1.24-alpine AS builder

RUN apk add --no-cache git
RUN go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

RUN xcaddy build \
    --with github.com/caddy-dns/duckdns

FROM caddy:2.9-alpine
COPY --from=builder /go/caddy /usr/bin/caddy
